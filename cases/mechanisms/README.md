# Explicit synthetic accounting mechanisms

These are additional executable methodology checks. They do not change SV-01,
RQ-07 or LG-01 policy, derive a full ledger from raw receipts, or authorize an
actual payment. Complete compiler verification remains deferred.

| Source | Scenario-selected policy and independent checkpoint |
| --- | --- |
| [advance-issues.spl](advance-issues.spl) | RR-01 actual participant-prepayment funding within the quarter, with both issue and eligibility evidence observed strictly before the timestamp cutoff; selected funding is added to the opening pool before nonnegative pooled earnings are recovered. Opening 0 + issue 15,000; earned 10,000; recovered 10,000; payable 0; closing 5,000 |
| [reserve-vintage.spl](reserve-vintage.spl) | RR-02 separate return-reserve ledger: V1 opening 12 - linked actual returns 7 - authorized unused release 5 = 0; V2 opening 0 + authorized addition 20 = 20; aggregate closing 20. Next-period V2 actual returns 8 and unused release 12 close V2 at 0 |
| [correction-payments.spl](correction-payments.spl) | Supplied revised entitlement under a named synthetic restatement: original issued 100, revised 90, delta -10, independently supplied actual paid 80, remaining obligation 10 |

Each event has identity, scope, explicit scenario authority and relevant dates;
duplicate event identities are rejected by both native/Python typed decoders.
Wrong scope, absent authority, negative magnitudes and movements beyond available
balances block the mechanism and yield empty business output/state ports.

The bounded RR-01 advance policy uses the actual funded date as the economic
effective date, separately from the exact issue and eligibility-evidence
observation timestamps. Thus June 30 funding first observed July 2 belongs to Q2
when the pinned cutoff is July 3; June 30 scheduled funding actually disbursed
July 1 belongs to Q3. A schedule or due date cannot substitute for actual funding.
Issue IDs and actual disbursement IDs are independently unique. Supplied evidence
must identify that issue/disbursement and match agreement, participant, authorized
pool, source title, USD currency, `participation_prepayment` balance purpose,
amount and actual funded date. Source title identity remains in the audit while
the recovery balance and earnings are pooled. Both issue and evidence must be
available strictly before the cutoff. Late or cutoff-equal observations are
excluded with audit flags; a currently available in-period issue with no matching
funding evidence blocks. Available evidence that denies eligibility or disagrees
with the issue also blocks. The fixture uses June 30 funding and separate July 2
issue/evidence observations with a July 3 cutoff.

`Instant` accepts known-offset RFC3339 timestamps and compares normalized exact
UTC seconds, including arbitrary decimal subseconds; output renders canonical
UTC RFC3339. Date-only and naive timestamps, unknown `-00:00` offsets, leap
seconds and normalization outside Gregorian years 0001–9999 are rejected.
Selected issues are added to the opening balance before current nonnegative
pooled earnings are applied. This policy does not choose FIFO, intra-quarter
earnings chronology, other offsets, acquisition funding treatment, reversals,
true-ups or historical catch-up/reopening behavior. The reserve example chooses no stage at
which a contractual video reserve changes a receipt basis, earnings or cash
payable, and makes no event-time cap/deadline compliance claim. Its typed
`reserve_vintages` state retains agreement, participant, pool, currency, purpose,
vintage and balance for each vintage. The `reserve_vintage_ledger` report shows
the two separate numerical checkpoints alongside the aggregate `reserve_ledger`.
Each stable movement references a unique supplied evidence record: an authorized
addition, actual return or authorized unused release. Exact amount, effective
date, vintage and other scope dimensions must agree. Both movement and evidence
must have been observed strictly before the explicit timestamp cutoff; only the
effective date selects the half-open accounting period. Missing or reused
evidence, wrong purpose and unsupported cross-vintage borrowing block. The
input contract is a complete selected-period snapshot: supplied out-of-period
or cutoff-unavailable reserve records block, rather than being silently filtered.
The advance mechanism instead explicitly reports excluded unavailable issues.
The reserve settlement stages add funds, apply actual returns and release unused funds within
each vintage. They assert availability at those stages, not chronological caps.
This ledger is separate from the synthetic post-earnings payment holdback and
from the unresolved contractual video-return reserve. The correction
example accepts a revised entitlement as supplied; it does not recompute a
corrected historical period or select prospective recognition instead.

Supporting `*-bindings.json` files are typed mechanism inputs, not canonical
full-run packages. Run with:

```powershell
python -m spl_compiler mechanism advance-issues cases/mechanisms/advance-issues-bindings.json --output .lake/mechanisms/advance-demo
```

The runner compares emitted Lean execution, independent native IR interpretation
and Python reference evaluation, and exports typed IR and native audit trace.
Closing aliases can be passed between the named mechanism tests; a production
StateCell still needs canonical scope, period and policy-lineage validation.
The supplied RR-01/RR-02 research answers govern these bounded synthetic policies;
remaining questions and exclusions are recorded in
[the question log](../../docs/spl/implementation-questions.md). These examples do
not establish contractual approval or authorize a payment.
