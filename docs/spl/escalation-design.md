# Independent ordered escalation controls

23 November 2026. This C04 oracle/design precedes executable SPL and uses only
standard-library exact arithmetic. It extends selected synthetic method controls,
not language primitives. The [policy](../../cases/escalation/policy.md) names five
variants explicitly; no default crossing-row or retroactive interpretation is
inferred. The external sourced retroactive-policy question remains open.

The [neutral fixture](../../cases/escalation/neutral.json) preserves opening
cumulative basis 80 and recognized entitlement 8, supported by an original
historical period containing basis 80 from zero. Current ordered rows are 30 and 40.
Brackets are 0..100 at .1 and 100+ at .2, with lower-inclusive equality. All exact
source values, scopes, row IDs, sequence, dates and evidence remain inputs.

For opening B0/H0 and current rows b_i, let B1=B0+sum(b_i), and r(x) be the
lower-inclusive bracket rate at x:

| Method | Current result | Baseline | Closing recognized |
| --- | --- | --- | --- |
| prospective_split | Exact widths crossed in each marginal band times its rate | 12 | 20 |
| current_period_ending_rate | sum(b_i)*r(B1) | 14 | 22 |
| row_opening_rate | Sum b_i*r(before row i) | 11 | 19 |
| row_ending_rate | Sum b_i*r(after row i) | 14 | 22 |
| cumulative_reprice_delta | B1*r(B1)-H0 | 22 | 30 |

The first four methods leave historical recognized earnings unchanged and add
only current results. The fifth deliberately reprices the full cumulative basis,
then subtracts the original recognized total once. It is a synthetic delta,
not a new payment or historical contractual approval. This finite profile selects
nondecreasing rates and rejects negative repricing deltas; decreasing-rate and
negative-adjustment policies are separate questions.

Each period's original events have unique explicit nonnegative sequences.
Physical permutation preserves results. Partition changes can change whole-row
rates: with opening 80, one row 70 at its opening rate gives 7, whereas 30+40 gives 11;
row-ending 10+60 gives 13 versus 14 for one 70. Marginal split, current-whole-ending
and cumulative repricing retain their own aggregate properties. A universal
split/merge assertion would erase the contractual distinction being tested.

The exact top-level neutral shape is:

```text
schema_version = escalation-neutral/1
case_id, scope, period {start,end}, as_of, cutoff, policy
bracket_table, events[], evidence[], opening_state, prior_result?
```

Economic scope is exactly
`{contract_id,participant_id,pool_id,asset_id,currency}`, with USD currency.
`policy` is `{id,revision,method,equality,rounding,evidence_class,table_availability}` selecting
`SYNTHETIC-ESCALATION-01@1`, one of the five named methods, `lower_inclusive`,
`exact_no_rounding`, `research_assumption` and
`before_all_period_openings_utc`.

`bracket_table` has `{id,version,scope,effective,approved_date,recorded_date,
observed_at,source_ref,evidence_ref,brackets}`. Its complete effective interval
covers the original historical periods and current period. Approval/recorded
Dates satisfy `approved_date <= recorded_date <= as_of`. Exact observations and
evidence separately satisfy `< cutoff`; no recording Instant or ambient timezone
is inferred. The named fixed-table availability policy additionally requires
table recording on/before each replayed period opening and its explicit
observation before that opening's declared UTC midnight. Newly available terms
cannot silently determine old history. Historical original facts are still
supplied reconstructions, not authenticated past observation-time snapshots.
Each bracket has
`{id,sequence,lower,upper,rate,source_ref,evidence_ref}`, with exact nonnegative
strings and upper either an exact finite bound or literal `unbounded`.
Sequences are unique nonnegative integers. Bands start at zero, are contiguous,
have positive finite width and exactly one final unbounded band. Rates are
nondecreasing in `[0,1]`. The state pins the full original table; changing its
amounts, scope, identity, source/evidence or dates is an amendment, not ordinary
carry. Physical bracket order alone is normalized by explicit sequence.

Each original event has
`{id,scope,basis,sequence,effective_date,observed_at,source_ref,evidence_ref}`.
Its effective date lies in its declared period. All retained original IDs and
source references remain unique across history/current facts, so a previously
recognized basis cannot be counted again under another period. The selected
complete-period view rejects out-of-period rows rather than silently excluding
them. Evidence records are `{id,scope,observed_at,kind}`.

Opening/closing state has:

```text
scope, purpose = cumulative_escalation, policy_id, policy_revision, method
bracket_table, boundary, origin, source_case_id
cumulative_basis, recognized_entitlement, period_history[]
```

Each historical period is
`{source_case_id,period,opening_basis,opening_recognized,events[],current_result,
closing_basis,closing_recognized}`. The financial oracle independently replays
those original event rows under the pinned named method and table. Its first
history starts at zero basis/recognized entitlement, periods are adjacent, and
each history result must reconcile exactly to the next opening and the declared
state totals. No issued or paid status is inferred from recognized earnings.

Genesis is zero/empty with origin/source_case_id `genesis`. Baseline origin
`supplied_history` discloses the historical source snapshot and does not claim
an actual compiler run. Tests must additionally execute real oracle genesis80→8
followed by an adjacent30+40 run under each method. Ordinary `prior_result`
origin requires exact serialized predecessor state and matching
`{source_case_id,period,closing_state,result_ref?}` summary. Optional external
result_ref is supplied provenance, not a canonical digest computed or
authenticated by the oracle. Canonical actual predecessor metadata remains a
separate interface responsibility.

`escalation(data)` returns complete per-row basis before/after, selected
bracket/rate or marginal slices, current result, opening/closing recognized
earnings and exact state. `exact_json` preserves neutral exact Fraction values
for carry. Required tests cover all five hand controls, equality, ordered row
partition effects, zero/empty facts, exact fractional widths, duplicate/source
identity, bracket gaps/overlap/rates, as-of/effective/cutoff boundaries, full
historical replay, method/bracket amendment rejection and actual adjacent carry.

Independent authoring verification on 23 November 2026: `python -m unittest
Tests.test_escalation_oracle -v` passed all 17 test methods in 0.028 seconds.
This records neutral controls only. Native, emitted and canonical execution
require separate implementation and comparison evidence.
