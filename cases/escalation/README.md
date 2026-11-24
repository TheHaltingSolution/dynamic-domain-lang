# Ordered cumulative escalation

This selected C04 profile implements five separately named synthetic methods
using original ordered basis facts and a fixed, fully pinned bracket table. The
[independent oracle](../../oracles/escalation.py),
[design](../../docs/spl/escalation-design.md), [policy](policy.md) and
[neutral fixture](neutral.json) precede the executable source. The sourced
retroactive-policy question remains open; the synthetic repricing option does
not answer it.

Opening cumulative basis 80 and recognized earnings 8, followed by rows 30 and
40, cross a threshold 100 from rate .1 to .2:

| Selected method | Current result | Closing recognized |
| --- | ---: | ---: |
| `prospective_split` | 12 | 20 |
| `current_period_ending_rate` | 14 | 22 |
| `row_opening_rate` | 11 | 19 |
| `row_ending_rate` | 14 | 22 |
| `cumulative_reprice_delta` | 22 | 30 |

Marginal slices use exact crossed widths. Whole-period ending uses the period's
ending rate for every current row; row methods select each row's opening or
ending rate. Repricing computes cumulative basis times its current rate and
subtracts original recognized earnings once. It is a calculated entitlement
delta, not a payment of the cumulative total. Lower bounds are inclusive;
finite upper bounds are exclusive. No rounding is inferred.

Original event sequence controls economic order independently of physical
input order. Partitioning a row can change whole-row methods. For opening 80,
one 70 earns 7 at its opening rate, while 30+40 earns 11; row-ending 10+60 earns 13
instead of 14 from one 70. Tests preserve these distinctions instead of imposing
a universal split/merge law.

## Original history and fixed terms

The schedule validates every bracket, including source/evidence references,
unique IDs/sequences, zero-based contiguous positive-width partition, exactly
one final unbounded band and nondecreasing rates in `[0,1]`. The full table,
including scope, identity/version, original exact value spellings, dates and
references, is pinned in state. An ordinary carried run rejects method or table
amendments. Bracket physical order is normalized by explicit sequence.

Every original historical period and event is replayed from zero using the
same selected financial method as current facts. The source checks adjacent
history periods, unique case/event/source identities, scope/evidence/date
availability, declared opening/current/closing summaries and declared state
totals. Prior recognized earnings are recomputed; a supplied 80/8 snapshot is
disclosed as supplied history, not treated as an authenticated statement.
Genesis is explicitly zero/empty. Actual successor tests serialize the generic
closing cell, retain its real `prior_result_ref` and match the supplied neutral
predecessor summary to that exact snapshot. This is consistency of supplied
provenance, not cryptographic authentication of outside facts.

Approval/recording Dates satisfy `approved <= recorded <= as_of`. Exact
observations and evidence independently satisfy `< cutoff`. The named synthetic
fixed-table convention additionally requires table recording on/before every
replayed period opening and table observation strictly before its UTC midnight.
The adapter mechanically validates the Gregorian opening Date and transports
that explicit midnight Instant because the language has no Date-to-Instant
conversion. It does not decide table availability or calculate rates, slices,
earnings or replay totals; those comparisons and calculations run in SPL.
Historical facts remain supplied original reconstructions, not complete past
observation-time snapshots.

## Representation and evidence

The adapter tags exact numbers and encodes `unbounded` as `Option<Money<USD>>`.
Bracket numeric lexemes, original event basis strings and original timestamp
spellings accompany their exact values so normalization cannot erase source
changes. The full table pin rejects an equivalent-offset timestamp spelling
amendment, while Instant comparisons still use exact chronological values. An optional lexical record
preserves noncanonical historical summary spellings. Calculated current
summaries carry no such original text. Money/rate arithmetic uses exact numeric
fields; textual metadata supplies lineage only.

The typed row detail contains `kind`, a slice list and an optional selected
bracket/rate. Neutral export removes the unused alternative to match the
oracle's two distinct shapes. It also decodes numeric/sequence tags and removes
mechanical UTC/lexical transport fields. These are representation conversions,
not financial calculations. Every current row and every historical replay
exposes basis/recognized before and after, current result and rate/slices;
tests compare these and the full successor state with independent controls.

With the pinned environment and existing native kernel:

```powershell
python -m cases.escalation.build_modules
python -m unittest Tests.test_escalation_oracle Tests.test_escalation_modules -v
```

Five generated templates are intentionally unbound. The builder binds fresh
compiler/runtime/module identities for execution. Native test groups request
canonical `compare` (reference, native IR and native-emitted Lean), then
separately execute Lean from the Python emitter using the same decoded bindings.
Reference-only groups name their narrower execution scope. Atomic negative
examples compare source-native diagnostics; earlier wrapper validation can
reject other malformed physical inputs before financial execution.

This finite implementation uses lists, sorting, filters and nested folds, with
repeated history and identity scans. The generic input/resource guard is an
engineering boundary, not a measured capacity claim. It includes no term
amendment/reset authority, decreasing-rate/negative-delta policy, implicit
rounding, FX, issued/paid inference, bank execution or full contractual proof.
Issuance remains unissued; the generic wrapper does not assess payment evidence.
