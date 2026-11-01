import numpy as np


def softmax(logits: np.ndarray) -> np.ndarray:
    shifted = logits - logits.max(axis=-1, keepdims=True)
    exp = np.exp(shifted)
    return exp / exp.sum(axis=-1, keepdims=True)


def combine(probabilities: np.ndarray) -> np.ndarray:
    """Plain average of per-photo probabilities, shape (photos, classes) -> (classes,)."""
    return probabilities.mean(axis=0)


def apply_ranges(
    scores: np.ndarray, ranges: list[dict], measurements: dict[str, float], penalty: float
) -> np.ndarray:
    """Lower each cultivar's score once per measurement outside its known range, then renormalize."""
    scores = scores.copy()
    for index, cultivar_ranges in enumerate(ranges):
        for feature, value in measurements.items():
            low, high = cultivar_ranges.get(feature, (-np.inf, np.inf))
            if not low <= value <= high:
                scores[index] *= penalty
    return scores / scores.sum()


def top_k(scores: np.ndarray, k: int) -> list[tuple[int, float]]:
    order = np.argsort(scores)[::-1][:k]
    return [(int(index), float(scores[index])) for index in order]
