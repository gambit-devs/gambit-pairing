"""Deadline-bounded Dutch candidate search, without heuristic repairs.

Candidate generation follows C.04.3 articles 3 and 4 (February 2026).
Working BSNs are local indices; no candidate mutates player history.
"""

from itertools import combinations

from gambitpairing.exceptions import NoPairingAvailableException
from gambitpairing.models.enums import Colour

from .dutch_rules import (
    FloatType,
    _assign_colors_fide,
    _get_color_imbalance,
    _get_color_preference,
    _get_float_type,
    _has_strong_color_preference,
    _is_topscorer,
    _meets_absolute_criteria,
    _played_colors,
)


def pair_round(
    players,
    previous,
    current_round,
    total_rounds,
    initial_color,
    check,
    pairing_numbers=None,
):
    ordered = sorted(players, key=lambda p: (-p.score, p.pairing_number))
    edges = {}
    for a, b in combinations(ordered, 2):
        check()
        edges[frozenset((a, b))] = (
            _assign_colors_fide(a, b, current_round, initial_color, pairing_numbers)
            if _meets_absolute_criteria(a, b, previous, current_round, total_rounds)
            else None
        )
    groups = []
    for player in ordered:
        if not groups or groups[-1][0].score != player.score:
            groups.append([])
        groups[-1].append(player)
    matching_caches = {}
    # Player histories are fixed during the search; evaluate rules once.
    preference = {p: _get_color_preference(p) for p in ordered}
    strong = {p: _has_strong_color_preference(p) for p in ordered}
    imbalance = {p: _get_color_imbalance(p) for p in ordered}
    last_two = {p: _played_colors(p)[-2:] for p in ordered}
    topscorer = {p: _is_topscorer(p, current_round, total_rounds) for p in ordered}
    floats = {
        (p, back): _get_float_type(p, back, current_round)
        for p in ordered
        for back in (1, 2)
    }

    def unplayed(player, index):
        outcomes = player.outcome_types
        return player.opponent_ids[index] is None or (
            index < len(outcomes) and outcomes[index] != "normal"
        )

    def bye_eligible(player):
        return not player.has_received_bye and not any(
            result == 1 and unplayed(player, i)
            for i, result in enumerate(player.results)
            if i < len(player.opponent_ids)
        )

    def splits(pool, count):
        first, second = pool[:count], pool[count:]
        yield first, second
        positions = {p: i for i, p in enumerate(pool)}
        for size in range(1, min(len(first), len(second)) + 1):
            exchanges = []
            for left in combinations(first, size):
                for right in combinations(second, size):
                    check()
                    key = (
                        sum(positions[p] for p in right)
                        - sum(positions[p] for p in left),
                        tuple(-positions[p] for p in reversed(left)),
                        tuple(positions[p] for p in right),
                    )
                    exchanges.append((key, left, right))
            for _, left, right in sorted(exchanges, key=lambda item: item[0]):
                selected = (set(first) - set(left)) | set(right)
                yield [p for p in pool if p in selected], [
                    p for p in pool if p not in selected
                ]

    def homogeneous(pool, count):
        if len(pool) >= 10:
            from .matching import optimal_homogeneous, optimal_with_downs

            # With each downfloater fixed, only C10-C13 vary within a
            # homogeneous bracket/remainder. Exact weights have no carries.
            # Weights depend only on the pair and base, so matching costs
            # are shared by every pool of the same size in this round.
            base = len(pool) + 1
            weights, costs = matching_caches.setdefault(base, ({}, {}))
            for a, b in combinations(pool, 2):
                edge = frozenset((a, b))
                if edges[edge] is not None and edge not in weights:
                    value = 0
                    for metric in quality([edges[edge]], [], pool, None)[1:5]:
                        value = value * base + metric
                    weights[edge] = value
            if len(pool) == 2 * count:
                yield from optimal_homogeneous(
                    pool, edges, weights, splits, check, costs
                )
            else:
                yield from optimal_with_downs(
                    pool, count, edges, weights, splits, check, costs
                )
            return
        seen = set()
        for first, second in splits(pool, count):
            for pairs, rest in pair_prefix(first, second):
                signature = frozenset((w.id, b.id) for w, b in pairs)
                if signature in seen:
                    continue
                seen.add(signature)
                yield pairs, rest

    def pair_prefix(first, pool):
        check()
        if not first:
            yield [], pool
            return
        a = first[0]
        for i, b in enumerate(pool):
            pair = edges[frozenset((a, b))]
            if pair is None:
                continue
            for tail, rest in pair_prefix(first[1:], pool[:i] + pool[i + 1 :]):
                yield [pair] + tail, rest

    def candidates(residents, mdps, pair_count, dominated=lambda head: False):
        if not mdps:
            yield from homogeneous(residents, pair_count)
            return
        # Residents share one score below every MDP, so the limbo alone fixes
        # the C6/C7 head of every candidate built from this choice.
        down_count = len(mdps) + len(residents) - 2 * pair_count
        for moved_count in range(min(len(mdps), len(residents), pair_count), -1, -1):
            for chosen in combinations(mdps, moved_count):
                check()
                limbo = [p for p in mdps if p not in chosen]
                limbo_scores = sorted((p.score for p in limbo), reverse=True)
                head = (
                    down_count,
                    tuple(limbo_scores)
                    + (residents[0].score,) * (down_count - len(limbo)),
                )
                if dominated(head):
                    continue
                for pairs, remainder in pair_prefix(chosen, residents):
                    if 2 * (pair_count - moved_count) > len(remainder):
                        continue
                    for extra, down in homogeneous(remainder, pair_count - moved_count):
                        yield pairs + extra, limbo + down

    def quality(pairs, down, residents, bye):
        assignments = [
            (p, color)
            for w, b in pairs
            for p, color in ((w, Colour.WHITE), (b, Colour.BLACK))
        ]
        top_pairs = [
            (p, color)
            for w, b in pairs
            if topscorer[w] or topscorer[b]
            for p, color in ((w, Colour.WHITE), (b, Colour.BLACK))
        ]
        c10 = sum(
            abs(imbalance[p] + (1 if color == Colour.WHITE else -1)) > 2
            for p, color in top_pairs
        )
        c11 = sum(last_two[p] == [color, color] for p, color in top_pairs)
        c12 = sum(
            bool(preference[p]) and preference[p] != color for p, color in assignments
        )
        c13 = sum(strong[p] and preference[p] != color for p, color in assignments)
        mixed = [
            (a, b) if a.score > b.score else (b, a)
            for a, b in pairs
            if a.score != b.score
        ]
        counts, differences = [], []
        for back in (1, 2):
            counts.extend(
                (
                    sum(
                        p in residents and floats[p, back] == FloatType.FLOAT_DOWN
                        for p in down
                    ),
                    sum(
                        floats[low, back] == FloatType.FLOAT_UP for _, low in mixed
                    ),
                )
            )
            differences.extend(
                (
                    tuple(
                        sorted(
                            [
                                high.score - low.score
                                for high, low in mixed
                                if floats[high, back] == FloatType.FLOAT_DOWN
                            ]
                            + [
                                p.score - residents[0].score + 1
                                for p in down
                                if p not in residents
                                and floats[p, back] == FloatType.FLOAT_DOWN
                            ],
                            reverse=True,
                        )
                    ),
                    tuple(
                        sorted(
                            (
                                high.score - low.score
                                for high, low in mixed
                                if floats[low, back] == FloatType.FLOAT_UP
                            ),
                            reverse=True,
                        )
                    ),
                )
            )
        c9 = (
            sum(unplayed(bye, i) for i in range(len(bye.opponent_ids)))
            if bye and down == [bye]
            else 0
        )
        return (c9, c10, c11, c12, c13, *counts, *differences)

    cache = {}
    feasible_cache = {}

    def feasible(pool):
        check()
        key = frozenset(pool)
        if key in feasible_cache:
            return feasible_cache[key]
        if not pool:
            return True
        if len(pool) % 2:
            answer = any(
                bye_eligible(p) and feasible([q for q in pool if q is not p])
                for p in pool
            )
        else:
            a = min(
                pool,
                key=lambda p: sum(
                    edges.get(frozenset((p, q))) is not None for q in pool if q is not p
                ),
            )
            answer = any(
                edges[frozenset((a, b))] is not None
                and feasible([p for p in pool if p is not a and p is not b])
                for b in pool
                if b is not a
            )
        feasible_cache[key] = answer
        return answer

    def solve(index, mdps):
        check()
        cache_key = (index, tuple(p.id for p in mdps))
        if cache_key in cache:
            return cache[cache_key]
        if not feasible(mdps + [p for group in groups[index:] for p in group]):
            cache[cache_key] = None
            return None
        if index == len(groups):
            if not mdps:
                return [], None, (0, ()), ()
            if len(mdps) == 1 and bye_eligible(mdps[0]):
                return [], mdps[0], (0, ()), ()
            return None
        residents = groups[index]
        bracket = sorted(mdps + residents, key=lambda p: (-p.score, p.pairing_number))
        best = best_key = None
        eligible_byes = [p.score for p in ordered if bye_eligible(p)]
        lowest_bye = min(eligible_byes) if len(ordered) % 2 and eligible_byes else 0
        maximum = min(len(bracket) // 2, len(residents))
        minimum_down = len(bracket) - 2 * maximum
        minimum_head = (
            minimum_down,
            tuple(p.score for p in bracket[-minimum_down:]) if minimum_down else (),
        )

        def dominated(head):
            return (
                best_key is not None
                and best is not None
                and best_key[0] == lowest_bye
                and head > best[2]
            )

        for pair_count in range(maximum, -1, -1):
            for pairs, down in candidates(residents, mdps, pair_count, dominated):
                check()
                down = sorted(down, key=lambda p: (-p.score, p.pairing_number))
                head = (len(down), tuple(p.score for p in down))
                if dominated(head):
                    continue
                child = solve(index + 1, down)
                if child is None:
                    continue
                tail, bye, next_head, _ = child
                metrics = quality(pairs, down, residents, bye)
                key = (bye.score if bye else 0, *head, next_head, metrics)
                if best_key is None or key < best_key:
                    best_key = key
                    best = pairs + tail, bye, head, key
                next_residents = groups[index + 1] if index + 1 < len(groups) else []
                next_pool = sorted(down + next_residents, key=lambda p: -p.score)
                next_minimum = len(next_pool) - 2 * min(
                    len(next_pool) // 2, len(next_residents)
                )
                minimum_next_head = (
                    (
                        next_minimum,
                        (
                            tuple(p.score for p in next_pool[-next_minimum:])
                            if next_minimum
                            else ()
                        ),
                    )
                    if next_residents
                    else (0, ())
                )

                # Each pair has only one slot of each colour. Excess preferences
                # are unavoidable, even in the ideal matching. Downfloaters may
                # absorb at most len(down) preferences. These are lower bounds,
                # not a relaxed acceptance criterion or a heuristic cutoff.
                def preference_bound(strong_only=False):
                    preferences = [
                        preference[p]
                        for p in bracket
                        if not strong_only or strong[p]
                    ]
                    return max(
                        0,
                        preferences.count(Colour.WHITE) - pair_count - len(down),
                        preferences.count(Colour.BLACK) - pair_count - len(down),
                    )

                lower_metrics = (
                    0,
                    0,
                    0,
                    preference_bound(),
                    preference_bound(True),
                    0,
                    0,
                    0,
                    0,
                    (),
                    (),
                    (),
                    (),
                )
                # Theoretical lower bounds prove perfection; no heuristic cap.
                if (
                    head == minimum_head
                    and next_head == minimum_next_head
                    and metrics == lower_metrics
                    and (bye is None or bye.score == lowest_bye)
                ):
                    cache[cache_key] = best
                    return best
            # Lower pair counts may permit a lower-scoring bye (C5 before C6).
            if best is not None and (best[1] is None or best[1].score == lowest_bye):
                break
        cache[cache_key] = best
        return best

    result = solve(0, [])
    if result is None:
        raise NoPairingAvailableException(
            f"No legal Dutch pairing exists for round {current_round}"
        )
    pairs, bye, _, _ = result
    pairs.sort(
        key=lambda pair: (
            -max(p.score for p in pair),
            -sum(p.score for p in pair),
            min(p.pairing_number for p in pair),
        )
    )
    return pairs, bye, [(w.id, b.id) for w, b in pairs], bye.id if bye else None
