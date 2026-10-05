import importlib.util
from pathlib import Path
from unittest.mock import Mock

import pytest

spec = importlib.util.spec_from_file_location(
    "download_hugging_face", Path(__file__).resolve().parents[1] / "scripts/download_hugging_face.py"
)
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)


@pytest.fixture
def download_mock(monkeypatch):
    mock = Mock()
    monkeypatch.setattr(module, "snapshot_download", mock)
    monkeypatch.setattr(module, "load_dotenv", Mock())
    return mock


def test_defaults_are_pinned_and_independent_of_working_directory(download_mock, tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    module.download()
    download_mock.assert_called_once_with(
        repo_id="earl562/mango-varieties", repo_type="dataset",
        revision="f482454c26bcab8137b0eed3e45317e8bf6ff260",
        local_dir=module.ML_ROOT / "data/raw/hugging_face_data",
        allow_patterns=None, max_workers=4,
    )
    module.load_dotenv.assert_called_once_with(module.ML_ROOT.parent / ".env")


def test_selected_splits_and_relative_output(download_mock, tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    module.download("raw", ["train", "validation"])
    args = download_mock.call_args.kwargs
    assert args["local_dir"] == tmp_path / "raw"
    assert args["allow_patterns"] == [
        "README.md", ".gitattributes", "data/train-*.parquet", "data/validation-*.parquet",
    ]


def test_rerun_reuses_same_snapshot(download_mock, tmp_path):
    module.download(tmp_path)
    module.download(tmp_path)
    assert download_mock.call_args_list[0] == download_mock.call_args_list[1]


def test_interruption_prints_resume_command(download_mock, monkeypatch, capsys):
    monkeypatch.setattr("sys.argv", ["download_hugging_face.py"])
    download_mock.side_effect = KeyboardInterrupt
    assert module.main() == 130
    assert "Rerun the same command" in capsys.readouterr().out
