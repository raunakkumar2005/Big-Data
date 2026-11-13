"""Deterministic reservoir sampling helper for bounded batch samples."""
from __future__ import annotations

import random
from typing import TypeVar

T = TypeVar("T")


def reservoir_sample(items: list[T], size: int, seed: int | None = None) -> list[T]:
    if size < 0:
        raise ValueError("reservoir size cannot be negative")
    rng = random.Random(seed)
    reservoir: list[T] = []
    for index, item in enumerate(items):
        if index < size:
            reservoir.append(item)
        elif size and rng.randrange(index + 1) < size:
            reservoir[rng.randrange(size)] = item
    return reservoir
