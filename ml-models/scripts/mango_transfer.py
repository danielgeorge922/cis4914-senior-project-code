"""Four explicit mango experiments and a shared PyTorch transfer-learning workflow."""

from __future__ import annotations

import hashlib
import json
import random
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
import pandas as pd
import torch
from PIL import Image, ImageOps
from torch import nn
from torch.utils.data import DataLoader, Dataset, WeightedRandomSampler
from torchvision import models, transforms
from torchvision.transforms import InterpolationMode


SPLITS = ("train", "validation", "test")
TARGETS = np.array([0.6, 0.2, 0.2])
ARCHITECTURES = ("ResNet50", "VGG16", "EfficientNetB0")
TOP_K_VALUES = (1, 3, 5, 10, 20)
MEAN, STD = [0.485, 0.456, 0.406], [0.229, 0.224, 0.225]
PAD_COLOR = (124, 116, 104)
PREPROCESSING = {
    "size": 224, "rgb": True, "aspect_preserving_padding": True,
    "mean": MEAN, "std": STD, "padding_color": PAD_COLOR,
    "train_augmentation": {"horizontal_flip": 0.5, "rotation_degrees": 15,
                           "brightness": 0.1, "contrast": 0.1,
                           "saturation": 0.05, "scale": [0.9, 1.0]},
}


def connected_groups(frame, keys, prefix):
    parents = list(range(len(frame)))

    def find(i):
        while parents[i] != i:
            parents[i] = parents[parents[i]]
            i = parents[i]
        return i

    for key in keys:
        seen = {}
        for i, value in enumerate(frame[key]):
            if pd.isna(value) or not str(value).strip():
                continue
            if value in seen:
                parents[find(i)] = find(seen[value])
            else:
                seen[value] = i
    return [f"{prefix}{find(i):04d}" for i in range(len(frame))]


def load_catalog(manifest_path, ml_root):
    with Path(manifest_path).open(encoding="utf-8") as handle:
        records = [json.loads(line) for line in handle if line.strip()]
    frame = pd.json_normalize(records)
    frame = (frame.sort_values("completed_at", kind="stable")
             .drop_duplicates("raw_path", keep="last")
             .sort_values("raw_path").reset_index(drop=True))
    frame["class_name"] = (frame["annotation.cultivar"].astype("string")
                           .str.replace(r"\s+", " ", regex=True).str.strip()
                           .str.upper().replace("", pd.NA))
    frame["view"] = frame["annotation.view_type"].astype("string").str.strip().str.lower()
    frame["annotation_code"] = (frame["annotation.specimen_code"].astype("string")
                                .str.upper().str.replace(r"\s+", "", regex=True)
                                .replace("", pd.NA))
    if "source_sha256" not in frame:
        frame["source_sha256"] = pd.NA
    frame["image_path"] = frame.raw_path.map(lambda path: str(Path(ml_root) / path))
    frame["duplicate_group"] = connected_groups(frame, ["sha256", "source_sha256"], "d")
    frame["split_group"] = connected_groups(
        frame, ["annotation_code", "sha256", "source_sha256"], "g",
    )
    # Conflicting exact copies cannot form a meaningful classification target.
    conflicts = frame.groupby("duplicate_group").class_name.nunique()
    if conflicts.gt(1).any():
        raise ValueError("An exact-image group has conflicting class labels; review annotations first.")
    forced_train = set(frame.loc[frame.annotation_code.isna(), "split_group"])
    return frame, forced_train


