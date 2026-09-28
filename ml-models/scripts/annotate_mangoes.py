import argparse
import base64
import csv
import hashlib
import json
import os
import random
import re
import time
from datetime import datetime, timezone
from email.utils import parsedate_to_datetime
from pathlib import Path
from typing import Literal

import httpx
from dotenv import load_dotenv
from filelock import FileLock, Timeout
from google import genai
from google.genai import types
from google.genai._gaos.lib.compat_errors import APIError, APIResponseValidationError
from pydantic import BaseModel, ValidationError

ML_ROOT = Path(__file__).resolve().parents[1]
PROMPT = """Analyze this mango image and return the requested fields.
- view_type: exterior if the mango is intact, interior if cut open, otherwise unknown.
- post_it_text: transcribe every visible line on the handwritten post-it, preserving
  line breaks. Include numbers and codes. Use [illegible] for unclear characters.
  Return null if there is no note.
- cultivar: the cultivar written on the note, or null if absent or unclear.
  Do not infer it from appearance.
- specimen_code: a code such as R11 P7, or null if absent or unclear.
- label_readable: whether a human could reasonably verify the note.
"""


class MangoAnnotation(BaseModel):
    view_type: Literal["exterior", "interior", "unknown"]
    post_it_text: str | None
    cultivar: str | None
    specimen_code: str | None
    label_readable: bool


class IdentifiedMangoAnnotation(MangoAnnotation):
    image_id: str


class GroupAnnotations(BaseModel):
    annotations: list[IdentifiedMangoAnnotation]


GROUP_PROMPT = (PROMPT + "\nAnalyze each image independently. Return exactly one annotation per supplied image_id. "
                "Never transfer notes, cultivars, or specimen codes between images. "
                "Leave missing or unreadable labels null even if another image has a readable note.")


