import unicodedata


def normalize(term):
    return " ".join(unicodedata.normalize("NFKC", term).casefold().split())


def term_counts(predicted, expected):
    actual = {normalize(term) for term in predicted}
    gold = {normalize(term) for term in expected}
    return len(actual & gold), len(actual - gold), len(gold - actual)


def precision_recall_f1(tp, fp, fn):
    precision = tp / (tp + fp) if tp + fp else 0.0
    recall = tp / (tp + fn) if tp + fn else 0.0
    return {
        "precision": precision,
        "recall": recall,
        "f1": 2 * precision * recall / (precision + recall) if precision + recall else 0.0,
    }


def percentile(values, fraction):
    if not values:
        return None
    values = sorted(values)
    index = (len(values) - 1) * fraction
    low = int(index)
    high = min(low + 1, len(values) - 1)
    return values[low] + (values[high] - values[low]) * (index - low)