def assign_group_splits(frames, forced_train, seed, attempts=5000):
    """Require all selected view/classes in every split; fail rather than relax grouping."""
    combined = pd.concat(frames.values(), ignore_index=True)
    names = sorted(combined.split_group.unique())
    group_index = {group: i for i, group in enumerate(names)}
    class_keys = sorted(set(zip(combined.view, combined.class_name)))
    class_index = {key: i for i, key in enumerate(class_keys)}
    counts = np.zeros((len(names), len(class_keys)), dtype=int)
    for row in combined.itertuples():
        counts[group_index[row.split_group], class_index[(row.view, row.class_name)]] += 1
    groups_by_class = [np.flatnonzero(counts[:, i]) for i in range(len(class_keys))]
    rng = np.random.default_rng(seed)
    best, best_score = None, float("inf")
    forced = np.array([group in forced_train for group in names])
    for _ in range(attempts):
        assignment = np.full(len(names), -1)
        assignment[forced] = 0
        order = sorted(range(len(class_keys)), key=lambda i: (len(groups_by_class[i]), rng.random()))
        feasible = True
        for i in order:
            available = groups_by_class[i]
            present = set(assignment[available]) - {-1}
            missing = [s for s in range(3) if s not in present]
            unassigned = available[assignment[available] == -1].copy()
            if len(unassigned) < len(missing):
                feasible = False
                break
            rng.shuffle(unassigned)
            rng.shuffle(missing)
            for group, split in zip(unassigned, missing):
                assignment[group] = split
        if not feasible:
            continue
        open_groups = assignment == -1
        assignment[open_groups] = rng.choice(3, size=open_groups.sum(), p=TARGETS)
        split_counts = np.stack([counts[assignment == s].sum(axis=0) for s in range(3)])
        if not (split_counts > 0).all():
            continue
        score = np.abs(split_counts / counts.sum(axis=0) - TARGETS[:, None]).mean()
        for view in frames:
            columns = [i for i, key in enumerate(class_keys) if key[0] == view]
            score += np.abs(split_counts[:, columns].sum(axis=1) / counts[:, columns].sum() - TARGETS).mean()
        if score < best_score:
            best, best_score = assignment.copy(), score
    if best is None:
        raise ValueError("No class-complete group split found. Three groups is necessary but not always sufficient.")
    return {group: SPLITS[best[i]] for i, group in enumerate(names)}


def assign_image_splits(frame, seed):
    """Stratify individual images, keeping exact copies together but allowing code overlap."""
    rng = np.random.default_rng(seed)
    pieces = []
    for _, part in frame.groupby("class_name", sort=True):
        units = sorted(part.duplicate_group.unique())
        if len(units) < 3:
            raise ValueError("A 4+ class has fewer than three distinct image groups; cannot fill all splits.")
        rng.shuffle(units)
        n_val = max(1, int(round(len(units) * TARGETS[1])))
        n_test = max(1, int(round(len(units) * TARGETS[2])))
        mapping = {unit: ("validation" if i < n_val else "test" if i < n_val + n_test else "train")
                   for i, unit in enumerate(units)}
        pieces.append(part.assign(split=part.duplicate_group.map(mapping)))
    return pd.concat(pieces, ignore_index=True)


def prepare_experiments(manifest_path, ml_root, seed=4914):
    catalog, forced_train = load_catalog(manifest_path, ml_root)
    base, strict = {}, {}
    for view in ["interior", "exterior"]:
        frame = catalog[catalog.view.eq(view) & catalog.class_name.notna()].copy()
        counts = frame.class_name.value_counts()
        base[view] = frame[frame.class_name.isin(counts[counts.ge(4)].index)].copy()
        group_counts = base[view].groupby("class_name").split_group.nunique()
        strict[view] = base[view][base[view].class_name.isin(group_counts[group_counts.ge(3)].index)].copy()
        if strict[view].class_name.nunique() < 2:
            raise ValueError(f"Too few {view} classes for the 3+ groups experiment.")
    group_map = assign_group_splits(strict, forced_train, seed)
    experiments = {}
    for view_index, view in enumerate(["interior", "exterior"]):
        for variant in ["3plus", "4plus"]:
            key = f"{view}_{variant}"
            if variant == "3plus":
                frame = strict[view].assign(split=strict[view].split_group.map(group_map)).copy()
                policy = "4+ images and 3+ code/hash groups; groups kept together"
            else:
                frame = assign_image_splits(base[view], seed + view_index)
                policy = "4+ images; image-stratified, exact copies kept together, code overlap allowed"
            frame = frame.sort_values("raw_path").reset_index(drop=True)
            names = sorted(frame.class_name.unique())
            class_map = {name: i for i, name in enumerate(names)}
            frame["class_id"] = frame.class_name.map(class_map).astype("int64")
            splits = {name: frame[frame.split.eq(name)].copy().reset_index(drop=True) for name in SPLITS}
            for part in splits.values():
                if set(part.class_name) != set(names):
                    raise ValueError(f"Incomplete class coverage in {key}.")
                if not part.image_path.map(lambda p: Path(p).is_file()).all():
                    raise FileNotFoundError(f"Missing JPEGs in {key}.")
            if frame.groupby("duplicate_group").split.nunique().gt(1).any():
                raise ValueError(f"Exact duplicate leakage in {key}.")
            if variant == "3plus" and frame.groupby("split_group").split.nunique().gt(1).any():
                raise ValueError(f"Group leakage in {key}.")
            experiments[key] = {"frame": frame, "splits": splits, "class_names": names,
                                "class_to_id": class_map, "policy": policy, "seed": seed}
    return experiments


