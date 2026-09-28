import base64
import csv
import importlib.util
import json
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import Mock

import pytest
import httpx
from filelock import FileLock
from google import genai
from google.genai._gaos.lib.compat_errors import APIError, APIConnectionError

REAL_CLIENT = genai.Client

spec = importlib.util.spec_from_file_location(
    "annotate_mangoes", Path(__file__).resolve().parents[1] / "scripts/annotate_mangoes.py"
)
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)

ANNOTATION = dict(view_type="exterior", post_it_text="PAHERI\nR11 P7", cultivar="PAHERI",
                  specimen_code="R11 P7", label_readable=True)


def api_error(code, message, headers=None):
    response = httpx.Response(code, headers=headers, request=httpx.Request("POST", "https://example.test"))
    return APIError.generate(code, {"error": {"message": message}}, message, response)


@pytest.fixture
def setup(tmp_path, monkeypatch):
    source = tmp_path / "images"
    source.mkdir()
    for name in ("A.HEIC", "B.heic", "C.HEIC"):
        (source / name).write_bytes(name.encode())
    (source / "A.MOV").write_bytes(b"video")
    output = tmp_path / "results/annotations.jsonl"
    client = Mock()
    client.interactions.create.return_value = SimpleNamespace(
        output_text=json.dumps(ANNOTATION), usage=None,
    )
    monkeypatch.setenv("GEMINI_API_KEY", "test-key")
    monkeypatch.setattr(module.genai, "Client", Mock(return_value=client))
    monkeypatch.setattr(module, "load_dotenv", lambda *args: None)
    monkeypatch.setattr(module.time, "sleep", Mock())
    return source, output, client


def test_resume_and_limit(setup):
    source, output, client = setup
    module.MangoAnnotator(source, output, group_size=1).run(limit=1)
    assert len(output.read_text().splitlines()) == 1
    module.MangoAnnotator(source, output, group_size=1).run(limit=1)
    assert len(output.read_text().splitlines()) == 2
    module.MangoAnnotator(source, output, group_size=1).run()
    module.MangoAnnotator(source, output, group_size=1).run()
    assert client.interactions.create.call_count == 3
    assert client.close.call_count == 3


def test_changed_source_model_prompt(setup):
    source, output, client = setup
    module.MangoAnnotator(source, output, group_size=1).run()
    (source / "A.HEIC").write_bytes(b"changed")
    module.MangoAnnotator(source, output, group_size=1).run()
    module.MangoAnnotator(source, output, model="other", group_size=1).run()
    annotator = module.MangoAnnotator(source, output, group_size=1)
    annotator.fingerprint = "changed-prompt"
    annotator.run()
    assert client.interactions.create.call_count == 10


def test_unknown_labels_are_completed(setup):
    source, output, client = setup
    client.interactions.create.return_value.output_text = json.dumps({
        **ANNOTATION, "view_type": "unknown", "cultivar": None, "post_it_text": None,
        "specimen_code": None, "label_readable": False,
    })
    module.MangoAnnotator(source, output, group_size=1).run()
    module.MangoAnnotator(source, output, group_size=1).run()
    assert client.interactions.create.call_count == 3


def test_retries_stop_and_preserve_progress(setup):
    source, output, client = setup
    success = client.interactions.create.return_value
    error = api_error(429, "rate limited")
    client.interactions.create.side_effect = [success, *([error] * 5)]
    with pytest.raises(RuntimeError, match="progress saved"):
        module.MangoAnnotator(source, output, group_size=1).run()
    assert len(output.read_text().splitlines()) == 1
    assert not output.with_name("errors.jsonl").exists()
    waits = [call.args[0] for call in module.time.sleep.call_args_list]
    for minimum in (16, 32, 64, 128):
        assert any(minimum <= wait < minimum + 1 for wait in waits)
    client.interactions.create.side_effect = None
    module.MangoAnnotator(source, output, group_size=1).run()
    assert len(output.read_text().splitlines()) == 3


@pytest.mark.parametrize("code,message", [(401, "bad key"), (403, "forbidden"),
                                        (404, "missing model"), (429, "RequestsPerDay quota")])
def test_fatal_errors_stop_without_retry(setup, code, message):
    source, output, client = setup
    client.interactions.create.side_effect = api_error(code, message)
    with pytest.raises(RuntimeError):
        module.MangoAnnotator(source, output, group_size=1).run()
    assert client.interactions.create.call_count == 1


def test_server_retry_delay(setup):
    source, output, client = setup
    client.interactions.create.side_effect = api_error(429, "limited", {"Retry-After": "301"})
    with pytest.raises(RuntimeError, match="five minutes"):
        module.MangoAnnotator(source, output, group_size=1).run()
    assert client.interactions.create.call_count == 1


def test_invalid_responses_stop_after_three_images(setup):
    source, output, client = setup
    client.interactions.create.return_value.output_text = "not JSON"
    with pytest.raises(RuntimeError, match="Three consecutive"):
        module.MangoAnnotator(source, output, group_size=1).run()
    assert client.interactions.create.call_count == 6