class MangoAnnotator:
    def __init__(self, input_dir, output, model="gemini-3.8-flash", delay=2, group_size=3):
        self.input_dir = Path(input_dir).resolve()
        self.output = Path(output).resolve()
        self.model = model
        self.delay = delay
        self.group_size = group_size
        self.client = None
        self.last_request_end = None
        self.records = {}
        self.fingerprint = hashlib.sha256(
            (PROMPT + json.dumps(MangoAnnotation.model_json_schema(), sort_keys=True)
             + "image/heic").encode()
        ).hexdigest()
        self.legacy_fingerprint = self.fingerprint
        if group_size > 1:
            self.fingerprint = hashlib.sha256(
                (GROUP_PROMPT + json.dumps(GroupAnnotations.model_json_schema(), sort_keys=True)
                 + f"image/heic:{group_size}").encode()
            ).hexdigest()

    def is_completed(self, identity):
        return (self.key(identity) in self.records or
                (self.group_size > 1 and
                 self.key({**identity, "fingerprint": self.legacy_fingerprint}) in self.records))

    @staticmethod
    def key(record):
        return tuple(record[k] for k in ("raw_path", "sha256", "model", "fingerprint"))

    @staticmethod
    def append(path, record):
        line = json.dumps(record, ensure_ascii=False) + "\n"
        with path.open("a", encoding="utf-8") as handle:
            handle.write(line)
            handle.flush()
            os.fsync(handle.fileno())

    def load_progress(self):
        self.records = {}
        if not self.output.exists():
            return
        data = self.output.read_bytes()
        lines = data.splitlines(keepends=True)
        offset = 0
        for index, line in enumerate(lines):
            try:
                record = json.loads(line)
            except (ValueError, UnicodeDecodeError) as exc:
                if index != len(lines) - 1 or line.endswith(b"\n"):
                    raise RuntimeError(f"Corrupt results at line {index + 1}.") from exc
                backup = self.output.with_name(self.output.name + f".{time.time_ns()}.tail.bak")
                with backup.open("xb") as handle:
                    handle.write(line)
                    handle.flush()
                    os.fsync(handle.fileno())
                with self.output.open("r+b") as handle:
                    handle.truncate(offset)
                    handle.flush()
                    os.fsync(handle.fileno())
                print(f"Recovered incomplete final line; backup: {backup}")
                break
            try:
                MangoAnnotation.model_validate(record["annotation"])
                key = self.key(record)
                self.records.pop(key, None)
                self.records[key] = record
            except (KeyError, TypeError, ValidationError) as exc:
                raise RuntimeError(f"Invalid saved record at line {index + 1}.") from exc
            offset += len(line)
        else:
            if data and not data.endswith(b"\n"):
                with self.output.open("ab") as handle:
                    handle.write(b"\n")
                    handle.flush()
                    os.fsync(handle.fileno())

    def save_result(self, identity, response, annotation):
        record = {
            **identity,
            "completed_at": datetime.now(timezone.utc).isoformat(),
            "annotation": annotation.model_dump(),
        }
        self.append(self.output, record)
        key = self.key(record)
        self.records.pop(key, None)
        self.records[key] = record

    @staticmethod
    def sanitize(value):
        if not isinstance(value, str):
            return None
        for name in ("GEMINI_API_KEY", "GOOGLE_API_KEY"):
            secret = os.getenv(name)
            if secret:
                value = value.replace(secret, "[REDACTED]")
        value = re.sub(r"https?://\S+", "[URL REDACTED]", value)
        value = re.sub(r"AIza[\w-]+", "[REDACTED]", value)
        value = re.sub(r"(?i)(bearer\s+|(?:api[_-]?key|authorization|token)[\s\"':=]+)\S+",
                       r"\1[REDACTED]", value)
        value = re.sub(r"[A-Za-z0-9+/=_-]{80,}", "[PAYLOAD REDACTED]", value)
        return " ".join(value.split())[:1000]

    def print_error(self, identity, category, attempt, code=None, error=None):
        body = getattr(error, "body", {})
        details = body.get("error", body) if isinstance(body, dict) else {}
        details = details if isinstance(details, dict) else {}
        message = details.get("message")
        if not isinstance(message, str):
            message = {
                "invalid_response": "Response did not match the expected JSON schema.",
                "unreadable_file": "Could not read image bytes, or the file was empty.",
            }.get(category, getattr(error, "message", None) or "Request failed without a structured error message.")
        response = getattr(error, "response", None)
        headers = response.headers if response is not None else {}
        diagnostic = {
            "message": self.sanitize(message),
            "api_code": self.sanitize(str(details.get("status") or details.get("code") or "")) or None,
            "request_id": self.sanitize(headers.get("x-request-id") or headers.get("x-goog-request-id")),
        }
        extra = " ".join(f"{key}={value}" for key, value in diagnostic.items() if key != "message" and value)
        print(f"Error {identity['raw_path']} ({category}, attempt {attempt}, HTTP {code}): "
              f"{diagnostic['message']} {extra}".rstrip(), flush=True)

    @staticmethod
    def retry_delay(error):
        response = getattr(error, "response", None)
        header = response.headers.get("Retry-After") if response is not None else None
        wait = 0.0
        if header:
            try:
                wait = float(header)
            except ValueError:
                try:
                    wait = (parsedate_to_datetime(header) - datetime.now(timezone.utc)).total_seconds()
                except (ValueError, TypeError):
                    pass
        details = getattr(error, "body", {})
        if isinstance(details, dict):
            details = details.get("error", details)
        if isinstance(details, dict):
            for detail in details.get("details", []):
                if isinstance(detail, dict) and "retryDelay" in detail:
                    try:
                        wait = max(wait, float(str(detail["retryDelay"]).removesuffix("s")))
                    except ValueError:
                        pass
        return max(0, wait)

    def annotate(self, data, identity):
        grouped = isinstance(data, list)
        if grouped:
            identities = identity
            identity = identities[0]
            parts = [{"type": "text", "text": GROUP_PROMPT}]
            for index, image in enumerate(data):
                parts.extend([
                    {"type": "text", "text": f"The next image has image_id: image_{index + 1}"},
                    {"type": "image", "data": base64.b64encode(image).decode("ascii"), "mime_type": "image/heic"},
                ])
            schema = GroupAnnotations
        else:
            parts = [{"type": "image", "data": base64.b64encode(data).decode("ascii"), "mime_type": "image/heic"},
                     {"type": "text", "text": PROMPT}]
            schema = MangoAnnotation
        invalid = 0
        for attempt in range(1, 6):
            if self.last_request_end is not None:
                time.sleep(max(0, self.delay - (time.monotonic() - self.last_request_end)))
            try:
                response = self.client.interactions.create(
                    model=self.model,
                    input=parts,
                    response_format={"type": "text", "mime_type": "application/json",
                                     "schema": schema.model_json_schema()},
                    store=False,
                )
            except (ValidationError, APIResponseValidationError):
                invalid += 1
                self.print_error(identity, "invalid_response", attempt)
                if invalid >= 2 or attempt == 5:
                    return None
                continue
            except (APIError, httpx.TransportError) as exc:
                code = getattr(exc, "status_code", None)
                self.print_error(identity, type(exc).__name__, attempt, code, error=exc)
                details = json.dumps(getattr(exc, "body", {})).lower()
                daily = code == 429 and any(s in details for s in (
                    "perday", "per_day", "per day", "daily quota", "daily limit",
                ))
                retryable = code is None or code in (408, 429) or (500 <= code < 600)
                if daily or not retryable or attempt == 5:
                    raise RuntimeError(f"Stopped on {type(exc).__name__} (HTTP {code}); progress saved.") from None
                wait = max(16 * 2 ** (attempt - 1) + random.uniform(0, 1), self.retry_delay(exc))
                if wait > 300:
                    raise RuntimeError("Server requests a wait over five minutes; progress saved.") from None
                print(f"Retry {attempt}/4: HTTP {code}; waiting {wait:.1f}s", flush=True)
                time.sleep(wait)
                continue
            finally:
                self.last_request_end = time.monotonic()
            try:
                annotation = schema.model_validate_json(response.output_text or "")
                if grouped:
                    expected = [f"image_{i + 1}" for i in range(len(data))]
                    returned = [item.image_id for item in annotation.annotations]
                    if len(returned) != len(expected) or set(returned) != set(expected):
                        raise ValueError("Missing, duplicate, or unexpected image IDs")
                    by_id = {item.image_id: item for item in annotation.annotations}
                    annotation = [MangoAnnotation.model_validate(by_id[key].model_dump(exclude={"image_id"}))
                                  for key in expected]
            except (ValidationError, ValueError):
                invalid += 1
                self.print_error(identity, "invalid_response", attempt)
                if invalid >= 2 or attempt == 5:
                    return None
                continue
            return response, annotation

    def export_csv(self):
        latest = {}
        for record in self.records.values():
            latest[(record["raw_path"], record["model"], record["fingerprint"])] = record
        target = self.output.with_suffix(".csv")
        temporary = target.with_suffix(".csv.tmp")
        fields = ["raw_path", "sha256", "model", "fingerprint", "completed_at",
                  *MangoAnnotation.model_fields, "status"]
        try:
            with temporary.open("w", newline="", encoding="utf-8") as handle:
                writer = csv.DictWriter(handle, fieldnames=fields)
                writer.writeheader()
                for record in latest.values():
                    writer.writerow({**{k: record[k] for k in fields[:5]},
                                     **record["annotation"], "status": "pending"})
                handle.flush()
                os.fsync(handle.fileno())
            os.replace(temporary, target)
        finally:
            temporary.unlink(missing_ok=True)
        print(f"Exported {len(latest)} records to {target}")

    def run(self, limit=None, export_only=False):
        self.output.parent.mkdir(parents=True, exist_ok=True)
        completed = reused = failed = processed = 0
        try:
            with FileLock(str(self.output) + ".lock", timeout=0):
                self.load_progress()
                if export_only:
                    self.export_csv()
                    return
                if not self.input_dir.is_dir():
                    raise RuntimeError(f"Input directory does not exist: {self.input_dir}")
                files = sorted(p for p in self.input_dir.rglob("*") if p.is_file() and p.suffix.lower() == ".heic")
                load_dotenv(ML_ROOT.parent / ".env")
                key = os.getenv("GEMINI_API_KEY")
                invalid_streak = 0
                pending = []
                for index, path in enumerate(files):
                    if limit is not None and processed + len(pending) >= limit:
                        break
                    identity = {"raw_path": Path(os.path.relpath(path, ML_ROOT)).as_posix(),
                                "model": self.model, "fingerprint": self.fingerprint}
                    try:
                        data = path.read_bytes()
                        if not data:
                            raise OSError("Empty file")
                    except OSError:
                        self.print_error(identity, "unreadable_file", 0)
                        failed += 1
                        processed += 1
                        print(f"Unreadable: {path.name}", flush=True)
                        continue
                    identity["sha256"] = hashlib.sha256(data).hexdigest()
                    if self.is_completed(identity):
                        reused += 1
                        continue
                    pending.append((data, identity))
                    if len(pending) < self.group_size:
                        continue
                    yield_group = pending
                    pending = []
                    # Process full groups here; the final partial group is handled below.
                    if self.client is None:
                        if not key:
                            raise RuntimeError("Set GEMINI_API_KEY in the environment or repository-root .env.")
                        self.client = genai.Client(api_key=key, http_options=types.HttpOptions(
                            timeout=60000, retry_options=types.HttpRetryOptions(attempts=1),
                        ))
                        self.client.interactions.sdk_configuration.retry_config.strategy = "none"
                    saved = self.process_group(yield_group)
                    processed += len(yield_group)
                    completed += saved
                    failed += len(yield_group) - saved
                    invalid_streak = invalid_streak + 1 if not saved else 0
                    if invalid_streak >= 3:
                        raise RuntimeError("Three consecutive invalid responses; progress saved.")
                    print(f"Saved {completed}; reused {reused}; failed {failed}; unscanned {len(files) - index - 1}", flush=True)
                if pending:
                    if self.client is None:
                        if not key:
                            raise RuntimeError("Set GEMINI_API_KEY in the environment or repository-root .env.")
                        self.client = genai.Client(api_key=key, http_options=types.HttpOptions(
                            timeout=60000, retry_options=types.HttpRetryOptions(attempts=1),
                        ))
                        # Interactions currently interprets attempts=1 as one extra retry.
                        self.client.interactions.sdk_configuration.retry_config.strategy = "none"
                    saved = self.process_group(pending)
                    completed += saved
                    failed += len(pending) - saved
        except Timeout:
            raise RuntimeError("Another process holds the results lock.") from None
        finally:
            if self.client is not None:
                self.client.close()
                self.client = None
            print(f"Completed {completed}; reused {reused}; failed {failed}. Results: {self.output}")
            print("Resume by rerunning the same command.")

    def process_group(self, pending):
        print("Annotating: " + ", ".join(Path(i["raw_path"]).name for _, i in pending), flush=True)
        if self.group_size == 1:
            result = self.annotate(*pending[0])
            if result is None:
                return 0
            response, annotation = result
            annotations = [annotation]
        else:
            result = self.annotate([data for data, _ in pending], [i for _, i in pending])
            if result is None:
                return 0
            response, annotations = result
        for (_, identity), annotation in zip(pending, annotations):
            self.save_result(identity, response, annotation)
        return len(annotations)


def main():
    parser = argparse.ArgumentParser(description="Annotate mango HEIC files with resumable Gemini requests.")
    parser.add_argument("--input", type=Path, default=ML_ROOT / "data/raw/sharepoint_data/Fruit_Images")
    parser.add_argument("--output", type=Path, default=ML_ROOT / "data/manifests/sharepoint_gemini/annotations.jsonl")
    parser.add_argument("--model", default="gemini-3.8-flash")
    parser.add_argument("--delay", type=float, default=2)
    parser.add_argument("--group-size", type=int, choices=range(1, 6), default=3)
    mode = parser.add_mutually_exclusive_group()
    mode.add_argument("--limit", type=int)
    mode.add_argument("--export-only", action="store_true")
    args = parser.parse_args()
    if args.delay < 0 or (args.limit is not None and args.limit < 1):
        parser.error("--delay must be nonnegative and --limit must be positive")
    try:
        MangoAnnotator(args.input, args.output, args.model, args.delay, args.group_size).run(args.limit, args.export_only)
    except KeyboardInterrupt:
        print("Interrupted; saved annotations will be reused.")
        return 130
    except (RuntimeError, OSError) as exc:
        print(str(exc))
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
