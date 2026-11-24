# Fixed-term cap, floor and actual-funded advance

This selected C05 profile calculates seven explicitly named synthetic methods
from original earnings, actual funding and complete-population controls. The
[independent oracle](../../oracles/term_guarantees.py),
[design](../../docs/spl/term-guarantee-design.md), [policy](policy.md) and
[neutral fixture](neutral.json) define these research assumptions. The face
minimum is a funding ceiling/reference, not an advance, issued obligation or
payment manufactured by the calculation.

| Method | Entitlement stages | Eligible advance recovery |
| --- | --- | --- |
| `term_cap` | Cumulative term cap | None |
| `term_floor_at_end` | Floor only at exact term end | None |
| `actual_funded_advance` | Current earned entitlement | Earned entitlement |
| `floor_cap_advance_including_topup` | End-only floor, then cap | Final entitlement |
| `floor_cap_advance_earned_only` | End-only floor, then cap | Retained earned only |
| `cap_floor_advance_including_topup` | Cap earned, then end-only floor | Final entitlement |
| `cap_floor_advance_earned_only` | Cap earned, then end-only floor | Capped earned only |

Floor-before-cap removes topup before earned when the cap binds. Cap-before-floor
consumes the cap with capped earned only; the floor credit is outside that cap.
The methods can therefore end with different entitlement and cap consumption.
Unmet floor is reported when the selected precedence allows the cap to win.
Floor topup never creates funded advance. All amounts use exact USD arithmetic
with no rounding or minor-unit assumption.

The baseline actual advance is face 150, independently evidenced funding 150 and
earned 80: recovered 80, calculated payable 0 and prepayment 70. An explicitly
attested empty funding population with the same face instead gives payable 80
and prepayment 0. Interim earned 40 followed by final earned 40 under floor 100
gives entitlement 40 then 60. Cap 100 across earned 60 then 60 gives 60 then 40;
starting another period does not reset the cap.

## Original populations and term replay

Every advance-method period requires exactly one original
`complete_funding_population` attestation for its exact term, scope and period.
Its funding IDs, disbursement IDs and exact funded total must match the complete
original funding list. Empty facts establish zero new recognized funding only
with explicitly empty ID lists and attested total zero. Dropping or changing a
funded row fails these controls. Missing current or historical completeness
blocks results and successor state; it is not a numeric zero funding/payment.

Funding records retain original event/disbursement IDs, source/support, positive
amount, funded Instant, observed Instant and supplied UTC funded Date. SPL
checks the supplied Date against mechanically transported UTC projection,
recognition inside the selected period, funded-at no later than observation,
strict observation before cutoff and actual-funding support evidence. Approval
alone cannot fund an advance. Funding is pooled within the period before
recovery; no FIFO or intraperiod earnings/funding priority is inferred.

The schedule replays all original earnings and funding periods from term-opening
zero. Every period checks scope, original IDs, category-specific source views,
disbursement reuse, evidence, period/cutoff boundaries and population controls.
It recomputes six separate meters: earned, recognized entitlement before advance
recovery, cap consumption, total funded, total recovered and prepayment. The
declared opening must match them all and the closure flag. The entire original
term, method, scope and cap reduction order remain pinned. Every replay exposes
all floor, cap, retained-component, recovery, calculated-payable and meter
intermediates for independent comparison.

Genesis is zero/empty at the original term opening. Adjacent carry serializes
the actual canonical closing cell and retains its `prior_result_ref`, checked
against the supplied predecessor summary and complete original history. This
establishes consistency of supplied provenance, not cryptographic authentication
of external funding or an issued statement. Closure occurs only when the period
ends exactly at term end. Remaining prepayment stays visible; no expiry,
forgiveness, recourse or new-term use is inferred.

## Boundary and reproduction

The adapter imports no financial oracle and computes no entitlement, funding
total, floor, cap, recovery or meter. It transports exact numeric tags and
original lexical source fields, encodes population alternatives and mechanically
derives UTC funded Date and explicit UTC opening midnight. The source performs
the financial and availability comparisons. Original amount and timestamp
spellings survive neutral export alongside exact typed comparisons, so term
amendments and original funding lineage remain visible.

The thin selected helper passes a validated blocked-evidence label to the generic
runner before atomic publication. Only `TERM_FUNDING_POPULATION_REQUIRED` maps
to `funding_evidence_status = no_event_supplied`; it cannot assert completeness,
change a quantity or mutate a successful digest. Completed artifacts are checked
with `spl_compiler.artifacts.load_completed_result`. Review `result.json` equals
the returned result for successful and missing-population runs.

Successful source output separately states funding-population completeness and
`settlement_payment_evidence_status = no_event_supplied`. Generic raw payment
assessment remains `not_assessed`. Known actual advance funding does not establish
a later royalty settlement payment. Issuance stays unissued and no numeric
`actual_paid` field is inferred.

With the repository's pinned environment and existing native kernel:

```powershell
python -m cases.term-guarantees.build_modules
python -m unittest Tests.test_term_guarantee_oracle Tests.test_term_guarantee_modules -v
```

Seven method templates and the default advance alias are intentionally unbound;
execution binds current compiler/runtime/module identities. Native test groups
use canonical compare (reference, native IR and native-emitted Lean), then
execute Lean from the separate Python emitter against the same decoded bindings.
Reference-only methods name their narrower execution evidence. Tests compare
all stages, every historical prefix's financial replay and complete successor
state against independent controls.

Repeated finite lists, filters and folds have growing replay/identity-scan costs.
The generic resource guard is an engineering boundary, not a capacity result.
Full guarantee administration, amendments/reset authority, funding reversals,
withholding, settlement-payment execution, FX and contractual recourse remain
outside this selected profile.
