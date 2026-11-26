# Explicit cumulative escalation variants

`SYNTHETIC-ESCALATION-01`, revision `1`. These five methods are separately
selected synthetic `research_assumption` variants. The sourced retroactive
repricing question remains open; the repricing variant below does not answer
or approve it. No bank payment, issuance, clawback or amendment is inferred.

Use nonnegative exact USD basis and a pinned bracket table. Brackets partition
the nonnegative line from zero without gap or overlap, with one final unbounded
band, unique explicit sequence and nondecreasing rates in `[0,1]`. Lower bounds
are inclusive and finite upper bounds exclusive. Exact threshold equality picks
the band beginning at that threshold. No implicit rounding applies.

Current original basis facts have unique IDs and explicit unique nonnegative
sequence, matching economic scope, effective dates inside the selected half-open
period, and observations/evidence strictly before cutoff. The supplied sequence
is economic order; physical input order has no effect. Rates and brackets must
be explicitly approved/recorded on or before the civil as-of Date. Date as-of
selection is separate from exact observation availability. Every retained
historical original and every declared bracket is validated.

This fixed-table profile additionally requires table recording on/before every
replayed period's opening Date and its observation strictly before that opening's
explicit UTC midnight. This named availability convention is synthetic; it
prevents applying newly captured terms to old history. Historical source facts
are replayed as supplied original history, not asserted to be an authenticated
historical issued statement or complete past observation-time snapshot.

Let B0 be opening cumulative basis, H0 opening recognized entitlement, b_i each
ordered current basis, C=sum(b_i), and B1=B0+C. Let r(x) select the bracket at x.

| Named method | Current calculated entitlement | Closing recognized entitlement |
| --- | --- | --- |
| prospective_split | Sum of current basis slices at each crossed band's rate | H0+current |
| current_period_ending_rate | C*r(B1) | H0+current; prior periods unchanged |
| row_opening_rate | Sum(b_i*r(basis immediately before row i)) | H0+current |
| row_ending_rate | Sum(b_i*r(basis immediately after row i)) | H0+current |
| cumulative_reprice_delta | B1*r(B1)-H0 | B1*r(B1) |

Opening basis 80 / recognized 8, current rows 30 then 40, and bands 0..100 at .1
and 100+ at .2 yield 12, 14, 11, 14 and 22 respectively. The repricing amount 22
is a synthetic calculated delta against original recognized 8, not a new
disbursement of the cumulative total 30. Negative repricing deltas and decreasing
rates require another policy and block this finite selection.

Event partition matters for whole-row methods. For the same opening 80, one row
70 at its opening rate earns 7, while rows 30+40 earn 11. Splitting into 10+60 gives
row-ending 13 instead of 14 from one row 70. Do not assert universal split/merge
invariance. Marginal split and current-period-ending totals preserve their stated
aggregate invariance within this exact, unrounded policy.

State pins method, scope, full original bracket table, boundary, cumulative basis,
recognized entitlement and complete original period/event history. Historical
snapshot 80/8 is explicitly supplied with original basis 80 and evidence; the oracle
recomputes that history instead of treating it as an issued or paid amount.
Genesis is explicitly zero/empty. Actual adjacent successor carry requires the
exact prior closing snapshot and matching predecessor summary. Method changes,
term amendments, bracket resets, history deletion and repeated original event IDs
block ordinary carry. Original event/source identities must not be renamed to
evade recognition history.
