# Supplied withholding and settlement carry

23 November 2026. This is one synthetic `research_assumption` method for selected
C12/C16 variants. The policy is `SYNTHETIC-SETTLEMENT-01`, revision `1`; its
[neutral fixture](../../cases/settlement/neutral.json) and independent
[oracle](../../oracles/settlement_adjustments.py) precede the SPL implementation.
No tax applicability, remittance, filing, professional approval or bank execution
is inferred. Existing records, lists, maps, exact arithmetic and explicit
rounding can express this method; it establishes no necessary compiler extension.

The supplied rate applies once to newly earned gross entitlement. Exact rates
lie in `[0,1]`. All input money and state are nonnegative integral USD cents;
issue, payment and application records must be positive. Withholding is rounded
once after aggregating current earnings, to USD .01 with half-even rounding.
This cent restriction avoids silently choosing a policy for withholding rounded
above subcent earnings. Threshold money is cent-integral and nonnegative.

Opening state separates unissued net entitlement from identified issued
obligations. Old issued balances remain due, retain their original identity,
amount, paid-to-date, issue date, source and evidence, and are never reissued
merely because a threshold is reached later.

| Symbol | Meaning |
| --- | --- |
| E | Sum of current gross earned rows |
| W | Half-even cent rounding of `E * supplied_rate` |
| N | Current net entitlement `E - W` |
| U | Opening unissued net entitlement, already withheld when earned |
| O | Opening issued outstanding, sum of original amount less paid-to-date |
| C | New issuance candidate `U + N` |
| Q | `C` if `C >= minimum_payout`, otherwise zero |
| I | Independently evidenced new issuance, optional one positive notice exactly equal to Q |
| P | Independently evidenced actual payments, fully allocated to original/new issue IDs |
| U' | Closing unissued `C - I`; eligible but unissued amounts remain here |
| O' | Remaining identified issued obligations after applications |
| Closing unpaid | `U' + O' = U + O + N - P` |

Neither new eligibility nor a supplied issue notice is cash paid. No supplied
issue means `I=0`, including when Q is positive. Actual payments require complete
applications, each payment total conserved, with no application beyond an
obligation's remaining balance. Partial payments and one payment split across
old/new obligations are allowed. Missing references, overpayments, duplicate or
previously recognized event IDs block. No transfer, offset or reversal is implied.

All selected-period source rows are retained with IDs, scope, source/evidence
references and observation instants. Earned effective dates, current issue dates
and paid dates lie in the half-open selected period. Original opening issue dates
precede its start. Event dates precede their observation, observations precede
the exact cutoff, and application observations follow the linked payment and
issue observations. Physical row order has no financial meaning. This is a
complete selected-period view, not a raw intake filter.

Every run requires one explicit `complete_settlement_population` attestation
with matching scope and period, observed strictly before cutoff. It covers the
supplied earned, issued, paid and application populations. With this attestation,
empty payment/issue lists establish zero observed events for this view and are
labelled `complete_no_events`. Missing attestation yields
`SETTLEMENT_PAYMENT_POPULATION_REQUIRED`, payment status `no_event_supplied`,
and no numeric paid result or consumable closing state. Empty lists alone do
not establish zero actually paid.

The immutable neutral input has these exact top-level fields:

```text
schema_version = settlement-neutral/1
case_id, scope, period {start,end}, cutoff, terms
earned[], issued[], payments[], applications[], evidence[], opening_state
prior_result?   // required for successor carry; omitted for explicit genesis
```

`scope` is exactly `{contract_id,participant_id,pool_id,asset_id,currency}` with
USD currency. Every fact and evidence record repeats this scope. `terms` is
exactly `{policy_id,policy_revision,withholding_rate,minimum_payout,rounding,
threshold,evidence_class}`, selecting `half_even_cent_once`, `at_least` and
`research_assumption`. Exact neutral numbers are strings; decimal strings and
rational `n/d` strings are supported by the oracle. A canonical adapter must
transport them into the existing exact typed codecs rather than binary floats.

Every earned, issued, payment and application row has
`{id,scope,amount,observed_at,source_ref,evidence_ref}`. Earned adds
`effective_date`, issued adds `issued_date`, payment adds `paid_date`, and
application adds `payment_id,issued_id`. IDs are unique within their category.
Every evidence row has `{id,scope,observed_at,kind}`; the required completeness
record additionally has `period`. Other source evidence may be carried forward
to support original obligations. All referenced evidence must be supplied.

Opening and closing structured state share exactly:

```text
scope, purpose = net_unpaid, policy_id, policy_revision
boundary, origin, source_case_id
deferred_unissued, issued_obligations[], recognized_ids[]
```

Each obligation contains the original issued-row fields plus `paid_to_date`.
Fully settled obligations leave the active list; their issuance IDs remain in
history. `recognized_ids` contains category-qualified tokens such as
`earned:row-1`, `issued:notice-1`, `payments:bank-1` and
`applications:application-1`. Thus unrelated categories may use the same raw ID
without collision, while prior event recognition cannot be applied twice.

Explicit genesis has origin/source_case_id `genesis`, boundary at the period
start, zero deferred entitlement, no obligations and empty history. Successor
opening is the exactly serialized prior closing snapshot with origin
`prior_result`, boundary at the adjacent next period start, and source_case_id
equal to the preceding calculation's case ID. Its required `prior_result` is
`{source_case_id,period,closing_state,result_ref?}`. The oracle checks exact
snapshot equality, adjacent boundaries and matching case identity. An optional
external `result_ref` is retained as supplied provenance, not computed or
cryptographically validated by this financial oracle. The generic canonical
state cell separately carries its actual predecessor `result@sha256` reference.
**A source_case_id is not a canonical result digest.**

The oracle returns exact `Fraction` intermediates, obligation movements and
closing state. `exact_json` recursively converts those to neutral exact strings
for a serialized successor. The oracle imports only standard-library date,
Fraction and regular-expression support; it does not read SPL or consume
compiler-projected bindings. Independent controls validate the supplied
synthetic policy, not its legal authority.

| Period | E / W / N | Opening unissued / issued outstanding | Candidate / new issue / actual paid | Closing unissued / issued / total |
| --- | --- | --- | --- | --- |
| Q1 | 100 / 10 / 90 | 0 / 0 | 90 / 90 / 80 | 0 / 10 / 10 |
| Q2 | 10 / 1 / 9 | 0 / 10 | 9 / 0 / 0 | 9 / 10 / 19 |
| Q3 | 20 / 2 / 18 | 9 / 10 | 27 / 27 / 20 | 0 / 17 / 17 |

Q3 applies 10 of the actual 20 to the old Q1 notice and 10 to the new Q3 notice;
it never issues 37 by treating the prior issued 10 as new entitlement. Threshold
equality at net 25 qualifies. Zero/empty earnings, no notice despite eligibility,
payment against a prior issue below the new threshold, half-cent ties at gross
.01/.03 with rate .5, bad state boundaries/history, scope/currency mismatch,
duplicate records, incomplete or excessive applications and missing/late evidence
are required independent discriminators.

This slice does not establish every C12/C16 lifecycle, multi-currency settlement,
tax administration, general deductions, cancellation/reissue, dependent-period
restatement, bank execution, concurrent state commit, or general idempotent
publication. Source, canonical, oracle and execution evidence remain separate.