def experiment_tables(experiments):
    summaries, split_rows, overlap_rows = [], [], []
    for key, exp in experiments.items():
        frame, names = exp["frame"], exp["class_names"]
        summaries.append({"Experiment": key, "Classes": len(names), "Images": len(frame),
                          "Avg images/class": round(len(frame) / len(names), 2), "Split policy": exp["policy"]})
        for split, part in exp["splits"].items():
            split_rows.append({"Experiment": key, "Split": split, "Images": len(part),
                               "Classes": part.class_name.nunique(), "Percent": round(100 * len(part) / len(frame), 1)})
        for column in ["annotation_code", "split_group", "duplicate_group"]:
            grouping = frame.dropna(subset=[column]).groupby(column).split.nunique()
            overlap_rows.append({"Experiment": key, "Relationship": column,
                                 "Groups crossing splits": int(grouping.gt(1).sum())})
    return (pd.DataFrame(summaries).set_index("Experiment"),
            pd.DataFrame(split_rows).set_index(["Experiment", "Split"]),
            pd.DataFrame(overlap_rows).pivot(index="Experiment", columns="Relationship", values="Groups crossing splits"))


class PadResize:
    def __call__(self, image):
        return ImageOps.pad(image.convert("RGB"), (224, 224),
                            method=Image.Resampling.BILINEAR, color=PAD_COLOR)


def make_transform(training):
    steps = []
    if training:
        steps += [transforms.RandomHorizontalFlip(), transforms.RandomRotation(
            15, interpolation=InterpolationMode.BILINEAR, expand=True, fill=PAD_COLOR),
            transforms.ColorJitter(brightness=0.1, contrast=0.1, saturation=0.05)]
    steps.append(PadResize())
    if training:
        steps.append(transforms.RandomAffine(0, scale=(0.9, 1.0),
                     interpolation=InterpolationMode.BILINEAR, fill=PAD_COLOR))
    steps += [transforms.ToTensor(), transforms.Normalize(MEAN, STD)]
    return transforms.Compose(steps)


class MangoDataset(Dataset):
    def __init__(self, frame, training=False):
        self.frame = frame.reset_index(drop=True).copy()
        self.transform = make_transform(training)

    def __len__(self):
        return len(self.frame)

    def __getitem__(self, index):
        row = self.frame.iloc[index]
        with Image.open(row.image_path) as opened:
            image = ImageOps.exif_transpose(opened).convert("RGB")
        return self.transform(image), int(row.class_id)


def make_loader(exp, split, batch_size=16, seed=4914):
    frame = exp["splits"][split]
    sampler = None
    if split == "train":
        counts = frame.class_id.value_counts()
        weights = frame.class_id.map(1 / counts).to_numpy(copy=True)
        sampler = WeightedRandomSampler(torch.as_tensor(weights, dtype=torch.double),
            len(frame), replacement=True, generator=torch.Generator().manual_seed(seed))
    return DataLoader(MangoDataset(frame, split == "train"), batch_size=batch_size,
                      sampler=sampler, shuffle=False, num_workers=0,
                      generator=torch.Generator().manual_seed(seed))


class TransferClassifier(nn.Module):
    def __init__(self, backbone, feature_size, num_classes, dropout):
        super().__init__()
        self.backbone = backbone.requires_grad_(False).eval()
        self.head = nn.Sequential(nn.Dropout(dropout), nn.Linear(feature_size, 128),
                                  nn.ReLU(), nn.Dropout(dropout), nn.Linear(128, num_classes))

    def train(self, mode=True):
        super().train(mode)
        self.backbone.eval()  # Includes frozen BatchNorm statistics, not just weights.
        return self

    def forward(self, x):
        with torch.no_grad():
            features = self.backbone(x)
        return self.head(features)


