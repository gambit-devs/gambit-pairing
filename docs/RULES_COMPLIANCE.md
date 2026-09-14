# Rules and verification

The implementation targets the [FIDE Dutch rules effective February 2026](https://handbook.fide.com/chapter/C0403202602),
[FIDE tiebreak regulations effective March 2026](https://handbook.fide.com/chapter/TieBreakRegulations032026),
and [US Chess 2026 online rulebook](https://new.uschess.org/sites/default/files/media/documents/us-chess-rule-book-online-2026.pdf), Rule 34.
This is an implementation and regression-test scope, not federation certification.

## Standings

FIDE and US Chess calculations have separate unplayed-round adjustments.
Regression cases cover FIDE voluntary-unplayed cuts and dummy caps, recursive
direct encounter, round-robin forfeits, US Modified Median (including nine-round
cuts), cumulative and opposition cumulative. Rating calculations exclude
forfeits; ARO is excluded from ranking when participants are unrated.
FIDE round-robin standings do not use Buchholz. Unresolved ties share places
(1, 1, 3); display ordering within a shared place does not break the sporting tie.

New configurations record `rules_version: "2026"` and `unresolved_ties: "shared"`.
Older documents without a version are labeled `legacy-unspecified`; this label
does not select an emulation of historical rule calculations.

## Native GP Dutch

The native engine searches bracket candidates with resident exchanges,
heterogeneous brackets, downstream completion and ordered quality criteria.
Absolute colour restrictions apply before the final round too. Unplayed rounds
do not count as played encounters or colours. A player awarded an unplayed
full point is ineligible for a pairing-allocated bye.

The search is deadline-bounded. Expiry raises `PairingTimeoutException` and
restores input state; it never returns a heuristic pairing or switches to BBP.
The legacy `fide_strict` flag cannot disable these guarantees. Exhaustive search
can time out on difficult fields; no universal performance guarantee is made.

Homogeneous brackets/remainders with zero or one downfloater use independent
NetworkX minimum-weight matching to optimize colour costs. Exact completion
costs preserve the first Dutch resident exchange/transposition among optimal
candidates. With one downfloater, each candidate is still passed to downstream
bracket evaluation; the graph optimizer does not replace C5-C8 look-ahead.
Unavoidable colour-preference counts provide additional proven lower bounds.
Repeat-downfloat score differences include MDPs left in limbo, using an artificial
opponent score below the resident score; omitting them incorrectly rewarded
double-floating a protected MDP. See the [FIDE terms and definitions](https://tec.fide.com/wp-content/uploads/2025/02/2025-fide-dutch-terms-and-definitions.pdf).

## Backend boundaries

Models store configuration, player data and canonical round outcomes.
Tournament controllers own recording, undo, replay, pairing and standings.
Scheduled half/zero-point byes survive save/load and use the same replay path as
CLI simulation. Completed forfeits are excluded from played-opponent history.
Pairing workers operate on serialized copies; commit checks stale state, roster,
configuration, completed rounds, player data, assignment and absolute criteria.
Qt views consume standings projections rather than calculating sporting ranks.

## Verification

Run the normal suite with `python -m pytest -q`. Run differential tests against
the built, integrated BBP with `gambit-test bbp-reference --all`. To cross-check
against an independently obtained [BBP Pairings v6.0.0](https://github.com/BieremaBoyzProgramming/bbpPairings/releases/tag/v6.0.0),
override the engine explicitly:

```bash
GAMBIT_REFERENCE_BBP=/absolute/path/to/bbpPairings.exe python -m pytest -q tests/test_dutch_reference.py
```

The original reference matrix compares exact oriented pairings and byes across 315 rounds:
seven field sizes, three seeds, five rounds, and normal, unplayed-result and
reversed-initial-colour scenarios. It is supplemented by 210 rounds covering all
six rating distributions and five result patterns, and 14 rounds at 32/64 players
that previously timed out. Agreement on these 539 rounds is evidence, not a proof
for all tournament states. Direct pytest runs skip reference cases without
`GAMBIT_REFERENCE_BBP`; the CLI sets that variable from application discovery.

The independent in-process validator checks absolute criteria and produces
quality diagnostics, but does not prove global C5–C21 optimality. Reports therefore
explicitly mark incomplete full verification `not_verified`; CLI exit code 2
preserves that distinction. Neither a clean diagnostic report nor agreement
with BBP should be advertised as full FIDE/US Chess certification.