def test_tail_recovery_and_corruption(setup):
    source, output, client = setup
    module.MangoAnnotator(source, output, group_size=1).run(limit=1)
    with output.open("ab") as handle:
        handle.write(b'{"partial":')
    module.MangoAnnotator(source, output, group_size=1).run()
    assert len(output.read_text().splitlines()) == 3
    assert len(list(output.parent.glob("*.tail.bak"))) == 1
    output.write_text('broken\n' + output.read_text())
    with pytest.raises(RuntimeError, match="Corrupt"):
        module.MangoAnnotator(source, output, group_size=1).run()


def test_lock_excludes_second_writer(setup):
    source, output, client = setup
    output.parent.mkdir()
    with FileLock(str(output) + ".lock"):
        with pytest.raises(RuntimeError, match="Another process"):
            module.MangoAnnotator(source, output, group_size=1).run()
    client.interactions.create.assert_not_called()


def test_csv_latest_revision_multiline_no_api(setup, monkeypatch):
    source, output, client = setup
    module.MangoAnnotator(source, output, group_size=1).run(limit=1)
    original = json.loads(output.read_text())
    newer = {**original, "sha256": "new-hash"}
    module.MangoAnnotator.append(output, newer)
    module.MangoAnnotator.append(output, original)
    client.reset_mock()
    monkeypatch.delenv("GEMINI_API_KEY")
    module.MangoAnnotator(source, output, group_size=1).run(export_only=True)
    with output.with_suffix(".csv").open() as handle:
        rows = list(csv.DictReader(handle))
    assert len(rows) == 1
    assert rows[0]["sha256"] == original["sha256"]
    assert rows[0]["post_it_text"] == "PAHERI\nR11 P7"
    assert rows[0]["status"] == "pending"
    client.interactions.create.assert_not_called()


def test_interrupt_keeps_completed_samples(setup):
    source, output, client = setup
    client.interactions.create.side_effect = [client.interactions.create.return_value, KeyboardInterrupt()]
    with pytest.raises(KeyboardInterrupt):
        module.MangoAnnotator(source, output, group_size=1).run()
    assert len(output.read_text().splitlines()) == 1
    client.close.assert_called_once()
    with FileLock(str(output) + ".lock", timeout=0):
        pass


def test_sdk_validation_error_retried(setup):
    source, output, client = setup
    try:
        module.MangoAnnotation.model_validate({})
    except module.ValidationError as exc:
        validation_error = exc
    client.interactions.create.side_effect = [validation_error, client.interactions.create.return_value]
    module.MangoAnnotator(source, output, group_size=1).run(limit=1)
    assert client.interactions.create.call_count == 2
    assert len(output.read_text().splitlines()) == 1


def test_unreadable_empty_file_continues(setup):
    source, output, client = setup
    (source / "A.HEIC").write_bytes(b"")
    module.MangoAnnotator(source, output, group_size=1).run()
    assert client.interactions.create.call_count == 2
    assert len(output.read_text().splitlines()) == 2
    assert not output.with_name("errors.jsonl").exists()


def test_connection_error_retries(setup):
    source, output, client = setup
    client.interactions.create.side_effect = [
        APIConnectionError(request=httpx.Request("POST", "https://example.test")),
        client.interactions.create.return_value,
    ]
    module.MangoAnnotator(source, output, group_size=1).run(limit=1)
    assert client.interactions.create.call_count == 2


def test_sdk_transport_request_retry_and_usage(setup, monkeypatch):
    source, output, _ = setup
    requests = []

    def respond(request):
        requests.append(request)
        if len(requests) == 1:
            return httpx.Response(429, json={"error": {"message": "rate limited", "code": "RESOURCE_EXHAUSTED"}})
        return httpx.Response(200, json={
            "id": "test-interaction", "status": "completed",
            "steps": [{"type": "model_output", "content": [{"type": "text", "text": json.dumps(ANNOTATION)}]}],
            "usage": {"total_input_tokens": 100, "total_output_tokens": 20, "total_tokens": 120},
        })

    def make_client(**kwargs):
        kwargs["http_options"].httpx_client = httpx.Client(transport=httpx.MockTransport(respond))
        return REAL_CLIENT(**kwargs)

    monkeypatch.setattr(module.genai, "Client", make_client)
    module.MangoAnnotator(source, output, group_size=1).run(limit=1)
    assert len(requests) == 2
    assert requests[0].url.path.endswith("/interactions")
    assert requests[0].extensions["timeout"]["read"] == 60
    payload = json.loads(requests[0].content)
    assert payload["store"] is False
    assert payload["response_format"]["schema"] == module.MangoAnnotation.model_json_schema()
    content = payload["input"][0]["content"]
    assert base64.b64decode(content[0]["data"]) == b"A.HEIC"
    assert content[0]["mime_type"] == "image/heic"
    assert content[1]["text"] == module.PROMPT
    assert not output.with_name("errors.jsonl").exists()
    record = json.loads(output.read_text())
    assert set(record) == {"raw_path", "sha256", "model", "fingerprint", "completed_at", "annotation"}
    assert record["annotation"] == ANNOTATION