def create_model(architecture, num_classes, dropout=0.35, pretrained=True):
    if num_classes < 2 or not 0 <= dropout < 1:
        raise ValueError("Need at least two classes and dropout in [0, 1).")
    if architecture == "ResNet50":
        base = models.resnet50(weights=models.ResNet50_Weights.IMAGENET1K_V1 if pretrained else None)
        width = base.fc.in_features
        base.fc = nn.Identity()
        backbone = base
    elif architecture == "VGG16":
        base = models.vgg16(weights=models.VGG16_Weights.IMAGENET1K_V1 if pretrained else None)
        width = 512
        backbone = nn.Sequential(base.features, nn.AdaptiveAvgPool2d(1), nn.Flatten())
    elif architecture == "EfficientNetB0":
        base = models.efficientnet_b0(weights=models.EfficientNet_B0_Weights.IMAGENET1K_V1 if pretrained else None)
        width = base.classifier[1].in_features
        backbone = nn.Sequential(base.features, nn.AdaptiveAvgPool2d(1), nn.Flatten())
    else:
        raise ValueError(f"Unknown architecture: {architecture}")
    return TransferClassifier(backbone, width, num_classes, dropout)


def classification_metrics(labels, logits, class_names):
    """Top-k accuracy counts images whose true cultivar is among the first k predictions.

    If k exceeds the number of model classes, use all classes. Break tied scores
    by class ID so top-1 agrees with argmax and the ranked lists are repeatable.
    """
    labels, logits = labels.cpu(), logits.detach().cpu()
    count = len(class_names)
    ranked = logits.argsort(dim=1, descending=True, stable=True)
    predicted = ranked[:, 0]
    cm = torch.bincount(labels * count + predicted, minlength=count * count).reshape(count, count)
    tp, support = cm.diag().float(), cm.sum(1)
    precision = tp / cm.sum(0).clamp_min(1)
    recall = tp / support.clamp_min(1)
    f1 = 2 * precision * recall / (precision + recall).clamp_min(1e-12)
    correct_at_rank = ranked.eq(labels[:, None])
    topk = {
        f"top{k}_accuracy": correct_at_rank[:, :min(k, count)].any(1).float().mean().item()
        for k in TOP_K_VALUES
    }
    metrics = {"accuracy": predicted.eq(labels).float().mean().item(),
               "macro_precision": precision.mean().item(), "macro_recall": recall.mean().item(),
               "macro_f1": f1.mean().item(),
               **topk, "output_classes": count,
               "classes_evaluated": int(support.gt(0).sum()), "images": len(labels)}
    per_class = pd.DataFrame({"class_name": class_names, "precision": precision.numpy(),
                              "recall": recall.numpy(), "f1": f1.numpy(), "support": support.numpy()})
    return metrics, per_class, cm


def evaluate_loader(model, loader, class_names, device):
    model.eval()
    total_loss, all_labels, all_logits = 0.0, [], []
    with torch.no_grad():
        for images, labels in loader:
            logits = model(images.to(device))
            total_loss += nn.functional.cross_entropy(logits, labels.to(device), reduction="sum").item()
            all_labels.append(labels)
            all_logits.append(logits.cpu())
    metrics, per_class, cm = classification_metrics(torch.cat(all_labels), torch.cat(all_logits), class_names)
    metrics["loss"] = total_loss / metrics["images"]
    return metrics, per_class, cm


def choose_device():
    return torch.device("cuda" if torch.cuda.is_available() else "mps" if torch.backends.mps.is_available() else "cpu")


