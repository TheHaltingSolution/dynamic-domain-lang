# Independent first-dollar merchandising controls

23 November 2026. This oracle/design precedes executable SPL and implements the
selected proposed RR-04 trigger-period recognition workflow for `B-C04-RETRO`,
with original-knowledge, obligation and replay controls. The
[policy](../../cases/merchandising-reprice/policy.md) and
[neutral facts](../../cases/merchandising-reprice/neutral.json) retain synthetic
accounting choices separately from the source economic lane. No future SPL,
compiler evaluator, projection helper or existing financial oracle is imported.

The primary reference is the [filed *Unique* agreement](https://www.sec.gov/Archives/edgar/data/1410132/000101376207002025/ex1014.htm),
§3.2(a)(i)–(v), §3.2(c), §3.2(d)(i)–(ii)(a) and Exhibit CB, printed pp.13–17.
Source economics are the first-dollar tiers, multiplier construction, selected
license deduction and CB adjustment boundary. Recognition timing, synthetic
figures, complete original views and the exact booking route are proposed
research assumptions, not historical accounts or professional approval.

The original external reviews are pinned by SHA-256 in `research`:
[RR-04](</C:/Projects/Film_TV_participation_dynamic_DSL/ResearchAgent/documents/SPL_RR04_Completion_Decisions.md:25>)
and [LD-03](</C:/Projects/Film_TV_participation_dynamic_DSL/ResearchAgent/documents/SPL_LD03_Completion_Review.md:134>).
Public source inspection confirmed the economic distinctions. Funding Charge
remains a supplied evidenced amount; its interest derivation is outside this
slice. No public source was treated as approval of this fixture's recognition
workflow, corrected-threshold treatment or original private accounts.

## Equations and independent discriminators

For original production C, authorized production-charge rate h, supplied Funding
Charge F, tier multiplier m, known box observation B and first-dollar rate r:

```text
production charge = C*h
tier threshold(m) = C*m + C*h + F
license NMI_i = qualifying_cash_i * (1-.30)    selected zero other adjustments
row target_i = NMI_i * r(B)
row delta_i = row target_i - already recognized_i
current earnings = sum row delta for current earned period
catch-up = sum row delta for older earned periods
new recognition = current earnings + catch-up
recognized unissued = cumulative recognized - original visible issue total
issued outstanding = original visible issues - actual applied payments
total unpaid = recognized unissued + issued outstanding
```

Here C=40m, h=.15 and F=1m give 77m/87m/107m. Treating 47m as the multiplication
base would wrongly give 94m at the second tier. The source inputs contain no
threshold result. At 86,999,999.99 the rate remains .065; at 87m equality it is
.075. NMI 7k/14k/3.5k yields original recognized Q1/Q2 455/910, revised row
allocations 525/1,050 and deltas 70/140. Q3 current 262.50 plus catch-up 210
recognizes 472.50, giving cumulative 1,837.50.

Actual old issued 1,365 and actual bank-paid 1,310 remain separate from these
targets. Old issued arrears are 55, unissued recognized is 472.50 and unpaid
total is 527.50. Hand controls exclude prospective-only 317.50, double-recognition
737.50, and paid-as-prior-entitlement 582.50. An additional actual payment 55
changes arrears to zero and total unpaid to 472.50 while catch-up remains 210.
The financial base of a catch-up is recognized entitlement, never paid cash.

## Exact neutral schema

`merchandising-reprice-neutral/1` has these exact top-level fields:

```text
case_id, scope, policy, research, terms, cost_basis, qualifications, cb_switch
run {view_id,mode}, periods[], views[], receipts[], box_office[]
issues[], payments[], applications[], populations[], no_default[], evidence[]
opening_state, prior_result?
```

Scope is `{contract_id,participant_id,pool_id,asset_id,currency}`, USD. Original
IDs are opaque nonempty Text in this neutral model; they are not globally
reclassified as SPL typed IDs. Amounts are exact nonnegative decimal/rational
strings. There is no implicit rounding or automatic withholding. The finite
profile allows 8 periods/views, 32 receipts, 16 box observations, 8 full original
issue events, 32 actual disbursements and 64 applications.

`policy` pins `RR04-MERCHANDISING-CATCHUP-01@1`, method
`trigger_period_catchup`, `complete_approved_zero_cb_credit`,
`exact_no_rounding`, negative-adjustments=`reject`,
`cash_date_basis=supplied_utc_date`, research_assumption and proposed review.
Research retains review hashes, primary URL and exact clause locator.

Each ordinary source record retains `id,scope,observed_at,source_ref,evidence_ref`.
Evidence retains `id,scope,kind,approved,observed_at,source_ref`. Approval is a
supplied synthetic source finding, not a professional-review claim. Every source
and its evidence must be available before the applicable exact cutoff. The
following additional fields define the original record kinds:

| Record | Additional original fields |
| --- | --- |
| terms | version, effective, production_charge_rate, license_deduction_rate, multipliers, rates, approved, recorded_date |
| cost_basis | production_cost, funding_charge |
| qualifications | integral graphic_units/comics_rank, units_date/rank_date/photography_date, feature_produced, feature_released, approved |
| cb_switch | complete, approved, effective_date, receipt_ids, credit_line_ids, prior_owner_entitlement, prior_credit_total, removed_from_defined_receipts, included_in_nmi |
| period | period `{start,end}` |
| view | source_case_id, period_id, mode, as_of, cutoff, coverage_end, recognition_id, approved |
| receipt | period_id, amount, received_date, recognition_date, qualifying, lane, receipt_ref |
| box_office | gross, effective_date, recorded_date, metric |
| issue | version, recognition_id, amount, issued_date |
| payment | bank_disbursement_id, amount, paid_date |
| application | payment_id, issue_id, amount, applied_date |
| no_default | view_id, approved, not_in_material_default |

License `receipt_ref` identifies a specific original `artifact#line`. Re-aliasing
that cash line under a new row ID blocks. Bank disbursement IDs likewise remain
unique; source aliases cannot create original payments or applications twice.
The lane is exclusively `third_party_license`. Nonqualifying current cash remains
visible in cash/population controls but contributes zero NMI. Other picture/scope
or unsupported media/metric inputs block rather than contaminate this lane.
The box metric is exactly `Daily_Variety_US_Canada_theatrical_cumulative`.

Every population record additionally retains `view_id,complete,receipt_coverage,
receipt_ids,receipt_total,adjustment_ids,adjustment_total,box_office_ids,issue_ids,
issue_total,payment_ids,disbursement_ids,payment_total,application_ids,
application_total`. Receipt coverage starts at the first supplied period and ends
at that view's coverage_end. Banking/issue/application visibility uses its exact
view cutoff independently. The explicit complete-zero adjustment population is
[]/0; it is not inferred from absent expense/guild/royalty facts. CB completeness
is separately explicit. Complete controls enumerate raw originals and their
separate source totals; they never supply computed targets, catch-up or earnings.

## Historical knowledge, previews and original accounting events

Periods are adjacent original calendar records. Each has one approved view with
its own civil as-of Date, exact observation cutoff and receipt-coverage end.
Final views cover the whole period; a preview covers a strict known prefix and
has no recognition ID. The civil as-of selects effective/recorded box evidence;
the separate exact cutoff selects observation availability. This finite profile
uses supplied UTC civil Dates for cash/accounting chronology and UTC midnight
coverage checks; no ambient timezone or clock is inferred. A source adapter may
mechanically transport Gregorian UTC midnights, but may not calculate any money
or choose a box/rate/winner.

Replay Q1 at April 3: rate .065, recognition 455, complete-empty known issues and
payments. The April 15 issue and April 20 payment do not enter that snapshot.
Replay Q2 at July 3: recognition 910, only Q1's old issue/payment known, issued
455, paid 400 and unissued recognized 910. The July 15 issue/payment events first
enter the Q3 accounting view. Then Q3 October 3 knows both original issue versions
and their actual applications. No future accounting event feeds an earlier
calculation, even though the current source ledger retains those originals.

The September 10 pre-trigger preview uses complete known receipt coverage only
through September 9 and excludes the future box trigger. It calculates current
candidate 227.50 and candidate total unpaid 282.50, while actual finalized
recognized entitlement stays 1,365 and `recognized_this_run=0`. Its status is
preview, `consumable_state=false`, `closing_state=None`, and recognition_history
contains only Q1/Q2. These are independent control outputs; a canonical source
must preserve non-consumability through its preview interface, not send JSON null
as an ordinary required SPL input or invent full future-period completeness.

This bounded profile requires original receipt observations by their original
view cutoff and nondecreasing original box records known within their effective
period. Late historical receipts and corrected threshold observations therefore
fail with a separate-variant diagnostic. That prevents inventing the unresolved
correction/loss policy. Observation equality at cutoff is excluded with exact
fractional-second comparisons.

Original full issues reference finalized recognition IDs and equal the original
recognition amount; their UTC Date starts no earlier than the original cutoff.
They cannot be silently replaced by current repriced row targets. Actual payments
are separately evidenced positive bank disbursements. Applications must fully
conserve each visible payment and stay within the original issue, with correct
issue/payment/application dates and observations. Missing complete population
evidence raises `MR_COMPLETE_POPULATION_REQUIRED` with
`payment_evidence_status=no_event_supplied`; no result/state or numerical paid
default is returned. This does not imply a new issue or bank execution.

## Recognition state and verification

Closing state pins scope, purpose=`first_dollar_merchandising`, policy, research,
terms, original cost/qualification/CB facts, boundary, origin/source_case_id,
last_view_id, per-original-receipt recognized amounts, recognition_history,
known_issued, actual_paid, issued_outstanding, recognized_unissued and original
source groups. Source groups retain original per-view cutoffs and raw records,
normalized by original ID. Every opening is reconstructed independently from
original prior views; a forged recognized number or changed original source
cannot become a new catch-up base.

Genesis has zero historical views and an explicit original frame. The default
Q3 fixture labels its reconstructed Q2 opening `supplied_history`, without a
fabricated canonical predecessor. Actual adjacent runs instead use origin
`prior_result` and exact serialized source_case_id/period/closing_state summary.
Optional external result_ref remains separate provenance. State source_case_id
is a calculation identity, not a `result@sha256` digest. A different SPL/canonical
author must carry the actual wrapper digest when that interface is built.

The independent `merchandising_reprice(data)` oracle uses only datetime,
fractions and re; `exact_json` exports Fractions recursively. It reports original
cash/deduction/NMI, row rate/old-recognized/target/delta, as-known snapshots,
separate original obligations/payments, current/catch-up recognition and closing
state. Source adapters may transport original raw facts and actual prior state;
they must not feed target, catch-up, recognized answers or reconstructed views
as new financial parameters.

Twenty-six unittest methods verify hand amounts, equality, immutability,
timing, source/CB/qualification/population controls, partial preview, zero/empty/
fractional current receipts, exact submicrosecond cutoffs, physical permutations,
no withholding default, and genuine serialized
Q1→Q2→Q3→Q4 carry with no repeated 210. No executable SPL or compiler import was
used. All five owned files are authored LF. External isolated-source snapshot,
review pins and test log are reported with the handoff. This establishes the
finite independent controls; compiler equivalence and professional disposition
remain separate work.
