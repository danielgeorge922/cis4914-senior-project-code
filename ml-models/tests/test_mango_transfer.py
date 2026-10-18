import importlib.util
import json
from pathlib import Path

import numpy as np
import pandas as pd
import pytest
import torch
from PIL import Image

spec = importlib.util.spec_from_file_location(
    "mango_transfer", Path(__file__).resolve().parents[1] / "scripts/mango_transfer.py",
)
mt = importlib.util.module_from_spec(spec)
spec.loader.exec_module(mt)


@pytest.fixture
def synthetic_catalog(tmp_path):
    records = []
    for view in ["interior", "exterior"]:
        for class_index, name in enumerate(["ALPHA", "BETA", "SPARSE"]):
            for photo in range(6):
                relative = f"{view}-{name}-{photo}.jpg"
                Image.new("RGB", (32, 24), (40 + photo * 20, 30 + class_index * 40, 90)).save(tmp_path / relative)
                records.append({"raw_path": relative, "sha256": relative, "source_sha256": "source-" + relative,
                    "completed_at": "2026-10-11", "annotation": {"cultivar": name, "view_type": view,
                    "specimen_code": f"{name}-{photo // 2 if name != 'SPARSE' else 0}"}})
    path = tmp_path / "annotations.jsonl"
    path.write_text("".join(json.dumps(record) + "\n" for record in records))
    return path, tmp_path


def test_four_selections_are_distinct_and_splits_are_repeatable(synthetic_catalog):
    manifest, root = synthetic_catalog
    first = mt.prepare_experiments(manifest, root, seed=17)
    second = mt.prepare_experiments(manifest, root, seed=17)
    assert set(first) == {"interior_3plus", "interior_4plus", "exterior_3plus", "exterior_4plus"}
    for key, exp in first.items():
        assert len(exp["class_names"]) == (2 if key.endswith("3plus") else 3)
        assert set(exp["frame"].class_id) == set(range(len(exp["class_names"])))
        pd.testing.assert_frame_equal(exp["frame"], second[key]["frame"])
        members = [set(part.raw_path) for part in exp["splits"].values()]
        assert len(set.union(*members)) == len(exp["frame"])
        assert all(not a & b for i, a in enumerate(members) for b in members[i + 1:])
        for part in exp["splits"].values():
            assert set(part.class_name) == set(exp["class_names"])
    strict = pd.concat([exp["frame"] for key, exp in first.items() if key.endswith("3plus")])
    assert strict.groupby("split_group").split.nunique().max() == 1
    broad = first["interior_4plus"]["frame"]
    assert broad.groupby("annotation_code").split.nunique().max() == 3


def test_image_split_keeps_exact_copies_together():
    frame = pd.DataFrame({"class_name": ["A"] * 6, "duplicate_group": ["d0", "d0", "d1", "d2", "d3", "d4"]})
    result = mt.assign_image_splits(frame, seed=4914)
    assert result.groupby("duplicate_group").split.nunique().max() == 1
    assert set(result.split) == set(mt.SPLITS)


def test_impossible_group_coverage_stops_instead_of_leaking():
    frame = pd.DataFrame({"class_name": ["A"] * 4, "view": ["exterior"] * 4, "split_group": ["g0"] * 4})
    with pytest.raises(ValueError, match="No class-complete"):
        mt.assign_group_splits({"exterior": frame}, set(), seed=1, attempts=10)


def test_sampler_assigns_equal_probability_mass_to_classes():
    frame = pd.DataFrame({"class_id": [0, 0, 0, 0, 1], "image_path": ["unused"] * 5})
    loader = mt.make_loader({"splits": {"train": frame}}, "train")
    weights = loader.sampler.weights.numpy()
    assert weights[frame.class_id.eq(0)].sum() == pytest.approx(weights[frame.class_id.eq(1)].sum())
    assert loader.sampler.replacement


def test_metrics_use_multiclass_scores_and_support():
    y = torch.tensor([0, 0, 1, 2])
    logits = torch.tensor([[5., 0., 0.], [5., 0., 0.], [5., 0., 0.], [0., 0., 5.]])
    metrics, details, cm = mt.classification_metrics(y, logits, ["A", "B", "C"])
    assert metrics["accuracy"] == pytest.approx(0.75)
    assert metrics["macro_f1"] == pytest.approx(0.6)
    assert details.support.tolist() == [2, 1, 1]
    assert cm.sum() == 4


def test_topk_counts_true_cultivar_at_each_ranking_boundary():
    # Six images place the correct cultivar at ranks 1, 3, 5, 10, 20, and 21.
    logits = torch.arange(24, 0, -1, dtype=torch.float32).repeat(6, 1)
    labels = torch.tensor([0, 2, 4, 9, 19, 20])
    metrics, _, _ = mt.classification_metrics(labels, logits, [f"C{i}" for i in range(24)])
    for k, hits in zip([1, 3, 5, 10, 20], [1, 2, 3, 4, 5]):
        assert metrics[f"top{k}_accuracy"] == pytest.approx(hits / 6)
    assert metrics["accuracy"] == metrics["top1_accuracy"]
    assert metrics["output_classes"] == 24