def fit_experiment(exp, architecture, dropout=0.35, epochs=10, patience=3,
                   learning_rate=1e-3, batch_size=16, device=None, seed=4914):
    """Train on full training split; select checkpoint with validation only."""
    if epochs < 1 or patience < 1:
        raise ValueError("epochs and patience must be positive.")
    device = choose_device() if device is None else torch.device(device)
    random.seed(seed)
    np.random.seed(seed)
    torch.manual_seed(seed)
    model = create_model(architecture, len(exp["class_names"]), dropout).to(device)
    optimizer = torch.optim.AdamW(model.head.parameters(), lr=learning_rate, weight_decay=0.01)
    train_loader = make_loader(exp, "train", batch_size, seed)
    val_loader = make_loader(exp, "validation", batch_size, seed)
    best_loss, best_head, stale, history, best_epoch = float("inf"), None, 0, [], None
    for epoch in range(1, epochs + 1):
        model.train()
        total_loss, total_correct, seen = 0.0, 0, 0
        for images, labels in train_loader:
            images, labels = images.to(device), labels.to(device)
            optimizer.zero_grad(set_to_none=True)
            logits = model(images)
            loss = nn.functional.cross_entropy(logits, labels)
            loss.backward()
            optimizer.step()
            total_loss += loss.item() * len(labels)
            total_correct += logits.argmax(1).eq(labels).sum().item()
            seen += len(labels)
        validation, _, _ = evaluate_loader(model, val_loader, exp["class_names"], device)
        history.append({"epoch": epoch, "train_loss": total_loss / seen,
                        "train_accuracy": total_correct / seen,
                        **{f"val_{key}": value for key, value in validation.items()}})
        print(f"Epoch {epoch}: train loss {total_loss / seen:.3f}; validation loss {validation['loss']:.3f}; "
              + "; ".join(f"top-{k} {validation[f'top{k}_accuracy']:.1%}" for k in TOP_K_VALUES)
              + f"; macro F1 {validation['macro_f1']:.3f}", flush=True)
        if validation["loss"] < best_loss - 1e-5:
            best_loss, best_epoch, stale = validation["loss"], epoch, 0
            best_head = {key: value.detach().cpu().clone() for key, value in model.head.state_dict().items()}
        else:
            stale += 1
        if stale >= patience:
            break
    if best_head is None:
        raise ValueError("No finite validation checkpoint was produced; check training settings.")
    model.head.load_state_dict(best_head)
    model.eval()
    validation, _, _ = evaluate_loader(model, val_loader, exp["class_names"], device)
    return {"model": model, "architecture": architecture, "dropout": dropout,
            "history": history, "best_epoch": best_epoch, "validation": validation,
            "config": {"epochs": epochs, "patience": patience, "learning_rate": learning_rate,
                       "batch_size": batch_size, "seed": seed, "device": str(device),
                       "optimizer": "AdamW", "weight_decay": 0.01, "balanced_sampling": True}}


def save_run(result, exp, experiment_key, output_root, manifest_path):
    timestamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S%fZ")
    run_dir = Path(output_root) / f"{experiment_key}-{result['architecture']}-{timestamp}"
    run_dir.mkdir(parents=True, exist_ok=False)
    # Backbones are frozen official IMAGENET1K_V1 weights; store the learned head plus reconstruction metadata.
    model = result["model"]
    checkpoint = {"architecture": result["architecture"], "weights": "IMAGENET1K_V1",
                  "dropout": result["dropout"], "class_names": exp["class_names"],
                  "head": {key: value.cpu().clone() for key, value in model.head.state_dict().items()}}
    torch.save(checkpoint, run_dir / "head.pt")
    columns = ["raw_path", "sha256", "source_sha256", "annotation_code", "split_group",
               "duplicate_group", "class_name", "class_id", "view", "split"]
    metadata = {"experiment": experiment_key, "policy": exp["policy"],
                "architecture": result["architecture"], "weights": "IMAGENET1K_V1",
                "dropout": result["dropout"], "best_epoch": result["best_epoch"],
                "class_names": exp["class_names"], "config": result["config"],
                "preprocessing": PREPROCESSING, "torch_version": str(torch.__version__),
                "manifest_sha256": hashlib.sha256(Path(manifest_path).read_bytes()).hexdigest(),
                "history": result["history"], "validation": result["validation"],
                "split_rows": json.loads(exp["frame"][columns].to_json(orient="records"))}
    (run_dir / "experiment.json").write_text(json.dumps(metadata, indent=2), encoding="utf-8")
    return run_dir


