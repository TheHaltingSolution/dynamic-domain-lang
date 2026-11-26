# DYN-02 contract extension selection answer

23 November execution update: the selected
[half-even dated/canonical method](../../cases/quest/README.md) now implements
the bounded fixture using the unchanged `0.4.3-dev` kernel. All 34 supplemental
checks and nine comparison-review scenarios pass, including both mandatory ties
and a non-origin due date. The supplied-day half-away probe below retains its
original scope; no claim is made that it implemented the later tie policy.
This strengthens the bounded method-fit evidence without selecting a core
extension, approving whole-contract liability or establishing Excel equivalence.

22 November 2026. Independent language-design assessment of the compiler's
[DYN-02 request](implementation-questions.md#dyn-02-required-contract-extension-before-fx),
then reconciled with the research recommendation supplied by the user. Baseline:
`0.4.3-dev`, commit `38f00a2`. This is a disclosed development analysis, not a
custodied holdout, historical account or new compiler release.

Later 22 November research disposition: the compiler's remaining questions now
have a selected **proposed synthetic** boundary in
[quest-two-flow-fixture.md](quest-two-flow-fixture.md). Use mathematical ACT/365
20% target, round the additional charge once with **half-even**, one obligation
and full principal payment, original dates/pinned calendar lineage, and keep the
monthly component/combined liability unresolved outside that scope. The earlier
probe below used half-away: its baseline agrees, but its tie behavior is not
the newly selected method. Required tie examples and canonical integration are
specified in the new handoff. Broader ambiguity discussions below describe the
source/whole-contract limits; they are not unanswered prerequisites for this
bounded synthetic computation. No new primitive is reserved.

## Decision

**Reserve no new core capability yet.** Keep all three clauses as development
candidates. Reject receipt-time FX and complete-half-year rational compounding
as demonstrated necessities for a core extension. Prioritize Quest's additional
20% return charge for a bounded, unchanged-compiler encoding investigation if
patent-rights finance is accepted within the demonstration's scope.

Do not reserve `XIRR`, `pow`, `exp`, EUR or a solver merely because that name/type
is absent. First determine which original facts and required outputs the clause
actually demands, and attempt a reusable old-language calculation. No candidate
currently meets the stronger gate: a material contractual output or verification
condition remaining unsatisfied after faithful ordinary encodings are considered.

This does not undo the calendar experiment. That experiment remains evidence of
an admitted API extension and compatibility work. Its supplied-date alternative
prevents relabeling it as a financially unavoidable extension under DYN-02.

## Candidate assessment

| Candidate | Strongest existing-language route | Current disposition |
| --- | --- | --- |
| FAME–Roundlake receipt-time FX | Records carry original currency and exact magnitude, typed quote orientation/source/availability, receipt identity and dates. Select the authorized quote, multiply magnitudes as Ratio, reconstruct USD only after checking the conversion relation, then apply the fee | Existing method fit for the ordinary receipt slice. Research reports unchanged native interpretation and emitted execution producing gross 300, fee 75, remainder 225. Canonical integration and the blocked-currency alternative remain separate work |
| Lionsgate–Mandate Cost of Funds | Fold complete half-year periods, joining dated approved LIBOR observations; update principal/accumulated interest exactly by the declared 2.75 percentage-point spread and semiannual convention | Existing method fit for the stated fixture. Starting 1,000 at an 8% annual nominal rate gives interest 40 then 41.60; plus insurance 10 gives hurdle 1,091.60 and excess 3.40 on 1,095. Research reports a reference-interpreter check, not a new full canonical/native validation here |
| Quest–MR Licensing XIRR additional charge | For one unpaid principal and one terminal repayment date, compute a fixed-target return charge with exact rational integer powers, internal search and a monetary-rounding certificate | Bounded financial solver now executed unchanged in native interpretation and emitted Lean; no necessary core gap established. Original-date/canonical integration, partial-flow and Excel-equivalence requirements are still unresolved |

For FX, tagged Ratio magnitude is a legitimate competing representation, not
currency mislabeling, provided original currency, units, quote relation and
lineage remain explicit and mismatches are checked. Simply calling EUR cash
`Money<USD>` without converting would be invalid. Native EUR/FX types strengthen
static guarantees; their rejection in the old checker does not demonstrate
financial inexpressibility. Generalizing same-currency division to EUR would
also permit `Money<EUR> / Money<EUR>` normalization before USD reconstruction.
That foundation change cannot be hidden when assessing a purported reserved FX
gap. Do not remove a working cancellation rule to manufacture an extension.

For compounding, partial periods, principal changes, reset/tenor and rounding
need selected policy. Those omissions are evidence/variant gaps, not proof that
the complete-period fold lacks multiplication semantics. Neither a longer method
nor a dedicated interest phrase automatically requires new core behavior.

## Quest requires a precise computation boundary

The filed agreement concerns patent monetization rather than film participation.
Schedule II, page 19 describes two late-charge components: a monthly-compounded
component referencing an applicable statutory rate, and an additional amount
targeting a 20% return from due date to payment using Excel XIRR. This memo
analyzes only the latter. It does not determine the statutory rate or combine
the two components without an approved policy.
[Filed Quest agreement](https://www.sec.gov/Archives/edgar/data/824416/000121390025034342/ea023916001ex99-1_quest.htm).

XIRR computes a return rate from dated cash flows. Microsoft's documentation
uses 365-day discounting and describes an iterative calculation with guess and
failure behavior. A clause fixing the target at 20% may instead require finding
the extra terminal amount; it does not automatically demand a general solver
for an unknown rate and arbitrary multi-sign cash flows. Mathematical target-rate
equivalence and matching a particular Excel implementation are different
acceptance contracts.
[Microsoft XIRR documentation](https://support.microsoft.com/en-us/excel/functions/xirr-function).

Before selection, pin:

- The permitted domain: film/TV only or a disclosed adjacent patent-rights case;
  original obligation, principal currency/amount, due date, actual principal
  payment(s), date evidence and relevant rate/terms.
- Calendar/day-count facts, selection of actual payment date and any same-day,
  partial-payment or multiple-obligation allocation policy.
- Which amount is the unknown, and whether required output is nearest-cent
  charge, minimum cent amount meeting the target, a rate/residual, a certified
  interval, or specified Excel-version behavior and errors.
- Rounding mode, point, ties, target tolerance and relation between the two
  separate late charges. Do not add an exact-real scalar output requirement
  after observing that `Ratio` cannot hold an irrational value.
- The supported input and resource envelope, and the required source lineage.
  Large integer cost or an arbitrary current resource cap is not by itself
  semantic inexpressibility.

For the one-flow synthetic scenario, preserve an actual principal-payment event
of 1,000 independently from the newly calculated additional charge. The modeled
terminal value `1,000 + charge` is used to evaluate the return condition; it is
not permission to rewrite the actual payment record or assert that the charge
was paid. No final late-payment liability is approved by this numerical example.

## Independent mathematical result and an important rounding distinction

Let principal `P > 0`, target annual rate `r > -1`, elapsed whole days `d > 0`,
and a selected two-flow ACT/365 target policy. Required additional amount is

```text
charge* = P × ((1 + r)^(d/365) - 1).
```

January 1 to July 2, 2026 is 182 days. With `P=1000`, `r=1/5`:

```text
charge* ≈ 95.171555668098832086119250777557836...
nearest cent:                         95.17
simple daily proration:               99.726027... -> 99.73
least cent charge reaching >=20%:     95.18
```

These are independently checked synthetic results, not Excel outputs or a
finding that the agreement chooses a rounding rule. A total of 1,095.17 implies
approximately 19.99965815%, slightly below 20%. A nearest-cent approximation and
a minimum amount meeting an inequality are therefore observably different.
Do not make 95.17 or 95.18 an unconditional contractual golden.

If the acceptance contract simultaneously requires an exact 20% mathematical
return and a whole-cent charge for this input, it needs a tolerance or rounding
policy: neither neighboring cent value equals the irrational ideal. That is an
inconsistent output requirement without such a policy, not something a new
compiler numeric primitive alone can cure.

### Exact old-language certificate

For a candidate positive terminal amount `A`, raising positive quantities to
the positive integer 365 preserves order:

```text
A < P × (1+r)^(d/365)  iff  (A/P)^365 < (1+r)^d.
```

Both sides of the right comparison are rational integer powers. Independently
verified exact comparisons for the nearest-cent cell are:

```text
(1095.165/1000)^365 < (6/5)^182 < (1095.175/1000)^365.
```

That certifies nearest-cent 95.17 without storing an irrational factor. The
minimum-cent alternative is certified by:

```text
(1095.17/1000)^365 < (6/5)^182 <= (1095.18/1000)^365.
```

These fixed comparisons establish the sample's rounding cell; **they are not
yet a reusable computation of the answer**. Supplying 95.17 as a financial
input or placing it in a fixture-specific source branch would violate the
agreed boundary. The solver must derive a candidate internally and verify it.

### Reusable baseline algorithm to attempt

The inspected baseline already has exact Ratio arithmetic, floor/ceiling
quantization, records, finite folds and acyclic imported functions. Integer
power can be a reusable old-language function:

1. Require a nonnegative integral exponent and a fixed published upper domain.
2. Fold a nonfinancial bit-step sequence carrying remaining exponent, base and
   product; derive quotient/parity with exact floor, multiply when odd and square
   only while work remains. Require remaining exponent zero at completion.
3. Compute `(1+r)^d` and search cent indices internally. Compare each trial
   `(P + trial_charge)/P` raised to 365 against that target rational value.
4. Validate the bracket, convergence and the selected exact cent/half-cent
   inequalities. Explicitly fail rather than publishing an uncertified result.

An initial one-year domain with nonnegative rate admits upper charge `P*r`;
outside that domain the bound must be generalized or the method must diagnose
its documented domain limit. An iteration count/bit schedule contains no
financial answer and is a legitimate algorithm parameter. It is not evidence
that every contractual duration, partial flow or resource case has been covered.

For original dates, permit pinned ordinary calendar facts such as endpoint
date-to-ordinal records, and compute the elapsed day count inside SPL. A missing
date-difference builtin does not block that faithful route. Financial computation
stays in SPL; adapters may normalize source/calendar observations but must not
calculate the charge or insert an externally solved candidate. Retain date,
payment, terms, calendar and observation identities in the result's trace.

The supplemental probe below has now exercised this algorithm against the
existing binary before any power/root/XIRR capability was added. Preserve the
results and complete the original-data boundary before a contract-level claim.
Canonical registration/profile work is a separate status from source-level
financial expressiveness.

## Executed unchanged-compiler financial solver probe

The external artifact record is
`C:\Projects\Film_TV_participation_dynamic_DSL\artifacts\spl\dyn02-design-probe\README.md`.
It contains `probe.spl`, generated `Probe.lean`, typed bindings, check/compile
outputs, four native/emitted result pairs, three native failure results,
an independent `Fraction` certificate checker and metadata with binary/source
hashes. The SPL source SHA-256 is
`3af2c3820ccfb01ab85c597be1345f64a4b3b27663b593b3beb0fad898e51a9c`.
The existing compiler binary is pinned there alongside Git HEAD `38f00a2` and
the Lean 4.35.0 toolchain; no compiler source or registered profile changed.

The program takes variable principal, rate and elapsed days. It computes its
own target rational, cent-index search and half-cent comparison. It contains
no expected 95.17/95.18 financial constants and receives no candidate answer.
Nine power slots and 24 search slots are explicit nonfinancial algorithm budgets.
The native compiler checked the 22 declarations and emitted Lean successfully.

| Principal USD | Annual rate | Elapsed days | Nearest-cent charge | Minimum-cent charge | Execution |
| ---: | ---: | ---: | ---: | ---: | --- |
| 1,000 | 20% | 182 | 95.17 | 95.18 | Native IR and emitted Lean calculated; exact outputs agree |
| 1,000 | 20% | 365 | 200.00 | 200.00 | Both calculated; exact outputs agree |
| 1,000 | 20% | 0 | 0.00 | 0.00 | Both calculated; zero-duration extension is an explicit synthetic scenario |
| 500 | 10% | 180 | 24.06 | 24.07 | Both calculated; exact outputs agree |

The separate exact-rational checker verified all emitted fields agree, target
power, minimum-cent predecessor inequalities, nearest half-cent inequalities
and cent integrality in each case. It supplies no value back to SPL. Native
negative checks blocked fractional days, days outside the one-year domain and
an oversized cent bracket with their respective diagnostics and no financial
emissions. Those failure checks were not also rerun through emitted Lean.

The actual declared domain is principal at least USD 0.01, nonnegative annual
rate, integral days from 0 through 365, and
`ceil(principal * rate / USD 0.01) < 2^24`. The probe is a computed method fit
within that domain, not a proof for all such inputs or general Quest performance.
The small runs generated roughly 15–17 MB of native trace each; optimizing that
overhead may be valuable but does not establish missing financial semantics.

Elapsed days are supplied to this isolated solver. No source obligation, original
date/calendar derivation, canonical module registration, issued liability or
actual payment application is claimed by it. A full original-fact witness must
still supply the approved evidence/date policy and produce lineage. In particular,
the probe is stronger than a hardcoded half-cent check, but narrower than complete
Quest contract compliance or Excel behavior equivalence. Preserve those bounds
when reporting the extension-selection result.

## Before and after acceptance gate

For Quest, the **next accepted task is an encoding experiment, not selection
of a reserved primitive**. Require at least:

| Test | Required observation |
| --- | --- |
| Main two-flow input | Selected nearest-cent policy derives 95.17 internally, with exact rounding-cell evidence and original-event lineage |
| Alternative acceptance policy | Minimum-cent-at-least-target derives 95.18; policy identity differs |
| Inputs vary | Different principal/rate/dates, zero-duration scenario and one-year complete period; no constant payout dispatch |
| Domain/failure | Invalid dates/flow pairing, absent evidence, ambiguous terms, inadequate bracket/iteration bound and exceeded resources block the declared scope |
| Precision boundaries | Half-cent ties, near ties, strict/equal target comparisons and quantization order handled under a pinned policy |
| Full integration | Original fact/calendar mapping, typed core, unchanged native interpretation and emitted execution, then explicit canonical descriptor/results/state/audit |

If a faithful reusable baseline method satisfies the agreed requirements,
classify it as a method/library and reject it for the stronger necessity demo.
If a genuinely required property remains, record that exact residual before
proposing an extension. A new certified accumulation/root facility might be
useful engineering, but its necessity is still to be established. Do not extend
the task to arbitrary multi-root XIRR, exact-real scalar outputs, unbounded
iteration or Excel bit identity without clause/application evidence.

For partial payments, several dated terms can be expressed through algebraic
or interval algorithms at a fixed rational target. Additional flows alone do
not prove an old-language impossibility. Conversely, do not claim that this
two-flow certificate proves every XIRR-related contract expressible. A theorem
about no encoding would require a language/domain argument, not a failed parser
call or a slow prototype.

## Compiler and research handoff

1. Preserve `38f00a2`, its source/binary/dependency identities and the pre-FX
   trust boundary. This documentation update does not alter or republish them.
2. Record FAME and complete-period LG as disclosed fits with their actual
   execution scope; add canonical coverage separately when chosen.
3. Resolve the short [DYN-02 follow-ups](dyn02-research-followups.md), then run
   the reusable Quest encoding if the adjacent rights domain is accepted.
4. Return either the complete old-language witness or the precise unsatisfied
   required behavior and smallest extension proposal. Keep the stronger
   selection gate open; no new capability is reserved by this memo.

No withheld evaluation material was accessed. Baseline suites and archived
performance/verification claims were not rerun here. The independent arithmetic
checks and supplemental unchanged-compiler probe are described above. This answer
does not implement a new operation or lift
the compiler team's existing pre-FX milestone gate.
