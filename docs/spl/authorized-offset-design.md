# Original obligation revision and separately authorized offsets

23 November 2026. This independent C08/C13 composition design precedes executable
SPL. It supplies explicitly synthetic policy controls for payment-aware recovery,
without widening the earlier earnings-only returns method or inferring a legal
clawback right. Existing exact arithmetic, records, finite folds and state can
express this method; no necessary new compiler primitive is presumed.

The [neutral baseline](../../cases/authorized-offsets/neutral.json) retains
original basis200 at original rate .5, original gross100, a separately issued100
notice and independent actual payment80. An expressly authorized original-rate
returnbasis80 reverses40. Revised entitlement60 is separate from old issued100
and actual paid80. Old outstanding=max(60-80,0)=0 and potential overpayment20.
Neither the signed return40 nor potential20 automatically creates a refund or
offset claim.

The [policy](../../cases/authorized-offsets/policy.md) selects
`revise_original_obligation_only`: retain the signed reversal effect for audit,
revise the old obligation, and do not also deduct that effect from future earnings
as a second current loss. A separately scoped approval may convert at most
unallocated overpayment capacity into prospective claim principal. Total principal
ever authorized against that original remains bounded by its cumulative potential
overpayment, including principal already recovered. This prevents authorizing the
same paid excess twice after an earlier claim becomes fully recovered.

For original basis B/rate r, cumulative returned b and frozen actual payment P:

```text
original gross G = B*r
signed reversal = -(b*r)
revised entitlement R = G-b*r
old outstanding = max(R-P,0)
potential overpayment O = max(P-R,0)
free authorization capacity = O - all authorized original-overpayment principal
```

For a prospective claim eligible on Date t, calculate O(t) using only original
reversals whose recognition Date is <= t. Register new claims by eligible Date,
then unique sequence, and require prior authorized principal plus this claim to
be <= O(t). A later return cannot fund an earlier prospective claim. Exact-date
equality is included. Original rate is bounded to [0,1] in this selected profile.

The issued notice is independently supplied and equals G in this bounded profile.
Original payments are fully applied to that issue, cannot exceed its original
amount, and remain immutable under returns/repayments. The frozen payment snapshot
is labelled with its own as-of, rather than masquerading as a newly measured
payment population in every later period. New original-obligation payments would
require a separately authorized snapshot revision beyond this method.
Actual disbursements must precede the first recognition period; their frozen
snapshot capture may follow those historical transactions. Its as-of must be
available by the first run's cutoff and remains pinned across actual carry.

Authorized claim balance is principal less actual cash repayments and calculated
future-earning offsets. Actual cash and accounting offsets are distinct movements.
Apply actual cash first as the explicitly selected settlement-stage order, then
process fresh unissued earning rows by effective Date/unique sequence. These are
calculated offsets at the run boundary, not assertions that old bank transactions
occurred in that order. Each claim has prospective eligibility no earlier than its
recorded approval. For each earning row, available capacity cannot become negative;
unabsorbed claims carry forward.

| Control | Selected result |
| --- | --- |
| G100/reversal40/paid80; no offset approval; earning30 | Old outstanding0; unresolved potential20; new payable30 |
| Same, authorized claim20; complete-empty cash recovery | Earning offset20; new payable10; claim remaining0 |
| Authorized20; actual cash recovery5; earning10 | Cash5 / offset10 / remaining5 / payable0 |
| Competing source claim25; earning30; clawback-first | Original claim offset20, other10; remaining0/15 |
| Same; other-claim-first | Original claim offset5, other25; remaining15/0 |
| G100/reversal40/paid50 | Old outstanding10; overpayment0, no automatic offset capacity |

Competing other claims are independently supplied original amounts with their own
source references and authorization; this does not invent an actual funded advance
or a general creditor right. `clawback_first` assigns original-overpayment claims
priority0/other1; `other_claim_first` reverses those priorities. Unique supplied
sequences resolve claims within a priority; a tie blocks. Closed claims retain
their identities/principal so recovery cannot reset source authority capacity.

The neutral top-level structure is:

```text
schema_version = authorized-offsets-neutral/1
case_id, scope, period {start,end}, as_of, cutoff, policy, original_bundle
reversals[], revision_authorities[], offset_authorities[], future_earnings[]
cash_recoveries[], recovery_applications[], evidence[], opening_state, prior_result?
```

Scope is exactly `{contract_id,participant_id,pool_id,asset_id,currency}`, USD.
Policy pins `SYNTHETIC-AUTHORIZED-OFFSETS-01@1`, explicit priority_recipe,
`revise_original_obligation_only`, `cash_then_earning_offsets`,
`date_then_unique_sequence`, `supplied_utc_date`, `unapplied_cash=reject`,
`exact_no_rounding` and `research_assumption`. Money is nonnegative exact neutral
decimal/rational strings; signed amounts are calculated effects, never negative
raw return or payment magnitudes. No rounding or bank execution occurs.