def test_old_saved_results_still_resume(setup):
    source, output, client = setup
    module.MangoAnnotator(source, output, group_size=1).run(limit=1)
    record = json.loads(output.read_text())
    record.update(api="interactions", sample_id="A", response_text=json.dumps(ANNOTATION))
    record["usage"] = {"total_token_count": 120}
    output.write_text(json.dumps(record) + "\n")
    client.reset_mock()
    module.MangoAnnotator(source, output, group_size=1).run()
    assert client.interactions.create.call_count == 2


def test_error_details_only_printed(setup, capsys):
    source, output, client = setup
    error = api_error(503, "Model is overloaded. Try again later.", {"x-request-id": "request-123"})
    error.body["error"]["status"] = "UNAVAILABLE"
    client.interactions.create.side_effect = [error, client.interactions.create.return_value]
    module.MangoAnnotator(source, output, group_size=1).run(limit=1)
    assert not output.with_name("errors.jsonl").exists()
    printed = capsys.readouterr().out
    for detail in ("Model is overloaded. Try again later.", "UNAVAILABLE", "request-123", "HTTP 503"):
        assert detail in printed


def test_error_details_redact_credentials_and_payload(setup, capsys):
    source, output, client = setup
    payload = "A" * 200
    error = api_error(403, f"Bad test-key; Bearer secret-token; https://example.test/?key=hidden {payload}")
    error.body["request"] = {"data": "PRIVATE IMAGE", "headers": {"Authorization": "PRIVATE KEY"}}
    client.interactions.create.side_effect = error
    with pytest.raises(RuntimeError):
        module.MangoAnnotator(source, output, group_size=1).run(limit=1)
    assert not output.with_name("errors.jsonl").exists()
    logged = capsys.readouterr().out
    for secret in ("test-key", "secret-token", "hidden", payload, "PRIVATE IMAGE", "PRIVATE KEY"):
        assert secret not in logged
    assert "REDACTED" in logged


def group_response(**kwargs):
    count = sum(part["type"] == "image" for part in kwargs["input"])
    return SimpleNamespace(output_text=json.dumps({"annotations": [
        {**ANNOTATION, "image_id": f"image_{i + 1}", "cultivar": f"cultivar-{i + 1}"}
        for i in reversed(range(count))
    ]}))


def test_groups_flat_records_and_resume(setup):
    source, output, client = setup
    for name in ("D.HEIC", "E.HEIC", "F.HEIC", "G.HEIC"):
        (source / name).write_bytes(name.encode())
    client.interactions.create.side_effect = group_response
    module.MangoAnnotator(source, output).run()
    assert client.interactions.create.call_count == 3
    counts = [sum(p["type"] == "image" for p in c.kwargs["input"])
              for c in client.interactions.create.call_args_list]
    assert counts == [3, 3, 1]
    records = [json.loads(line) for line in output.read_text().splitlines()]
    assert len(records) == 7
    assert all(isinstance(r["annotation"], dict) and "image_id" not in r["annotation"] for r in records)
    assert [r["annotation"]["cultivar"] for r in records[:3]] == ["cultivar-1", "cultivar-2", "cultivar-3"]
    module.MangoAnnotator(source, output).run()
    assert client.interactions.create.call_count == 3
    assert module.MangoAnnotator(source, output).delay == 2
    assert any(1.5 < c.args[0] <= 2 for c in module.time.sleep.call_args_list)


def test_group_limit_and_legacy_resume(setup):
    source, output, client = setup
    module.MangoAnnotator(source, output, group_size=1).run(limit=1)
    client.interactions.create.side_effect = group_response
    module.MangoAnnotator(source, output).run(limit=1)
    assert len(output.read_text().splitlines()) == 2
    assert client.interactions.create.call_count == 2
    module.MangoAnnotator(source, output).run()
    assert len(output.read_text().splitlines()) == 3


@pytest.mark.parametrize("ids", [["image_1", "image_1", "image_3"], ["image_1"], ["x", "y", "z"]])
def test_invalid_group_ids_not_saved(setup, ids):
    source, output, client = setup
    client.interactions.create.return_value.output_text = json.dumps({"annotations": [
        {**ANNOTATION, "image_id": key} for key in ids
    ]})
    module.MangoAnnotator(source, output).run()
    assert not output.exists()
    assert client.interactions.create.call_count == 2


def test_interrupt_mid_group_save_resumes_remaining_images(setup, monkeypatch):
    source, output, client = setup
    client.interactions.create.side_effect = group_response
    annotator = module.MangoAnnotator(source, output)
    save = annotator.save_result
    def interrupted(*args):
        save(*args)
        raise KeyboardInterrupt
    monkeypatch.setattr(annotator, "save_result", interrupted)
    with pytest.raises(KeyboardInterrupt):
        annotator.run()
    assert len(output.read_text().splitlines()) == 1
    module.MangoAnnotator(source, output).run()
    assert len(output.read_text().splitlines()) == 3
    assert sum(p["type"] == "image" for p in client.interactions.create.call_args.kwargs["input"]) == 2
