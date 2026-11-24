# Term-based cap/floor and funded-minimum controls

23 November 2026. This independent C05 design precedes executable SPL. It combines
only explicitly named synthetic methods under
[SYNTHETIC-TERM-GUARANTEES-01@1](../../cases/term-guarantees/policy.md), not a
default guarantee/advance interpretation. Generic exact arithmetic and state
can express the methods; no new necessary compiler primitive is presumed.

The [neutral baseline](../../cases/term-guarantees/neutral.json) supplies earned
80, a face minimum 150 and an independently evidenced actual funded advance 150.
It calculates recovered 80 / payable 0 / closing prepayment 70. It does not create
advance from the face amount. A second, explicitly complete-empty funding view
must instead calculate payable 80 / prepayment 0. Neither view invents a current
settlement actual-payment amount.

Let E be current earned entitlement, H prior final entitlement recognized within
the term, K prior cap-stage consumption, A prior actual-funded prepayment, F the
floor and C the cap. At final period only, floor input X receives topup
`max(F-H-X,0)`; interim topup is zero. Term recognition H counts entitlement before
advance recovery, never calculated payable or paid cash.

Seven variants are selected explicitly:

| Variant | Stage order | Eligible recovery |
| --- | --- | --- |
| term_cap | cap E by C-K | None |
| term_floor_at_end | end-only floor E against H | None |
| actual_funded_advance | E then funded advance | E |
| floor_cap_advance_including_topup | end-only floor → cap → advance | Final entitlement |
| floor_cap_advance_earned_only | Same floor/cap result | Retained earned component |
| cap_floor_advance_including_topup | cap → end-only floor → advance | Final entitlement |
| cap_floor_advance_earned_only | Same cap/floor result | Capped earned component |

The policy pins `cap_reduction_order=topup_before_earned`. Floor-before-cap
consumes the cap with final entitlement, retaining min(E,entitlement) as earned
and the remainder as floor credit. Cap-before-floor consumes the cap with capped
E only; the final floor credit is outside the cap. Thus the latter may recognize
more entitlement than C without misreporting its cap-stage meter. This is a
method difference, not a reset or arithmetic inconsistency. Floor topup never
increases the advance ledger. Recovery against that credit is permitted only in
the separately named including-topup variants.

Available advance is A plus actual new funding. Recover min(available, eligible
recovery base), calculate payable=entitlement-recovered, and carry
prepayment=available-recovered. Original funding remains a separately evidenced
cash event; it is not current settlement cash or proof of a later actual payment.
The face minimum merely limits aggregate funded amounts for this selected term.
It is not a manufactured advance, issued obligation or accrued guarantee debt.

| Control | Exact selected outcome |
| --- | --- |
| Term floor100, interim40 then final40 | Entitlement40 then60; topup20 only at end |
| Term cap100, period60 then60 | Entitlement60 then40; cumulative cap100, no reset |
| E80/F100/C90/actual funding50, floor→cap | Entitlement90 / payable40 |
| Same, cap→floor | Entitlement100 / payable50 |
| Actual funding150, floor→cap, include topup / earned only | Payable0 /10; prepayment60 /70 |
| Actual funding150, cap→floor, include topup / earned only | Payable0 /20; prepayment50 /70 |

All source money is nonnegative exact USD; no cent restriction or implicit
rounding is introduced for this pure calculation. Unknown/fractional amounts are
never replaced with zero. Funding is positive and carries original stable event
and disbursement identities, actual funded/observation Instants and a separately
supplied UTC funded Date. The named UTC date relation is mechanically checked;
actual funded_at <= observed_at < cutoff. Current recognition uses actual funded
Date in the selected half-open period, never due or approval dates. The selected
pooled-period order does not claim FIFO or within-period earned-after-funding
priority. Actual-funding evidence is separate and required.

Advance methods require a `complete_funding_population` attestation for the exact
term/scope/period, with independently supplied original funding IDs, disbursement
IDs and exact funded source total. Dropped or changed original facts fail those
population controls. Empty events mean zero recognized new funding only under
an explicitly attested empty population with total zero. Missing attestation is
`no_event_supplied` and prevents
final carry. Non-advance methods reject funding/nonzero prepayment. Output
settlement_payment_evidence_status remains `no_event_supplied`, with no numeric
actual paid field. Known funded advance150 is distinct from missing evidence of
the later royalty settlement's actual payment.