`original_bundle` contains original measurement, issued notice, payment_snapshot
and other_claims. The original retains id/scope/basis/rate/measurement_date/
observed_at/source_ref/evidence_ref. Issued retains id/original_id/scope/amount/
issued_date/observed_at/source_ref/evidence_ref. Payment snapshot contains
`{as_of,payments,applications,evidence_ref}`. Payments retain actual paid_at and
stable disbursement IDs; applications conserve each payment exactly against the
original issue. Other source claims retain id/scope/amount/measurement_date/
observed_at/origin_ref/source_ref/evidence_ref. Source references are provided
provenance, not authenticated custody or professional approval.

Revision authority explicitly names original/issued IDs, current effective period,
approved/recorded civil Dates, observation, permitted reversal IDs and maximum
returned basis. Reversal records retain original ID, authority ID, raw returned
basis, original return Date and current recognition Date, source and evidence.
All declared authorities are checked, including unused records. Cumulative returned
basis cannot exceed original B. No revised original rate or replacement source
entitlement is silently accepted.

Offset authority retains id, claim_id, kind (`original_overpayment` or
`other_supplied_claim`), origin_id, scope, amount, priority, sequence,
eligible_from, current effective period, approved/recorded Dates, observed_at,
source_ref and evidence_ref. Approved/recorded dates must be <=as_of; eligibility
must be no earlier than recording and lie within the current period. All claim
IDs, authorizations and priority/sequence positions remain unique across history.
Source principal already used by another claim cannot be authorized again.

Future earnings retain id/scope/amount/effective_date/sequence/observed_at/
source_ref/upstream_ref/evidence_ref. `upstream_ref` is a specific original line
(`artifact#line`), unique across history/current facts. A relabelled old earning
cannot create fresh offset capacity or another payable. Only dates on/after a
claim's eligible_from permit prospective offsets.

Cash recovery records retain id/receipt_id/scope/amount/received_date/received_at/
observed_at/source_ref/evidence_ref. Applications retain id/cash_id/claim_id/scope/
amount/observed_at/source_ref/evidence_ref. Require full cash application, matching
UTC Date, received_at<=observed_at<cutoff and actual-cash-recovery support evidence.
Applications cannot exceed a claim's remaining amount and must follow receipt and
authority observations. Unapplied/excessive recognized cash blocks this policy.

Ordinary evidence has id/scope/observed_at/kind. Original payment-population
attestation additionally pins issued_id/as_of/payment_ids/disbursement_ids/
application_ids/paid_total. Current cash-population attestation additionally pins
period/cash_ids/receipt_ids/application_ids/cash_total. Exact original populations
must match these controls. Missing completeness is unknown, not numerical zero;
no final state is returned. Complete-empty views are explicitly []/[]/[]/0.
Population observations must be no earlier than every original cash/application
observation they summarize, and must precede the applicable cutoff.

Opening/closing state pins scope, purpose=`authorized_original_recovery`, policy
ID/revision, priority_recipe, full original_bundle, boundary, origin/source_case_id,
cumulative returned_basis, claims and original period_history. History entries
contain source_case_id/period/as_of/cutoff plus the six current source arrays, without
solved financial answers. The oracle replays all original movements to verify
the actual opening and each claim's authorized/cash/offset/remaining balance.
Historical source and support observations must still precede that original
period's cutoff; a later observation cannot silently satisfy an old run. Stored
source arrays are normalized by original ID; financial order uses the explicitly
supplied Dates/sequences. The civil as-of selects approvals and does not replace
the separate exact Instant observation cutoff.
Genesis has zero returned basis, no claims/history; adjacent prior_result requires
exact serialized prior closing and matching case/period/closing_state summary.
Optional external result_ref is provenance; actual canonical predecessor digests
remain a separate interface responsibility.

The standard-library oracle `authorized_offsets(data)` reports original gross,
signed reversal, old issued/paid snapshot, revised/outstanding/overpayment,
claim capacity and movements, actual cash recovery, earning offsets, calculated
unissued payable, unresolved capacity and exact closing state separately. No new
settlement actual-paid amount is inferred. Required controls include authority
absence, partial payment, complete-empty versus missing evidence, aliases,
overapplications, cash-before-offset stage, prospective dates, competing priority,
additional reversals, actual serialized carry and prevention of double recovery.

Verification: 25 standard-library unittest methods cover these controls, including
amount-changing priority and same-kind sequence choices, physical-row permutation,
exact submicrosecond cutoff, cash/source aliases, unused invalid authorities,
missing versus complete-empty populations, and a serialized three-period chain.
The oracle imports only datetime, fractions and re; tests reject solved financial
input fields. A frozen external source snapshot and separate-process test log are
reported with this slice's handoff. These controls do not claim whole-contract
approval, bank execution, legal recovery authority or compiler equivalence.