def save_split_plan(experiments, output_root, manifest_path):
    """Persist the complete assignment before any model fitting in a fresh directory."""
    run_dir = Path(output_root) / ("split-plan-" + datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S%fZ"))
    run_dir.mkdir(parents=True, exist_ok=False)
    columns = ["raw_path", "sha256", "source_sha256", "annotation_code", "split_group",
               "duplicate_group", "class_name", "class_id", "view", "split"]
    payload = {"manifest_sha256": hashlib.sha256(Path(manifest_path).read_bytes()).hexdigest(),
               "experiments": {key: {"seed": exp["seed"], "policy": exp["policy"],
                   "class_names": exp["class_names"],
                   "rows": json.loads(exp["frame"][columns].to_json(orient="records"))}
                   for key, exp in experiments.items()}}
    (run_dir / "splits.json").write_text(json.dumps(payload, indent=2), encoding="utf-8")
    return run_dir / "splits.json"


def run_training(experiments, manifest_path, output_root, architectures=ARCHITECTURES,
                 dropout_rates=(0.35,), **fit_options):
    """Process models sequentially; dropout trials use the same splits, seed and full validation set."""
    results = {}
    for key, exp in experiments.items():
        for architecture in architectures:
            candidates = []
            for dropout in dropout_rates:
                print(f"\n{key} / {architecture} / dropout={dropout}", flush=True)
                result = fit_experiment(exp, architecture, dropout=dropout, **fit_options)
                run_dir = save_run(result, exp, key, output_root, manifest_path)
                result.pop("model").cpu()
                if torch.backends.mps.is_available():
                    torch.mps.empty_cache()
                result["run_dir"] = str(run_dir)
                candidates.append(result)
            selected = min(candidates, key=lambda item: item["validation"]["loss"])
            results[(key, architecture)] = {**selected, "dropout_trials": candidates}
    return results


def load_run(run_dir, device=None):
    device = choose_device() if device is None else torch.device(device)
    checkpoint = torch.load(Path(run_dir) / "head.pt", map_location="cpu", weights_only=True)
    model = create_model(checkpoint["architecture"], len(checkpoint["class_names"]), checkpoint["dropout"])
    model.head.load_state_dict(checkpoint["head"])
    return model.to(device).eval(), checkpoint["class_names"]


def evaluate_saved_runs(results, experiments, batch_size=16, device=None):
    device = choose_device() if device is None else torch.device(device)
    rows, details = [], {}
    for (key, architecture), result in results.items():
        model, names = load_run(result["run_dir"], device)
        exp = experiments[key]
        if names != exp["class_names"]:
            raise ValueError("Saved class mapping differs from the current experiment.")
        saved = json.loads((Path(result["run_dir"]) / "experiment.json").read_text())
        saved_test = {(row["raw_path"], row["sha256"]) for row in saved["split_rows"] if row["split"] == "test"}
        current_test = set(zip(exp["splits"]["test"].raw_path, exp["splits"]["test"].sha256))
        if saved_test != current_test:
            raise ValueError("Test membership changed since training; reload the original split.")
        metrics, per_class, cm = evaluate_loader(model, make_loader(exp, "test", batch_size), names, device)
        rows.append({"Experiment": key, "Architecture": architecture, **metrics})
        details[(key, architecture)] = {"per_class": per_class, "confusion": cm}
        (Path(result["run_dir"]) / "test_metrics.json").write_text(json.dumps(metrics, indent=2))
        model.cpu()
    return pd.DataFrame(rows), details


def predict_image(run_dir, image_path, top_k=20, device=None, actual_class=None):
    """Return ranked cultivar scores, optionally marking a known correct cultivar."""
    if isinstance(top_k, bool) or not isinstance(top_k, (int, np.integer)) or top_k < 1:
        raise ValueError("top_k must be a positive integer.")
    model, names = load_run(run_dir, device)
    if actual_class is not None:
        actual_class = " ".join(str(actual_class).upper().split())
        if actual_class not in names:
            raise ValueError(f"Cultivar {actual_class!r} is not in this model's class mapping.")
    with Image.open(image_path) as opened:
        image = ImageOps.exif_transpose(opened).convert("RGB")
    tensor = make_transform(False)(image).unsqueeze(0).to(next(model.parameters()).device)
    with torch.no_grad():
        logits = model(tensor)[0].cpu()
        ranked = logits.argsort(descending=True, stable=True)
        indices = ranked[:min(top_k, len(names))]
        probabilities = logits.softmax(0)[indices]
    predictions = pd.DataFrame({"rank": range(1, len(indices) + 1),
                                "class_name": [names[i] for i in indices.tolist()],
                                "score": probabilities.tolist()})
    predictions.attrs["output_classes"] = len(names)
    if actual_class is not None:
        predictions["is_correct_cultivar"] = predictions.class_name.eq(actual_class)
        predictions.attrs["actual_class"] = actual_class
        predictions.attrs["actual_rank"] = ranked.tolist().index(names.index(actual_class)) + 1
    return predictions