The exact neutral shape is:

```text
schema_version = term-guarantees-neutral/1
case_id, scope, period {start,end}, as_of, cutoff, policy, term
earnings[], fundings[], evidence[], opening_state, prior_result?
```

Scope is `{contract_id,participant_id,pool_id,asset_id,currency}`, USD. `policy`
has `{id,revision,method,floor_timing,cap_reset,cap_reduction_order,
funding_date_basis,term_availability,rounding,evidence_class}`, selecting
`SYNTHETIC-TERM-GUARANTEES-01@1`, `term_end`, `never_within_term`,
`topup_before_earned`, `supplied_utc_date`, `known_at_open_utc`,
`exact_no_rounding` and `research_assumption` alongside one named method.

`term` has `{id,revision,scope,period,floor,cap,recoupable_minimum_face,
approved_date,recorded_date,observed_at,source_ref,evidence_ref}`. Inactive term
amounts are explicitly zero: term_cap has floor/face0, term_floor has cap/face0,
advance-only has floor/cap0. The complete term is pinned in state. This fixed-term
profile requires approval/recording by the term opening and observation strictly
before its declared UTC opening midnight, separately from civil as-of. Amendments
or a new term cannot silently reuse cap, floor or prepayment meters.

Earnings are `{id,term_id,scope,amount,effective_date,observed_at,source_ref,
evidence_ref}`. Funding is `{id,disbursement_id,term_id,scope,amount,funded_date,
funded_at,observed_at,approved,source_ref,evidence_ref}`. Ordinary evidence is
`{id,scope,observed_at,kind}`; `complete_funding_population` additionally has
`term_id,period,funding_ids,disbursement_ids,funded_total`. These are original
population controls, not solved recovery, prepayment or settlement-paid answers.
Actual funding support has kind `actual_advance_funding`.
Original earnings IDs, funding IDs, disbursement IDs and source rows remain
unique across current/historical records. All required source evidence remains
available in successor inputs.

Opening/closing state has:

```text
scope, purpose = term_guarantee_and_prepayment, policy_id, policy_revision, method
cap_reduction_order, term, boundary, origin, source_case_id
term_earned, term_recognized_entitlement, term_cap_consumed
total_funded, total_recovered, prepayment, term_closed, period_history[]
```

Each history entry is `{source_case_id,period,earnings[],fundings[]}` preserving
original source records, rather than solved financial answers. The oracle replays
all adjacent periods from term-opening zero to verify each meter and current
opening. Genesis is zero/empty at term start. Successors require exactly serialized
prior closing state plus `{source_case_id,period,closing_state,result_ref?}`.
Actual canonical predecessor metadata is separate from case identity; the oracle
does not manufacture or authenticate a canonical result digest. No period after
term closure can reopen it. Remaining prepayment is visible without assuming
expiry, forgiveness, repayment recourse or permission to use it in another term.

The standard-library `term_guarantees(data)` oracle returns raw earnings, floor
and cap stages, retained earned/topup, explicit recovery base, recognized term
entitlement, actual new funded advance, calculated payable, each distinct closing
meter and original history. Exact neutral serialization supports real adjacent
carry. Method/order differences, floor finality, cap nonreset, funding completeness,
funded/observation boundaries, duplicate disbursement, scope/purpose/term changes
and predecessor errors are required controls. Complete guarantee administration,
withholding, actual settlement payments, funding reversals, FX and contractual
recourse remain outside this selected slice.

Independent authoring verification on 23 November 2026: `python -m unittest
Tests.test_term_guarantee_oracle -v` passed 19 test methods in 0.029 seconds after
adding source-population ID/total controls. This includes deliberate dropped or
changed actual funding, missing historical completeness, and the separately
attested empty-funding case. Native and canonical execution remain separate
implementation work; this is financial-oracle evidence only.
