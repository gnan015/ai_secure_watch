import math
from collections import Counter


def calculate_entropy(value: str) -> float:
    """Calculate Shannon entropy for a string.

    Entropy measures how unpredictable a string looks. Random-looking tokens
    usually have higher entropy than normal words.
    """
    if not value:
        return 0.0

    character_counts = Counter(value)
    value_length = len(value)
    entropy = 0.0

    for count in character_counts.values():
        probability = count / value_length
        entropy -= probability * math.log2(probability)

    return entropy


def is_high_entropy(value: str, threshold: float = 4.0) -> bool:
    """Return True when a value looks random enough to be suspicious."""
    return calculate_entropy(value) >= threshold
