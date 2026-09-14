"""Exact matching bounds with deterministic Dutch candidate-order selection.

NetworkX supplies the independent blossom optimizer. Its arbitrary optimal
matching is never returned: we select the first optimal resident split and
lexicographic S2 transposition using exact completion costs.
"""

from itertools import combinations

import networkx as nx


def optimal_homogeneous(pool, edges, weights, splits, check):
    def cost(first, second=None):
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

    optimum = cost(pool)
    if optimum is None:
        return
    for first, second in splits(pool, len(pool) // 2):
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


def optimal_with_one_down(pool, edges, weights, splits, check):
    """Optimize each possible downfloater independently, retaining Dutch order.

    The next bracket must still choose between these candidates. No downstream
    criterion is replaced by the graph optimizer.
    """
    candidates = []
    positions = {p: i for i, p in enumerate(pool)}
    for down in pool:
        selected = None

        def constrained_splits(_pool, count):
            nonlocal selected
            for rank, (first, second) in enumerate(splits(pool, count)):
                check()
                if down not in first:
                    selected = rank, first
                    yield first, [p for p in second if p is not down]

        remaining = [p for p in pool if p is not down]
        for pairs, _ in optimal_homogeneous(
            remaining, edges, weights, constrained_splits, check
        ):
            rank, first = selected
            transposition = tuple(
                positions[b if a is p else a] for p, (a, b) in zip(first, pairs)
            )
            candidates.append(((rank, transposition), pairs, [down]))
    for _, pairs, down in sorted(candidates, key=lambda item: item[0]):
        yield pairs, down
