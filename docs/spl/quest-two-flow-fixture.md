> **Non-normative execution update — 23 November 2026.** The new dated
> `DYN02-QUEST-TWOFLOW-NEAREST-EVEN@1` method and canonical fixture now execute
> on the unchanged `0.4.3-dev` kernel. See the
> [execution guide](../../cases/quest/README.md),
> [financial SPL source](../../cases/quest/charge.spl) and
> [readable policy](../../cases/quest/policy.md). A single combined run passed
> 34 new checks (20 independent oracle, nine canonical and five direct) in
> 402.120 seconds; the 86-target build and both smokes also passed. Baseline
> additional USD 95.17 and the full-year half-even tie results USD 0.00 and
> USD 0.02 are verified. All nine review scenarios also pass native IR/generated
> Lean/reference comparisons and independent exact certificates. The historical
> 352-check baseline was not rerun or republished for this method.
>
> This execution uses existing exact operations, finite folds and calendar
> observations; no solver, date-difference builtin or core extension was added.
> The prior half-away probe and the supplied specification below retain their
> original scope. Policy authority remains proposed `research_assumption`;
> monthly/combined liability, partial-payment rules, Excel operational
> equivalence and adjacent-domain owner acceptance remain unresolved. Existing
> proof scopes are unchanged. This update records engineering evidence and
> does not amend the selected fixture or establish contractual approval.

# Quest two-flow synthetic fixture specification

22 November 2026. Reconciles the compiler's four acceptance questions and the
research reply supplied by the user. This is a compact neutral specification
for implementation and independent checking. It is not a canonical package
schema, a new compiler capability or contractual approval.

Fixture/policy identity: `DYN02-QUEST-TWOFLOW-NEAREST-EVEN@1`.
Evidence class: `research_assumption`; review status: **proposed, pending review**.
Project scope: disclosed patent-rights development case; owner acceptance of
that adjacent domain for the demonstration remains pending. No holdout is implied.

## Disposition of the compiler's questions

| Question | Selected fixture policy | What remains unestablished |
| --- | --- | --- |
| Numerical result | Mathematical annual target 20%, actual whole elapsed days / 365; round the additional charge once to nearest USD cent, ties to even | No authoritative cent-rounding rule or minimum-return inequality has been established in reviewed Schedule II. The fixture convention is synthetic |
| Mandatory flows | Exactly one identified USD obligation and one full principal payment with one application; additional charge is the unknown, modeled at the principal-payment date for return calculation | Partial payments, multiple obligations, competing applications and later settlement of the additional charge are outside this fixture, not resolved for the whole agreement |
| Excel reference | Mathematical equivalence under the selected policy, certified by exact rational comparisons; no exact irrational scalar or reported IRR required | Particular Excel builds, guesses, iteration limits, tolerance and error equivalence have not been verified or adopted for this fixture |
| Two components | Compute only the additional target-return component on the selected overdue principal. Preserve the statutory monthly component separately and leave combined liability unresolved | Statutory rate evidence, monthly/stub conventions, combined ordering/crediting and broader principal-base interaction remain unapproved |

The selected synthetic scope can be implemented without resolving every possible
interpretation of the agreement. Do not present its output as the entire Late
Payment Charge, an issued liability or a professionally approved settlement.

## Source locators and authority

