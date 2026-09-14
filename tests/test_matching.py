"""Compare exact graph optimization to exhaustive candidate enumeration."""

from itertools import combinations, permutations
import random

import pytest

from gambitpairing.controllers.pairing.matching import (
    optimal_homogeneous,
    optimal_with_one_down,
)


@pytest.mark.parametrize("count", [6, 7])
@pytest.mark.parametrize("seed", range(5))
def test_optimizer_preserves_first_minimum_for_every_downfloater(count, seed):
    rng = random.Random(seed)
    pool = [object() for _ in range(count)]
    edges, weights = {}, {}
    for a, b in combinations(pool, 2):
        key = frozenset((a, b))
        edges[key] = (a, b) if rng.random() > 0.2 else None
        weights[key] = rng.randrange(5)

    def splits(players, size):
        for first in combinations(players, size):
            yield list(first), [p for p in players if p not in first]

    best = {}
    order = 0
    for first, second in splits(pool, count // 2):
        for transposition in permutations(second, len(first)):
            order += 1
            pairs = [edges[frozenset((a, b))] for a, b in zip(first, transposition)]
            if None in pairs:
                continue
            down = tuple(p for p in second if p not in transposition)
            cost = sum(weights[frozenset(pair)] for pair in pairs)
            candidate = cost, order, pairs, list(down)
            if down not in best or candidate[:2] < best[down][:2]:
                best[down] = candidate
    expected = [(v[2], v[3]) for v in sorted(best.values(), key=lambda v: v[1])]
    optimize = optimal_with_one_down if count % 2 else optimal_homogeneous
    actual = list(optimize(pool, edges, weights, splits, lambda: None))
    assert actual == expected
