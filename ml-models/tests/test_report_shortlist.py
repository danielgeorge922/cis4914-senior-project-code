import json
import sys
from pathlib import Path

import pandas as pd
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
from report_shortlist import report  # noqa: E402


@pytest.fixture
def shortlist_csv(tmp_path):
    rows = [("q1", "A", ["A", "B", "C"]),   # right at rank 1
            ("q2", "B", ["A", "B", "C"]),   # rank 2
            ("q3", "C", ["C", "A", "B"]),   # rank 1
            ("q4", "A", ["B", "C", "A"])]   # rank 3
    path = tmp_path / "shortlist.csv"
    pd.DataFrame([{"query": q, "true": t, "shortlist": json.dumps(s)} for q, t, s in rows]).to_csv(path, index=False)
    return path


def test_scores_a_shortlist(shortlist_csv):
    metrics, _, _ = report(shortlist_csv)
    # Worked by hand: predictions A, A, C, B against truth A, B, C, A.
    assert metrics["top1_accuracy"] == 0.5
    assert metrics["top3_accuracy"] == 1.0
    assert metrics["macro_f1"] == pytest.approx(0.5)  # F1 per cultivar: A 0.5, B 0, C 1


def test_gemini_answers_reorder_the_shortlist(shortlist_csv, tmp_path):
    answers = tmp_path / "answers.jsonl"
    answers.write_text(json.dumps({"query": "q2", "ranking": ["B", "A", "C"]}) + "\n")
    metrics, _, _ = report(shortlist_csv, answers)
    assert metrics["top1_accuracy"] == 0.75