- Quest prepaid forward purchase agreement effective April 11, 2025,
  **Schedule II, page 19, late-payment paragraph**: identifies the additional
  20% target and Excel XIRR reference alongside a distinct monthly-compounded
  component. [Filed agreement](https://www.sec.gov/Archives/edgar/data/824416/000121390025034342/ea023916001ex99-1_quest.htm).
- [Microsoft XIRR documentation](https://support.microsoft.com/en-us/excel/functions/xirr-function)
  supplies the mathematical 365-day discounting reference. It does not establish
  the contract's cent rounding, charge interaction or approval of this fixture.
- The research reply in the user conversation of 22 November selects the
  reconstruction choices recorded here. No reviewer contact, professional
  approval or actual historical payment record was supplied by that selection.

## Neutral original inputs

All transaction identifiers, amounts, dates and observations below are synthetic.
Use exact decimal strings and valid Date/Instant values. Every reference must
resolve within the pinned fixture closure. Physical field names may be mapped
to the implementation's declared module interface; their meanings must remain.

| Required record | Minimum fields and baseline values |
| --- | --- |
| Agreement/clause | `agreement_id=quest-synthetic`, source document/version and Schedule II locator, document digest when packaged |
| Obligation | `obligation_id=QO-1`, agreement, amount `{value:"1000",currency:"USD"}`, `due_date=2026-01-01`, source/evidence reference |
| Actual payment | `payment_id=QP-1`, amount `{value:"1000",currency:"USD"}`, `paid_date=2026-07-02`, actual-principal-payment evidence reference |
| Application | `application_id=QA-1`, payment `QP-1`, obligation `QO-1`, applied amount USD 1000, application/effective-date evidence |
| Evidence/availability | Stable evidence IDs, source identity, observed-at timestamps for obligation/payment/application and supporting date evidence; all required observations strictly before the pinned cutoff |
| Calendar | Pinned Gregorian date-to-ordinal observations covering both dates with the same origin/version; date, ordinal and calendar evidence/identity. Ordinary calendar facts contain no financial answer |
| Terms | Exact annual target Ratio `0.20`, ACT/365 basis, USD cent quantum `0.01`, `half_even`, policy ID/revision and proposed review status |
| Run | Scenario identity, cutoff, selected clause/policy/calendar versions and source/compiler/runtime dependencies |

A convenient synthetic availability setup is observations at
`2026-07-03T00:00:00Z` and cutoff `2026-07-04T00:00:00Z`; these are scenario
inputs, not inferred from the actual principal-payment date. Other complete
availability facts may be used with their own fixture identity.

For a relative Gregorian calendar origin of January 1, 2026, the two endpoint
ordinal facts are 0 and 182. SPL must look them up from the linked due/paid
dates and compute `paid_ordinal - due_ordinal`. Do not instead bind a precomputed
financial charge or omit the original dates. Validate calendar membership,
unique keys, common origin/version and evidence; malformed or contradictory
calendar data must not silently change the day count.

Validate exact one-to-one payment/application/obligation cardinality, USD
compatibility, payment amount = application amount = principal, correct links,
date evidence, cutoff and nonnegative elapsed days. Duplicate application or
economic payment identity cannot be counted twice. A partial amount, second
obligation or ambiguous application blocks this fixture rather than choosing
an allocation rule. A compiler's declared numeric search-domain limit must be
explicit and must fail safely outside it; it is not an agreement term.

## Required calculation and outputs

SPL derives elapsed days and performs the financial computation internally:

```text
d = ordinal(actual principal-payment date) - ordinal(due date)
additional* = principal × ((1 + annual_target)^(d/365) - 1)
additional = round additional* once to USD 0.01 using half_even
```

The displayed real-valued formula specifies the result; it does not prescribe
an irrational runtime type or a new power builtin. An exact-rational internal
search with a rounding certificate is an acceptable implementation.

Required neutral result for the baseline:

| Output | Expected value/meaning |
| --- | --- |
| Obligation/payment/application references | `QO-1`, `QP-1`, `QA-1`, preserved with source/date evidence |
| Elapsed days and basis | 182; ACT/365, exact fraction 182/365 |
| Target and policy | Ratio 0.20; `DYN02-QUEST-TWOFLOW-NEAREST-EVEN@1`, proposed |
| Actual principal payment | USD 1000, unchanged; no generated payment of the additional charge |
| Calculated additional charge | **USD 95.17**, scenario-only, calculated and unissued |
| Rounding certificate | Exact rational lower/upper comparisons, chosen cent index/parity, target power and relevant identities |
| Lineage | Original obligation, payment/application, clause/terms, calendar observations, cutoff and policy/source/compiler pins |
| Monthly/combined charge | Monthly component not calculated here; combined liability unresolved/not computed, with no invented numeric zero |

No exact unrounded scalar or separately reported IRR is required. The value
95.171555668... may be shown as explanatory approximation only. The modeled
principal-plus-charge return amount is not a replacement for the actual USD
1000 payment and does not establish that the additional USD 95.17 was disbursed.

## Half-even certificate and important tie tests

Let principal `P > 0`, target `r >= 0`, integral days `d >= 0`, cent quantum
`q=0.01`, and candidate **additional charge** `m*q`, with integral `m >= 0`.
Define `K=(1+r)^d` and `G(b)=((P+b)/P)^365` for nonnegative charge bound `b`.
Integer powers and these comparisons are rational computations.

- If `m` is even, accept both half-cent endpoints:
  `G(max(0,(m-1/2)*q)) <= K <= G((m+1/2)*q)`.
- If `m` is odd, both original half-cent inequalities are strict:
  `G((m-1/2)*q) < K < G((m+1/2)*q)`.
- At `m=0`, nonnegative charge supplies the lower-domain boundary; do not demand
  a negative-charge power comparison. Track the domain restriction explicitly.

For the 95.17 baseline, `m=9517` is odd and both inequalities are strict:

```text
(1095.165/1000)^365 < (6/5)^182 < (1095.175/1000)^365.
```

Determine parity from the additional-charge cent index, **not** the modeled
terminal-payment index. Round the additional charge itself, not the terminal
total before subtracting principal. Mandatory synthetic tie variants expose
both mistakes:

| Principal/rate/days | Exact additional | Selected half-even | Half-away alternative | Wrong round-total-then-subtract |
| --- | ---: | ---: | ---: | ---: |
| USD .01 / 50% / 365 | .005 | **.00** | .01 | .01 |
| USD .03 / 50% / 365 | .015 | **.02** | .02 | .01 |

The earlier unchanged-compiler probe implements positive half-away rounding.
Its 95.17 result is compatible at the non-tie baseline, but it does **not**
establish this newly selected half-even method. Refine the reusable method's
equality/parity logic and test it; existing exact arithmetic, quantization and
folds suffice in principle, so this is not evidence of a necessary new primitive.

## Material alternative discriminators

| Alternative to the selected fixture | Discriminating example | Disposition |
| --- | --- | --- |
| Minimum cent charge achieving at least 20% | Baseline charge 95.18 instead of 95.17; 95.17 implies about 19.99965815% | Retain as a separate explicitly synthetic policy, not the adopted fixture |
| Simple annual-rate daily proration | `1000*.20*182/365` rounds to 99.73 | Reject as equivalent to the selected compounded annual-target calculation |
| Half-away instead of half-even | USD .01 / 50% / 365 gives .01 instead of .00 | Separate synthetic rounding variant; baseline alone does not discriminate |
| Round terminal total first | USD .03 / 50% / 365 gives .01 additional instead of .02 | Reject for the selected additional-charge rounding boundary |
| Credit hypothetical USD 10 monthly charge as same-day inflow toward target | Baseline additional rounds to 85.17 instead of 95.17 | Research discriminator only; interaction is unadopted and monthly/combined liability remains unresolved |
| Claim a particular Excel build's operational output | No build-specific expected result supplied | Unverified, outside mathematical fixture equivalence; do not invent a golden |
| Partial payments/multiple obligations | Input no longer has the required one-to-one full-payment shape | Unsupported-scenario diagnostic; no implicit FIFO/pro-rata or universal policy |

## Next compiler task and exit criteria

Do not add a power/root/XIRR primitive for this fixture. First:

1. Preserve the unchanged `0.4.3-dev` computation probe as its original half-away
   evidence; create a new named method/policy revision for half-even behavior.
2. Bind original obligation/payment/application and date evidence, derive days
   through the pinned calendar relation, and compute charge plus certificate
   within SPL. Keep adapter work to faithful facts/calendar normalization.
3. Compare an independent neutral-fact oracle, native IR and emitted execution
   on the baseline, both tie variants and invalid scope/cardinality/calendar/
   cutoff cases. Exercise the real descriptor/canonical result lineage as well
   as direct typed bindings. Do not claim this integration already ran.
4. Report the complete witness or the exact residual requirement still unmet.
   A passing dated fixture is a reusable method fit and leaves the search for a
   genuinely necessary core extension open. A schema registration gap or method
   refinement is classified separately.

The research replies resolve the selected synthetic calculation sufficiently
for that engineering task. They do not resolve the complete agreement's monthly
charge interaction, broader cash-flow cases, Excel implementation equivalence,
project-owner scope acceptance or professional approval. Keep those limits in
the result/review record; do not request all four original questions again.