def test_topk_caps_at_class_count_and_breaks_ties_consistently():
    logits = torch.zeros(3, 3)
    labels = torch.tensor([0, 1, 2])
    metrics, _, _ = mt.classification_metrics(labels, logits, ["A", "B", "C"])
    assert metrics["accuracy"] == metrics["top1_accuracy"] == pytest.approx(1 / 3)
    for k in [3, 5, 10, 20]:
        assert metrics[f"top{k}_accuracy"] == 1.0
    assert metrics["output_classes"] == 3


def test_ranked_predictions_identify_correct_cultivar_inside_and_outside_list(monkeypatch, tmp_path):
    class FixedScores(torch.nn.Module):
        def __init__(self):
            super().__init__()
            self.logits = torch.nn.Parameter(torch.arange(24, 0, -1, dtype=torch.float32))

        def forward(self, images):
            return self.logits.unsqueeze(0).expand(len(images), -1)

    names = [f"C{i}" for i in range(24)]
    monkeypatch.setattr(mt, "load_run", lambda *args: (FixedScores(), names))
    image_path = tmp_path / "image.jpg"
    Image.new("RGB", (32, 24), "orange").save(image_path)

    predictions = mt.predict_image("unused", image_path, actual_class=" c19 ")
    assert predictions["rank"].tolist() == list(range(1, 21))
    assert predictions.class_name.tolist() == names[:20]
    assert predictions.is_correct_cultivar.sum() == 1
    assert predictions.iloc[-1].is_correct_cultivar
    assert predictions.attrs["actual_rank"] == 20
    assert predictions.score.is_monotonic_decreasing
    assert predictions.score.sum() < 1  # Scores retain the full model's softmax denominator.

    outside = mt.predict_image("unused", image_path, top_k=10, actual_class="C19")
    assert not outside.is_correct_cultivar.any()
    assert outside.attrs["actual_rank"] == 20
    assert len(mt.predict_image("unused", image_path, top_k=30)) == 24
    with pytest.raises(ValueError, match="class mapping"):
        mt.predict_image("unused", image_path, actual_class="NOT_A_MODEL_CLASS")
    with pytest.raises(ValueError, match="positive integer"):
        mt.predict_image("unused", image_path, top_k=0)


def test_training_uses_validation_only_and_checkpoint_reloads(synthetic_catalog, monkeypatch, tmp_path):
    manifest, root = synthetic_catalog
    exp = mt.prepare_experiments(manifest, root)["interior_3plus"]

    def tiny_model(architecture, num_classes, dropout=0.35, pretrained=True):
        return mt.TransferClassifier(
            torch.nn.Sequential(torch.nn.Conv2d(3, 4, 1), torch.nn.BatchNorm2d(4),
                                torch.nn.AdaptiveAvgPool2d(1), torch.nn.Flatten()),
            4, num_classes, dropout,
        )

    monkeypatch.setattr(mt, "create_model", tiny_model)
    real_make_loader = mt.make_loader
    accessed_splits = []

    def tracked_loader(experiment, split, *args, **kwargs):
        accessed_splits.append(split)
        return real_make_loader(experiment, split, *args, **kwargs)

    monkeypatch.setattr(mt, "make_loader", tracked_loader)
    result = mt.fit_experiment(exp, "ResNet50", epochs=2, patience=1, batch_size=4, device="cpu")
    assert "test" not in accessed_splits
    assert result["best_epoch"] in [1, 2]
    run = mt.save_run(result, exp, "interior_3plus", tmp_path / "runs", manifest)
    reloaded, names = mt.load_run(run, "cpu")
    assert names == exp["class_names"]
    for key, value in result["model"].head.state_dict().items():
        assert torch.equal(value.cpu(), reloaded.head.state_dict()[key])
    saved = json.loads((run / "experiment.json").read_text())
    assert len(saved["split_rows"]) == len(exp["frame"])
    assert saved["preprocessing"]["rgb"]
    for k in [1, 3, 5, 10, 20]:
        assert f"top{k}_accuracy" in saved["validation"]
        assert f"val_top{k}_accuracy" in saved["history"][0]
    results = {("interior_3plus", "ResNet50"): {"run_dir": str(run)}}
    scores, _ = mt.evaluate_saved_runs(results, {"interior_3plus": exp}, batch_size=4, device="cpu")
    test_metrics = json.loads((run / "test_metrics.json").read_text())
    for k in [1, 3, 5, 10, 20]:
        assert scores.iloc[0][f"top{k}_accuracy"] == test_metrics[f"top{k}_accuracy"]


def test_evaluation_preprocessing_is_deterministic_and_preserves_shape():
    image = Image.new("RGB", (80, 40), "red")
    transform = mt.make_transform(False)
    first, second = transform(image), transform(image)
    assert first.shape == (3, 224, 224)
    assert torch.equal(first, second)
    assert torch.isfinite(first).all()
    # The top-left pixel is padding, the center pixel is the original red image.
    assert not torch.equal(first[:, 0, 0], first[:, 112, 112])
