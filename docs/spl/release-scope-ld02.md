# LD-02 feature coverage and next release decision

21 November 2026. Proposed language-design answer to
[LD-02](implementation-questions.md#ld-02-design-conformance-and-next-release-scope)
and the user's request for broad Rightsline/Curve calculation coverage. Keep the
accepted readable direction. This is a design and implementation plan, not an
announcement that the added capabilities are implemented or vendor-equivalent.

## Decision and coverage target

The existing demo is a sound starting slice, not a broadly complete royalties
language. The next objective is **C1, a broad calculation coverage release**:
the finite economic method families in this document, implemented across the
surface, typed core, target, canonical interface and independent case suite.
Version names and dates remain proposals; this is not an effort estimate.

Subsequent steering integrated on 21 November: the user explicitly requires
an expandability demonstration, and has supplied the RR-03 response. Adopt
[the R1 benchmark/workload disposition](rr03-response-integration.md) as the
first finite baseline inside the broader C1 target. Preserve the deliberately
staged capability omission and experiment in
[extensibility-experiment.md](extensibility-experiment.md); implementing every
known feature before freezing would lose that experimental boundary.

The user's commercial coverage objective is the basis for selecting methods.
Public vendor documentation helps identify those methods. It does not establish
the parties' contract meaning or prove identical behavior across configurations.
Measure coverage with an explicit denominator: method/variant/evidence rows in
the [vendor evidence inventory](vendor-feature-evidence.md), plus requirements
in the [conformance ledger](conformance-ledger.md). Do not claim a numerical
percentage of all Rightsline/Curve functionality when their complete configured
behavior and product denominator are unknown.

The implemented baseline is `spl-implementation/0.3.0-dev`; this review inspects
sources and existing check records without rerunning or certifying that suite.
The ledger distinguishes compiler implementation from canonical integration.
Signed arithmetic or a handwritten formula is not full refunds/loss/correction
support when the package schema rejects the corresponding facts and policies.

## What C1 includes

| ID and method family | Required variants and canonical support | Synthetic discriminator or first witness |
| --- | --- | --- |
| C01 Scoped rule selection | Unique and greatest-priority matching; explicit fallback; effective intervals; unique winner, ambiguity, missing rule and valid zero with reasons | Receipt 100: default 20%, CA 40%, FR 0% gives 20/40/0; tied highest matches block |
| C02 Units, bases and rates | Money/ratio plus declared quantity units; flat percentage of a named gross/net base, fixed money per unit and participation separate from rate | Gross 125/net 100 at 20% gives 25/20; 100 units at 1.50 per unit gives 150, or 75 when a separately declared 50% share applies |
| C03 Deductions and fees | Pre-basis, pre-share and post-share operations; eligible subsets, caps and prior-consumption identity; fee base and order explicit | Revenue 1,000, costs 500: 80% revenue less costs = 300; 80% after costs = 400 |
| C04 Tiers and escalation | Marginal bands vs whole-base rate, cumulative meters, threshold equality, prospective row/split vs selected retroactive policy | 150 basis: first 100 at 10%, rest 20% = 20; whole-base 20% = 30 |
| C05 Caps, floors and guarantees | Scoped ceilings, nonrecoupable entitlement floor, recoupable minimum/advance as distinct policies; term/cumulative versus period meters | Earned 80, nonrecoupable period floor 100 gives entitlement 100; separate recoupable opening advance 150 against earned 80 gives payable 0/closing 70 |
| C06 Allocation and relationships | Bundles, multi-title/participant shares, direct approved allocations, declared weighted pools (including usage-weighted subscription pot), residual assignment and unmatched scope | Pot 120 with valid 3:1 usage weights allocates 90/30; zero total weight needs explicit fallback or blocks |
| C07 Recoupment and waterfalls | Explicit authorized pools, claim kinds, ordered priority versus proportional recovery, balances and excess funds | Funds 120, two claims of 100: A-first pays 100/20; equal pro rata pays 60/60 |
| C08 Returns and loss policies | Linked signed reversal, original measurement/rate linkage, period of recognition, separate negative basis/loss carry/zero floor policies | A earns 100, B -40: authorized signed pool gives 60; per-title floors before pooling give 100. Neither is a default |
| C09 Reserve vintages | Add/application/release by purpose/scope/vintage; term-based release schedule and cap; basis-stage reserve distinct from payment holdback | Adopted V1 12-7-5=0 and V2 0+20=20; application of 8 to V1 must fail despite aggregate balance 20 |
| C10 Cross-contract movement | Explicit transfer/subtraction rules and recipient/source scopes, transaction identity, conservation, acyclic dependency graph and authorized crossing | Source entitlement 100, authorized transfer 30: source remaining 70 and target addition 30, no new external cash implied |
| C11 Gates and ordered histories | Separate aggregate/work conditions; full versus proxy bases; opening/closing/continuous/event-time gates; explicit crossing row and same-event order | Existing full gate 400/100, proxy basis 210 and greater-of 30/35; new crossing policies require declared inputs and independent expectations |
| C12 Actual payments and obligations | Calculated/issued/paid distinct, payment applications, threshold/deferment carry and already-paid constraints; no bank execution | Issued/revised entitlement 90 with linked actual payment 80 leaves 10 outstanding; payment threshold 25 carries 10 unpaid under a separate supplied policy |
| C13 Corrections and replay | Original/reversal/replacement identity, original opening and dependent-period replay, separately authorized prospective adjustment, delta vs total outputs | Original payable 100, paid 80, revised 90: delta -10, outstanding 10; never create a new 90 disbursement |
| C14 Effective terms and calendars | Versioned amended terms, declared source date and as-of, fiscal periods, supplied business-day calendar and day-based proration | 300 monthly entitlement over declared 30 eligible days with 10 in force = 100 under that named proration rule |
| C15 Currency and FX | At least USD/EUR in first multi-currency witness; exact quoted observations with units/direction/date selection; source, contract and payment currencies separate; explicit rounding boundaries | EUR 100 at USD 1.10 per EUR = USD 110; a reverse quote cannot be silently substituted |
| C16 Statement adjustments | Explicit supplied withholding/deduction rates, minimum payout, separate earned/withheld/payable/unpaid balances and audit | Gross payable 100, supplied withholding 10% yields withheld 10/net 90; no tax-law applicability or filing is inferred |
| C17 Reusable contracts and reporting | Reusable typed module interfaces, parameterized methods, new contract registrations, multi-participant statement/detail/state, deterministic what-if runs and full lineage | New synthetic agreement and two participants run without a new contract-name branch in the interpreter/wrapper; scenario state remains distinct from issued results |

These numeric witnesses define selected synthetic methods, not vendor defaults
or contract approvals. They are seeds for separately authored fixtures and
oracles, not complete source programs or existing passing tests. Some families
have arithmetic support already; every required semantic/integration gap remains
visible in the ledger. Approved source, parameter and variant selections must
be attached to actual cases before using them as sourced contractual claims.

C1 deliberately includes FX, fiscal/calendar data, units and payment-threshold
calculation because omitting them would leave common royalty processing gaps.
Implement those after the reusable kernel, rather than adding automatic currency
conversion or interpreting legal calendars by default. Initial currency/quantity
and calendar dictionaries can be finite, versioned and explicit; the language
does not require global mutable registries or a general timezone engine in the
pure settlement function.

## Finite implementation sequence

| Gate | Scope and required result | Start now versus research dependency |
| --- | --- | --- |
| K1 Selection | RULE-01 priority with deterministic diagnostics and typed output, plus C01 canonical rule records and evidence | Semantics are specified now in the next-core design; no vendor tenant required |
| K2 Reusable data | Tuple keys, typed Map/lookup, Option handling, group/inner join and deterministic enumeration; generic interface descriptors | Use explicit synthetic schemas; no new contract interpretation required |
| K3 Ordered core | General finite fold with immutable state, tuple ordering/complete ties, first-order module definitions and controlled readable expansion | Generic fold can proceed; selected event economics cannot be inferred from order alone |
| M1 Ordinary royalties | C02-C07 recipes: bases, unit rates, staged costs/caps, tiers/guarantees, allocations and priority/pro-rata waterfalls | Implement declared synthetic variants; RR-03 supplies vendor/contract discriminators and priorities |
| M2 Period accounting | C08-C14: signed effects, scoped loss/carry, reserve schedules, transfers, obligations, approved replay/corrections and calendars | Retain RR-01/RR-02 named policy answers; new economic alternatives need case-specific decisions, not blanket approval |
| M3 Currencies and settlement outputs | C15-C16, typed FX observations, exact conversion, source/statement currency and supplied withholding/threshold policies | Basic synthetic arithmetic now; source/quote/date and jurisdiction applicability require supplied policy/evidence |
| I1 Broad canonical release | C17 plus all accepted C1 families integrated end-to-end, independent corpus/oracles and declared capacity envelope | Requires actual package profiles, mapped results and review gates; passing standalone formulas is insufficient |

Integrate and test after every gate; do not wait for all features to exist.
K1 is the immediate implementation priority. K2/K3 follow because they prevent
tiers, competing claims, reserve vintages and event histories from becoming
contract-specific backend code. Module interfaces and schema registration begin
with K1/K2; they must not be postponed until after a large hardcoded library.

The explicit C1 deferred list is: arbitrary recursive/user host programs,
unbounded or cyclic cross-contract fixed points, automated legal interpretation,
automatic discovery of approval/FX/tax policies, interest/discount/IRR engines
without selected cases, general optimization/constraint solving, distributed
transaction services and an all-jurisdiction tax/compliance engine. New evidence
can change this list only by a recorded release-scope revision. Basic signed
amounts, explicit interest formulas or tax facts can still be represented when
their supported interface and case policies permit them; that is not a claim
of a complete specialist subsystem.

Statistical forecasting/model training remains outside C1; deterministic scenario
comparison with supplied assumptions is included. The optional derived calendar-
month operation can remain outside R1 while C1 calendar work is planned, so that
the open extension experiment has an actual staged omission rather than a removed
working feature.

## How the core should grow

Use [next-core-semantics.md](next-core-semantics.md) for exact selection, key,
group/join and fold rules. The proposed additions are a small general kernel,
not a separate primitive for every vendor product term. Caps, fees, greater-of,
linear proration and guarantees mostly compose ordinary arithmetic/conditionals.
Tiers, event-triggered rate changes, waterfalls and reserve release schedules
compose fold/lookup/group with typed state. Joins may lower through grouped maps;
their specified multiplicity/order and unmatched diagnostics must still hold.

Units/quantity and currency-aware rate types need explicit typing/runtime/schema
extensions; do not bypass them by using untagged decimals. A `Rate<Units,USD>`
or equivalent checked representation is a typed monetary-per-unit value.
`FX<EUR,USD>` similarly denotes a direction, not an ordinary interchangeable
dimensionless rate at the boundary. Exact rate observations may store rational
values internally while the checker retains their dimensions.

Calendar/period relations are versioned data. Date stepping/difference and
explicit day-count operations, where missing, need total specified functions.
Do not use lexical date subtraction, ambient timezone or weekends as a substitute
for an applicable business calendar. The existing calendar-quarter phrase stays
available; add explicit fiscal-period and named-calendar authoring forms rather
than changing its meaning.

Losses, retroactive escalation, reserve stages and restatement are semantic
policies, not new arithmetic operators merely because each changes money.
Publish reusable policy recipes, variants, preconditions and movement equations.
A new custom fact/event kind or canonical field has to be supported at the
interface as well as in the expression evaluator. Signed support must reconcile
its sign convention, original event link and balance purpose end to end.

## Registration and authoring boundary

Adopt [policy-modules.md](policy-modules.md) for new contracts. Separate typed
interfaces, pure calculation modules, readable economic policies and run values.
Retain exact transitive pins and existing profile compatibility; stop adding
case-name branches for each new contract. Reusable first-order, acyclic imports
are sufficient initially; arbitrary functions or semantic-equivalence proving
are not prerequisites.

The current whole-expanded-core signatures remain honest bounded identity
checks. Preserve them for replay while migrating to exact module/interface
identities and deliberate registration. A parameterized rate edit within an
allowed term domain can change the terms/run identity; a different selector,
priority, allocation or rounding method changes policy, even when encoded by an
existing parameter. Every economic choice remains visible in readable main text
or an incorporated policy, with implementation expressions and actual values
in the review package as required by LD-01.

## Acceptance and independent evidence

For every C1 feature/variant, require a requirement locator, implemented positive
source+data witness, boundary/zero/empty and invalid witness, independent
intermediate/final amounts, targeted composition case, and explicit evidence
status. Include checks for:

- Rule overlap/tie/no-match/default/zero, failure in a demanded predicate and
  non-evaluation of unselected value bodies.
- Duplicate map keys, missing required lookups, empty groups, zero-title results,
  join multiplication and unmatched-row reconciliation.
- Ordered folds with equal dates, declared economic priority, permutation of
  physical input, missing tie policy and causal state across periods.
- Tier equality/crossing/split/retroactive variants; fixed-unit and participation
  order; aggregate versus line rounding; caps with prior consumption.
- Multiple participants and isolated pools/currencies/purposes/vintages; shared
  amount allocation, limited claims and reserve overapplication.
- Returns/reversals and original-rate linkage, authoritative replacement views,
  as-of versus effective time, replay with actual payment and duplicate correction.
- FX direction/rate/date/missing observation, fiscal/calendar edges, withholding
  as supplied policy and absence of bank-transfer side effects.
- Every registered module through canonical codec/validation/projection,
  native IR, generated execution, result/state, audit and strict finalization.

Retain the current 18,000/18,000/35 baselines and adopted mechanism fixtures.
Have independent financial oracles consume neutral source facts, not only
compiler-projected bindings or the compiler's own arithmetic/selection helpers.
An independent parser/interpreter is valuable but does not independently validate
the selected methodology or projection. The current Python language is acceptable
for independent financial oracles when implementation dependencies are excluded.

Preserve separate compiler, generated-execution and domain coverage measures.
The native interpreter audit is not direct emitted-code branch coverage. Use
target instrumentation or a justified target coverage method; do not infer
target coverage from equal output totals. Property-based bounded histories,
small exhaustive cases, constrained interactions and mutations supplement
reviewed cases without claiming every possible program is tested.

The research target stays three to five sourced public development cases overall,
with at least two materially different methods and separate synthetic coverage
fixtures. SV-readable/RQ-07 spelling or intake variants do not multiply the count
of independent contract methods. The supplied RR-03 answer now proposes Angel,
MQP and optional Roundlake; use [the response integration](rr03-response-integration.md)
for promotion conditions. Missing historical records must remain labeled gaps.
Keep Ilshin's detailed independent evaluation
outside shared development prompts and sources.

## Capacity and operational boundaries

Start measurement early: 100/1,000/10,000/100,000 combined facts/events while
independently varying title/participant counts, allocation fan-out, hot-pool skew,
periods, trace size and rational operand length. The current guard is a resource
limit, not evidence of speed or capacity. Record stage timing, peak memory,
trace nodes/edges and output size on named hardware. Obtain workload evidence
through RR-03 before promising realistic service levels or million-row support.

Use the [existing capacity plan](development-plan.md#scale-experiment-and-architecture-sequence)
to isolate compile/validation/settlement/audit/serialization costs and then
optimize measured bottlenecks. Deterministic maps/indexes or better sorting may
improve execution without new economics. Benchmark native calculation separately
from reference/IR comparison and process startup. Do not weaken exact arithmetic,
scope, diagnostics or required lineage to meet a timing target.

Signing, catalogue/rights availability administration, licensing negotiation,
document management, portals, bank payment execution and operational approvals
remain external applications. Their money-affecting facts and policy inputs
belong in canonical interfaces, not implicit I/O in settlement. This boundary
defines what broad **calculation** coverage means while allowing later service
integration. Full compiler proofs remain deferred, with operator/module semantics
and simple evaluators preserved for later Lean refinement arguments.

## Immediate compiler handoff

First resolve the concrete canonical Instant precision mismatch recorded in
ledger T10: a direct codec probe distinguishes .0000001 from .0000002 seconds
in exact semantics but the current Python datetime path collapses them. Add
canonical/native cutoff agreement checks before new ordered-time claims. This
is a correctness repair to existing behavior, not the deliberate extension gap.

Read the conformance ledger and implement K1 against its required boundary cases;
in parallel design module/interface descriptors and a neutral financial oracle.
Then implement K2/K3 and one composite C03/C07 method with explicit canonical
support. Promote the supplied RR-03 case candidates and investigate only their
remaining evidence gaps in parallel. Freeze R1 before adding its reserved optional
capability and run the extension experiment. Update the ledger with executed
witnesses and integration checks at each step; keep this proposal, the original
implementation snapshot and issued fingerprints distinguishable. No new compiler
code, performance result, domain approval or vendor-parity claim is delivered
by this document.
