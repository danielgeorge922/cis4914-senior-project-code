import sys
from pathlib import Path

import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
import build_split_manifest as bsm  # noqa: E402


def make_photo(root, split, category, cultivar, name):
    folder = root / ("train/augmented_data" if split == "train" else "test/preprocessed_data") / category / cultivar
    folder.mkdir(parents=True, exist_ok=True)
    (folder / f"{name}.jpg").write_bytes(name.encode())


def build(tmp_path):
    out = tmp_path / "out"
    out.mkdir(exist_ok=True)
    pd.DataFrame({"raw": ["CHAUSA"], "canonical": ["CHAUNSA"]}).to_csv(out / "cultivar_aliases.csv", index=False)
    return bsm.build(tmp_path / "split", out)


def make_cultivar(root, cultivar, train, test):
    for i in range(train):
        make_photo(root, "train", "fruit", cultivar, f"{cultivar}_{i}_orig")
        make_photo(root, "train", "fruit", cultivar, f"{cultivar}_{i}_aug1")
    for i in range(train, train + test):
        make_photo(root, "test", "fruit", cultivar, f"{cultivar}_{i}")


def test_val_comes_from_train_and_thin_cultivars_are_dropped(tmp_path):
    root = tmp_path / "split"
    make_cultivar(root, "Kent", train=20, test=5)
    make_cultivar(root, "Keitt", train=20, test=5)
    make_cultivar(root, "Sparse", train=2, test=1)  # 3 photos: under Daniel's 4-photo minimum
    out = build(tmp_path)
    assert set(out.cultivar) == {"KENT", "KEITT"}
    for _, group in out.groupby("cultivar"):
        specimens = group.drop_duplicates("specimen").split.value_counts()
        assert specimens.to_dict() == {"train": 18, "test": 5, "val": 2}
    assert out.groupby("specimen").split.nunique().max() == 1
    dropped = pd.read_csv(tmp_path / "out" / "dropped_cultivars.csv")
    assert dropped.cultivar.tolist() == ["SPARSE"]


def test_burst_shots_and_copies_are_one_specimen_on_one_side(tmp_path):
    root = tmp_path / "split"
    make_cultivar(root, "Kent", train=20, test=5)
    # Three shots 3 s apart plus a "(2)" copy: Kyle put two in train, two in test.
    make_photo(root, "train", "fruit", "Kent", "IMG_20210630_104250_orig")
    make_photo(root, "train", "fruit", "Kent", "IMG_20210630_104250_aug1")
    make_photo(root, "train", "fruit", "Kent", "IMG_20210630_104253_orig")
    make_photo(root, "test", "fruit", "Kent", "IMG_20210630_104256")
    make_photo(root, "test", "fruit", "Kent", "IMG_20210630_104250 (2)")
    make_photo(root, "test", "fruit", "Kent", "Kent_1022831")
    make_photo(root, "test", "fruit", "Kent", "Kent_1022831_0_jpg.rf.129eabe3")
    out = build(tmp_path)
    burst = out[out.raw_path.str.contains("IMG_")]
    assert burst.specimen.nunique() == 1
    assert burst.split.nunique() == 1
    assert burst[burst.raw_path.str.contains(r"\(2\)")].augmented.all()  # a download copy isn't scored twice
    roboflow = out[out.raw_path.str.contains("1022831")]
    assert roboflow.specimen.nunique() == 1
    assert roboflow[roboflow.raw_path.str.contains(".rf.")].augmented.all()
