"""Compare exact graph optimization to exhaustive candidate enumeration."""

from itertools import combinations, permutations
import random

import pytest

from gambitpairing.controllers.pairing.matching import (
    optimal_homogeneous,
    optimal_with_downs,
    optimal_with_one_down,
)


def _random_graph(count, seed, max_weight=5):
    rng = random.Random(seed)
    pool = [object() for _ in range(count)]
    edges, weights = {}, {}
    for a, b in combinations(pool, 2):
        key = frozenset((a, b))
        edges[key] = (a, b) if rng.random() > 0.2 else None
        weights[key] = rng.randrange(max_weight)
    return pool, edges, weights


def _splits(players, size):
    for first in combinations(players, size):
        yield list(first), [p for p in players if p not in first]


def _first_minimum_per_downfloater_set(pool, edges, weights, pairs_count):
    best = {}
    order = 0
    for first, second in _splits(pool, pairs_count):
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
    return [(v[2], v[3]) for v in sorted(best.values(), key=lambda v: v[1])]


@pytest.mark.parametrize("count", [6, 7])
@pytest.mark.parametrize("seed", range(5))
def test_optimizer_preserves_first_minimum_for_every_downfloater(count, seed):
    pool, edges, weights = _random_graph(count, seed)
    expected = _first_minimum_per_downfloater_set(pool, edges, weights, count // 2)
    optimize = optimal_with_one_down if count % 2 else optimal_homogeneous
    actual = list(optimize(pool, edges, weights, _splits, lambda: None))
    assert actual == expected


@pytest.mark.parametrize(
    "count, pairs_count", [(6, 2), (7, 2), (8, 2), (8, 3), (9, 3), (9, 2), (7, 1)]
)
@pytest.mark.parametrize("seed", range(5))
@pytest.mark.parametrize("max_weight", [5, 2])
def test_optimizer_preserves_first_minimum_for_every_downfloater_set(
    count, pairs_count, seed, max_weight
):
    # Low weights often make the direct S1/S2 pairing optimal (the shortcut).
    pool, edges, weights = _random_graph(count, seed, max_weight)
    expected = _first_minimum_per_downfloater_set(pool, edges, weights, pairs_count)
    actual = list(
        optimal_with_downs(pool, pairs_count, edges, weights, _splits, lambda: None)
    )
    assert actual == expected
