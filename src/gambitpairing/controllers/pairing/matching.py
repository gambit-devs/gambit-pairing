"""Exact matching bounds with deterministic Dutch candidate-order selection.

NetworkX supplies the independent blossom optimizer. Its arbitrary optimal
matching is never returned: we select the first optimal resident split and
lexicographic S2 transposition using exact completion costs.
"""

from itertools import combinations

import networkx as nx


def optimal_homogeneous(pool, edges, weights, splits, check, costs=None):
    if costs is None:
        costs = {}

    def cost(first, second=None):
        key = frozenset(first), None if second is None else frozenset(second)
        if key not in costs:
            costs[key] = matching_cost(first, second)
        return costs[key]

    def matching_cost(first, second):
        check()
        graph = nx.Graph()
        graph.add_nodes_from(first)
        if second is None:
            choices = combinations(first, 2)
        else:
            graph.add_nodes_from(second)
            choices = ((a, b) for a in first for b in second)
        for a, b in choices:
            key = frozenset((a, b))
            if edges[key] is not None:
                graph.add_edge(a, b, weight=weights[key])
        matching = nx.min_weight_matching(graph)
        check()
        if len(matching) * 2 != len(graph):
            return None
        return sum(weights[frozenset(pair)] for pair in matching)

    def direct(first, second):
        # Cost of pairing first[i] with second[i], or None if any is illegal.
        # Weights are non-negative, so a direct cost equal to a known lower
        # bound is optimal and is also the lexicographically first completion.
        total = 0
        for a, b in zip(first, second):
            key = frozenset((a, b))
            if edges[key] is None:
                return None
            total += weights[key]
        return total

    optimum = None
    for first, second in splits(pool, len(pool) // 2):
        straight = direct(first, second)
        if optimum is None:
            if straight == 0:
                yield [edges[frozenset(pair)] for pair in zip(first, second)], []
                return
            optimum = cost(pool)
            if optimum is None:
                return
        if straight == optimum:
            yield [edges[frozenset(pair)] for pair in zip(first, second)], []
            return
        if cost(first, second) != optimum:
            continue
        remaining_cost = optimum
        pairs = []
        for i, a in enumerate(first):
            for j, b in enumerate(second):
                check()
                key = frozenset((a, b))
                if edges[key] is None:
                    continue
                rest = second[:j] + second[j + 1 :]
                completion = direct(first[i + 1 :], rest)
                if (
                    completion is None
                    or weights[key] + completion != remaining_cost
                ):
                    completion = cost(first[i + 1 :], rest)
                if (
                    completion is not None
                    and weights[key] + completion == remaining_cost
                ):
                    pairs.append(edges[key])
                    second = rest
                    remaining_cost = completion
                    break
            else:
                raise AssertionError("Optimal matching completion disappeared")
        yield pairs, []
        return


def optimal_with_one_down(pool, edges, weights, splits, check, costs=None):
    """Optimize each possible downfloater independently, retaining Dutch order."""
    yield from optimal_with_downs(
        pool, len(pool) // 2, edges, weights, splits, check, costs
    )


def optimal_with_downs(pool, count, edges, weights, splits, check, costs=None):
    """Optimize each possible downfloater set independently, retaining Dutch order.

    Brute force pairs S1 (``count`` players) into S2 and floats the rest of S2.
    For a fixed downfloater set only C10-C13 vary, so only its first minimum
    can be chosen. The next bracket must still choose between these
    candidates. No downstream criterion is replaced by the graph optimizer.
    """
    candidates = []
    positions = {p: i for i, p in enumerate(pool)}
    for down in combinations(pool, len(pool) - 2 * count):
        floated = set(down)
        selected = None

        def constrained_splits(_pool, _count):
            nonlocal selected
            for rank, (first, second) in enumerate(splits(pool, count)):
                check()
                if floated.isdisjoint(first):
                    selected = rank, first
                    yield first, [p for p in second if p not in floated]

        remaining = [p for p in pool if p not in floated]
        for pairs, _ in optimal_homogeneous(
            remaining, edges, weights, constrained_splits, check, costs
        ):
            rank, first = selected
            transposition = tuple(
                positions[b if a is p else a] for p, (a, b) in zip(first, pairs)
            )
            candidates.append(((rank, transposition), pairs, list(down)))
    for _, pairs, down in sorted(candidates, key=lambda item: item[0]):
        yield pairs, down
