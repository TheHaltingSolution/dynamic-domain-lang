# Term caps, end-only floors and actual-funded prepayment

`SYNTHETIC-TERM-GUARANTEES-01`, revision `1`. These are seven named synthetic
`research_assumption` methods, not universal guarantee, financing or recoupment
rules. Amounts are exact nonnegative USD with no rounding. Scope, original term,
method, cap reduction order and meter purposes remain pinned across the term.

The term cap is cumulative, without a new-period reset. The floor activates only
when the selected period ends exactly at the term's end. Earlier periods earn
their ordinary calculated entitlement without an interim floor topup. The floor
meter counts final entitlement before advance recovery, not payable or paid cash.

Let E be current earned entitlement, H prior recognized term entitlement, C the
term cap, K prior cap-stage consumption and F the term floor. Unused parameters
are explicitly zero. The named methods are:

| Method | Entitlement before recovery | Cap consumption |
| --- | --- | --- |
| term_cap | min(E,C-K) | That admitted amount |
| term_floor_at_end | E+max(F-H-E,0) at term end; otherwise E | Zero |
| actual_funded_advance | E | Zero |
| floor_cap_advance_including_topup | Floor E against H at term end, then cap | Capped entitlement |
| floor_cap_advance_earned_only | Same entitlement; different recovery base | Capped entitlement |
| cap_floor_advance_including_topup | Cap E, then floor that stage against H at term end | Capped earned component only |
| cap_floor_advance_earned_only | Same entitlement; different recovery base | Capped earned component only |

For floor-before-cap methods, cap reduction removes topup before earned. Retained
earned=min(E,final entitlement), retained topup=entitlement-retained earned.
For cap-before-floor, retained earned is capped E and the final topup is outside
the cap. `including_topup` explicitly permits advance recovery against both;
`earned_only` permits recovery only against retained earned. This order is a
financial policy, not formatting. A cap-winning method may end below the floor;
report that unmet amount without silently overriding the selected precedence.

Only independently evidenced actual funding increases prepayment. A face
recoupable minimum is a ceiling/reference for aggregate funded advances in this
term, not a newly issued obligation, payable or automatic advance. Funding facts
retain stable event/disbursement IDs, actual funded Instant and its declared UTC
funded Date, observation, source and support. Funded Date selects the current
half-open period. Require actual funded_at <= observed_at < cutoff, matching UTC
Date and actual-funding support evidence. No due/approval date substitutes for
cash funding. Pool period funding before recovery; no FIFO or intraperiod priority
is inferred. Reusing either event or disbursement identity blocks.

Advance methods require a complete-funding-population attestation for every
recognized period. The attestation pins original funding IDs, disbursement IDs
and exact source funded total. Those controls must match the full original
funding population; dropping an actual funded row cannot become an empty view.
Only explicitly attested empty ID lists and funded total zero establish zero
new recognized funding. Missing completeness is `no_event_supplied` and blocks
consumable state; it cannot become numeric bank-paid zero. Non-advance methods
reject funding and nonzero prepayment rather than dropping another balance.

Available advance is prior prepayment plus actual new funding. Recover the lesser
of that availability and the method's explicitly eligible recovery base.
Calculated payable=entitlement-recovered; closing prepayment=availability-recovered.
Floor topup never increases advance. Settlement actual-payment evidence remains
`no_event_supplied`; no numeric amount paid is inferred from calculated payable,
recoupment, the face guarantee, or the separate advance-funding records.

Interim earned 40 followed by final earned 40 under a term floor 100 gives current
entitlements 40 then 60, with final topup 20. A face minimum 150 actually funded
150 against earning 80 gives recovered 80 / calculated payable 0 / prepayment 70.
With a complete-empty funding view, face 150 alone gives payable 80 / prepayment 0.

At term end, E80/F100/C90/funded50 gives entitlement90/payable40 for floor→cap,
versus100/50 for cap→floor. With funded150, including-topup recovery gives
floor→cap payable0/prepayment60 versus earned-only payable10/prepayment70;
cap→floor gives payable0/prepayment50 versus earned-only payable20/prepayment70.

Genesis is zero/empty at the term opening. Preserve original earnings/funding
history and distinct cumulative earned, recognized, cap-consumed, funded,
recovered and prepayment meters. Adjacent successors require exact actual prior
closing state and matching predecessor summary. Term changes, reset, repeated
events and reopening a closed term block. Unrecouped closing prepayment remains
visible at term end; no expiry, forgiveness, recourse or next-term use is inferred.
