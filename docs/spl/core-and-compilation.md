# SPL core and compilation specification

Version: proposed draft 0.1, 15 November 2026; research-response revision 20 November 2026. This document defines a candidate semantic contract for the first compiler. It does not describe an implemented SPL compiler or an approved interpretation of an agreement. The companion [language reference](language-reference.md) defines the authoring surface. Changes during implementation are expected; changes affecting calculated results require a new semantic version and migration evidence.

## 1. Architecture and boundaries

Implementation update, 20 November 2026: [implementation.md](implementation.md)
records the executable native Lean subset, total scalar runtime, independent
reference evaluator and canonical wrapper. The current readable iteration
elaborates the entire supported language to type-annotated `SPL.IR.Program`,
defensively revalidates its nodes and ports, emits directly from it, and supplies
separate native interpretation/audit DAGs. `spl-ir/0.1` is an inspectable artifact.
The IR is type annotated, rather than intrinsically typed dependent syntax.
Full compiler verification is deferred until after the demo. The narrow existing
scalar lemmas do not discharge the broader obligations in section 10.

The intended compilation path has more than two stages, while preserving two useful language layers:

```text
controlled SPL text
  -> parsed syntax with source spans
  -> resolved, typed and scope-checked schedule
  -> immutable functional core with independent evaluation
  -> generated Lean 4 module using a pure runtime
  -> Lake-built executable behind an input/output wrapper
```

SPL is the contract-facing language. Core is the small, explicit calculation language. Parsing and domain expansion must never ask a language model to interpret a clause during execution. Natural-language drafting assistance happens before review and compilation. A recognized phrase has one versioned expansion; unsupported text produces a diagnostic.

The generated module exports a settlement calculation. It does not read a clock, files, environment variables, network, exchange-rate service or mutable database. A run supplies every economic input, including material external decisions. A wrapper decodes and validates bytes, supplies the values, invokes the calculation, and writes results. Source adapters preserve source identities and perform approved normalization. Economic allocation, eligibility, fees, gates and recoupment belong to the schedule.

The core interpreter is specified separately from emitted Lean syntax. Agreement with that interpreter tests code generation. An independently authored reference calculation and hand-worked fixtures test the selected contract methodology; interpreter/emitter agreement alone cannot detect a shared interpretation error.

## 2. Proposed type system

Core is first order, statically typed, finite and immutable. Anonymous functions occur only as the bodies of finite collection operators; they cannot escape as values, recurse or call external code. Named definitions form an acyclic dependency graph. A fold carries state explicitly and does not introduce a dependency cycle.

| Type | Values and restrictions |
| --- | --- |
| `Bool` | `true`, `false`; no unknown truth value |
| `Int`, `Nat` | Mathematical signed and nonnegative integers; no machine overflow semantics |
| `Rational` | Canonical fraction `n/d`, integer `n`, strictly positive integer `d`, reduced by gcd |
| `Ratio` | Exact dimensionless rational; rates may be signed unless a declaration constrains them |
| `Money<C>` | Exact rational quantity with currency tag `C`; currency is part of the type |
| `Quantity<U>` | Exact rational with a declared unit; units cannot mix implicitly |
| `Date` | Valid Gregorian calendar date without time or timezone |
| `Instant` | Valid offset-bearing timestamp normalized by the adapter; no ambient local timezone |
| `Id<N>`, enum | Opaque stable identifier in namespace `N`, or member of a declared finite code set |
| `Text` | Display/evidence text; never implicitly parsed into an economic value |
| `Option<T>` | `none` or `some(value)`; absence is different from zero |
| record, tuple | Finite named fields or fixed ordered components with declared types |
| `List<T>` | Finite ordered sequence; duplicate values permitted |
| `Map<K,V>` | Finite partial function with unique keys and a declared total key order |

An indexed mapping with multiple indices is `Map<(AgreementId, PictureId, PeriodId, ...), V>`. It has exactly one output per complete key. Missing keys produce `none`, never an invented zero. The same data can be presented as an indexed definition in SPL without changing the map semantics.

Identifiers must be NFC at ingestion and use exact case-sensitive code-point equality after the interchange profile's validation; there is no locale-sensitive matching. Enumerations, dates, integers, opaque IDs and tuples of these have defined total orders. For identifiers the order is Unicode scalar lexicographic order; for tuples it is lexicographic field order. Maps do not expose implementation iteration order. Money and ratio values compare numerically, with money comparison requiring identical currency.

The initial executable slice is single currency. A schedule declares its currency and rejects conflicting input. Multiple currency tags may exist in the specification without implying v0 FX support. Future conversion must take a named observation, orientation and effective-date policy; no automatic conversion is permitted.

Financial values do not use `Float`/double. A decimal input such as `0.075` denotes exactly `75/1000`; `7.5%` denotes exactly `3/40`. The core can represent a proportional share such as `1/3` without premature decimal truncation. Transport may use decimal strings for inputs and a numerator/denominator record for a nonterminating intermediate. Display formatting is separate from quantization.

## 3. Core expression inventory

This is an abstract grammar, not an additional user-facing file syntax. `x` denotes a resolved binding ID, `T` a type, and `f` a nonrecursive operator body with explicit bound variables.

```text
e ::= literal(T,value) | variable(x)
    | let(x,e,e) | record(fields) | field(e,name) | tuple(es)
    | some(e) | none(T) | matchOption(e,noneBody,someVariable,someBody)
    | if(condition,thenBody,elseBody)
    | unary(op,e) | binary(op,e,e)
    | list(es) | map(xs,f) | filter(xs,predicate)
    | concat(xs,ys) | sort_by(xs,key) | fold(xs,initial,step)
    | sum(xs,f,zeroType)
    | make_map(rows,key,value) | lookup(map,key)
    | group_by(rows,key) | join(left,right,leftKey,rightKey)
    | choose_unique(rules,otherwiseBody?)
    | choose_priority(rules,otherwiseBody?)
    | quantize(value,quantum,mode)
    | require_some(option,diagnostic)
    | require(condition,diagnostic,body)
    | observe(nodeId,scope,evidence,e)
```

Each typed operator has a fixed signature. There is no unchecked cast, host-language escape, reflection, user-defined recursive function, arbitrary Lean snippet or call to a mutable service. Domain libraries are versioned expansions into this inventory. Adding an operator changes the core language and requires semantics and independent checks.

Arithmetic allows money addition/subtraction and comparisons within one currency, money times ratio, money divided by a nonzero ratio, and money divided by nonzero same-currency money yielding a ratio. Money times money is rejected. `min`, `max` and absolute value preserve units. `Nat` subtraction is checked and fails when negative, rather than silently truncating. Division by zero always fails in a demanded expression. Integer division, if added to the surface, must name its rounding direction; `/` in financial expressions denotes exact division.

A `require` assertion is not a theorem premise silently accepted by Lean. It is a runtime condition producing a stable diagnostic on failure. Static validation may discharge an assertion when its result is known, but must preserve its observable diagnostic if false. `require_some` converts a missing required value into a diagnostic. An optional field can be ignored only if the selected calculation does not demand it and the schema permits its absence.

## 4. Evaluation and collection semantics

Write `eval(program, inputs) = success(value, trace)` or `failure(diagnostics, trace)`. Successful results are immutable. No failure returns a finalized payable or a finalized successor state for the failed atomic scope. Diagnostics are data with stable codes, rule IDs, source spans and implicated business keys.

Evaluation is strict for ordinary arithmetic and record fields. `if` evaluates its condition and only its selected branch. Boolean `and`/`or` short-circuit left to right. Rule predicates are evaluated in stable rule-ID order; any predicate error blocks selection. Only the selected rule body evaluates. Thus a disabled gross branch need not divide by a missing or zero value, but required structural input validation still precedes calculation.

`choose_unique` evaluates predicates and requires exactly one matching rule. If none matches, an explicit `otherwise` body is selected; without it, selection fails. Two matches are an ambiguity even when their values happen to agree. `choose_priority` selects the unique matching rule with greatest declared integer priority; equal winning priority is an ambiguity. Defaults apply only when no ordinary rule matches. Neither file order nor lexical proximity resolves an overlap. Static analysis rejects provable ambiguities and runtime validation checks data-dependent ones.

| Operator | Normative result |
| --- | --- |
| `map(xs,f)` | Apply `f` once per member, preserving list order and multiplicity |
| `filter(xs,p)` | Keep members with true predicate, preserving order and multiplicity |
| `sum(xs,f,T)` | Exact addition of mapped values; empty list gives typed zero `T` |
| `sort_by(xs,k)` | Ascending key order; order-sensitive economic uses require a complete unique tie key |
| `fold(xs,z,step)` | Left fold: `s0=z`, `s(i+1)=step(si,xi)`; empty list returns `z` |
| `make_map(rows,k,v)` | Reject duplicate keys, including duplicates with equal values |
| `lookup(m,k)` | Return `some(v)` for present key, otherwise `none` |
| `group_by(rows,k)` | Map each observed key to its rows, preserving their relative order; empty input gives empty map |
| `join(l,r,lk,rk)` | Inner equijoin, full multiplicity, pairs ordered by left position then right position |

A group does not appear merely because a title exists in metadata. To emit zero-receipt titles, map over the explicit title universe and use a typed empty sum. Joins never invent missing values. Required one-to-one relations should use unique maps and checked lookups, avoiding accidental many-to-many multiplication. Aggregate queries must identify their amount kind and economic measure to prevent counting both a parent transaction and its cash child as receipts.

Unordered fact collections enter the calculation in canonical stable fact-ID order. Reordering a CSV with the same identities must not change the business result or canonical trace. An economic fold first sorts by its declared tuple, for example `(effective_date, contractual_priority, event_id)`. The last component can resolve an economic tie only when the schedule explicitly adopts that convention. A tie that needs a legal priority decision remains an error. No generic event-ID ordering can manufacture contractual priority.

Resource limits are implementation safeguards outside economic semantics. Exceeding a manifest-declared limit fails the run with a resource diagnostic; it cannot return truncated amounts, omit trace contributions or approximate a calculation.

The readable calendar phrase uses the added pure predicate
`is_calendar_quarter : Period -> Bool`: first-day Gregorian intervals Jan-Apr,
Apr-Jul, Jul-Oct or Oct-Jan. This has an explicit signature, independent native
and Python evaluation checks, and no fiscal/business-calendar inference.

## 5. Exact arithmetic and rounding

All intermediates remain exact until an explicit `quantize`. For quantum `q > 0` in the same unit, write `x/q = k + f` with `k=floor(x/q)` and `0 <= f < 1`:

- `floor` selects `k`; `ceiling` selects `k` if `f=0`, otherwise `k+1`.
- `toward_zero` selects floor for nonnegative values and ceiling for negative values.
- `half_even` selects the nearer integer; at `f=1/2`, select the even integer among `k` and `k+1`.
- `half_away_from_zero` selects the nearer integer; exact ties select the candidate with greater absolute value.

Multiply the selected integer by `q`. A nonpositive quantum or unit mismatch fails validation. For USD quantum `0.01`, half-even maps `1.005` to `1.00`, `1.015` to `1.02`, `-1.005` to `-1.00` and `-1.015` to `-1.02`. These are proposed language semantics, not an assertion about a particular contract's policy.

There is no ambient currency scale or automatic round-after-every-operation rule. The case profile must name the boundaries: row fee, picture earnings, pooled settlement, allocation, carry state or display. The research-integrated NUM-01 aggregate-cent scenario uses half-away-from-zero; half-even and per-line rounding remain separate explicit variants. Whole-dollar SV-01 and RQ-07 values do not require a new rounding operation. A case must pin its selected policy before freeze. If displayed rounded detail must add to a rounded total, the schedule must allocate the residual explicitly or report an identified rounding line. It must not conceal the difference.

### Ratio precision is a separate economic operation

The November research response reports an LG-M section 1.4(b) rule for in-scope financial ratios at their expressed decimal precision. This does not set monetary scale, identify every quotient as an in-scope ratio, or resolve negative ratio ties. Preserve the original expression unit and precision as policy metadata, independently of the normalized rational value. For example, two decimal places of a percentage imply a `Ratio` quantum of `0.0001`, whereas two decimal places of a dimensionless ratio imply `0.01`. Normalizing both values to fractions must not discard that distinction.

An approved expansion can use existing `quantize` on a dimensionless `Ratio` with an explicit quantum and mode. For the supplied positive synthetic check, `12.345%` becomes `12.35%`, then applying it to USD `10000` yields `1235`, versus `1234.5` without ratio quantization. This example selects the ratio, expression precision and operation order as fixture policy; it does not establish that either development branch contains that ratio. Positive half-up behavior does not authorize a particular signed mode without interpretation. Keep `NUM-01`'s aggregate cent half-away test and half-even alternatives as separate named synthetic profiles. There is no new universal money-rounding default.
A reusable allocation expansion takes a signed source amount, nonnegative exact weights summing to one, unique target keys, quantum and mode. First compute exact shares, then quantize each, then assign the residual to a declared target or distribute it using a documented largest-remainder algorithm and explicit tie keys. The chosen residual policy is economic configuration. Default iteration order is not a residual policy. Allocation validation proves that reported shares plus a declared unallocated remainder equal the source amount.

## 6. Dates, state and period boundaries

A reporting period is a half-open interval `[start,end)` of `Date`, with `start < end`. A fixture described as a calendar quarter includes its first date and excludes the first date of the next quarter. Every rule states which date it uses: receipt, incurred, posting, approval, payment or another supplied date. A source reporting interval does not imply a transaction day. Rules requiring unavailable day-level evidence fail or require a separately identified research policy.

Timestamp-to-date conversion belongs to a versioned adapter policy with an explicit timezone. It never uses the workstation's current timezone. An as-of cutoff controls which observations/approvals are available; an economic effective date independently controls applicability. Future-dated, late-observed and amended facts are selected by the schedule and run profile, rather than by ingestion order.

Separate actual receipt, credited-in-lieu, earned/nonrefundable, incurred, due, funded/paid, executed, approved and recorded/observed dates whenever the selected clause distinguishes them. A payment due date does not establish actual funding or opening-state recognition. A report deadline or fiscal-quarter book close does not select all expense dates. Contractual inclusive wording can normalize to half-open intervals only with an evidenced calendar transformation; the half-open representation itself does not interpret a clause. Business-day deadlines require the applicable versioned holiday/calendar facts and cannot be computed from weekends alone.

Snapshot availability and period membership are independent predicates. A December cash receipt first recorded in January can belong economically to December while being absent from an earlier snapshot. Late-captured amendments likewise preserve signing, effective and observation times and their approved transition policy. No general latest-amendment or posting-date fallback exists.
A candidate pure interface is:

```text
settle : ValidatedFacts × Parameters × OpeningState × RunContext
      -> Outcome<SettlementResult>

SettlementResult = {
  statements, detail, closing_state, reconciliation, trace, diagnostics
}
```

The compiled schedule is closed over its approved economic definitions and interpretation identity. `RunContext` contains the accounting period, explicit as-of/report dates, scenario identity and immutable bindings; it contains no mutable clock. Schedule/schemas/semantics/adapter/runtime identities are bound by the run manifest.

A state key includes balance kind, agreement, relevant participant/pool/picture scope, unit/currency and vintage when applicable. No generic undifferentiated credit balance is allowed. A recoverable advance, payable arrears, reserve and cumulative threshold meter have different economic identities. The schema records whether each kind is a nonnegative magnitude or signed quantity.

For nonnegative advance balance `A` and eligible nonnegative earnings `E`, the simple pilot expansion is:

```text
recovered = min(A,E)
payable = E - recovered
closing_advance = A - recovered
```

Require `A >= 0` and `E >= 0`; do not silently clamp negative earnings. Negative earnings, refunds and clawbacks need a case-specific policy. New advances enter `A` only through eligible supplied events and declared period logic. Where a financial fact and evidence event refer to the same payment or advance, selection must identify one authoritative economic contribution and link the other as evidence. Correction/replacement graphs must be acyclic and select a single declared active or reversal-based view; a replacement and its superseded amount cannot independently enter the same basis. A deductible acquisition advance and a participation prepayment cannot share a state key merely because both are called advances.

A reserve vintage obeys `closing = opening + additions - releases - applications + approved_adjustments`, with each movement's effect on earnings/payable declared separately. A payment fact is evidence of money already disbursed; a calculated payable does not create that fact. A later opening payable ledger can reference a prior result and separately reconcile actual payment events.

Rolling cumulative values use explicit opening meters plus current selected movements. A moving window requiring expired observations carries either the bounded dated history or a sufficient versioned state structure; an unqualified lifetime total is insufficient. A threshold declares whether it uses opening, current-close, period or rolling values, its equality comparison, and whether the rate change is prospective or retroactive.

### Gates and reserves require their own scopes

The broader post-Closing Contingent Participation Hurdle and per-work True-Cash Breakeven are separate conditions with separate evidence, dimensions and comparison operators. A case-level attestation for the broader hurdle must identify scope, effective coverage, evidence and selected assumption. It is not proved by the work-level comparison. A strict excess condition cannot be replaced by `>=`; equality may satisfy work-level breakeven while failing a distinct strict hurdle. Gate receipts, home-video gross payout proxy and supplied crossed-Net-Profits subtotal remain separately named values. Sharing a currency does not make those economic bases interchangeable. A supplied crossed subtotal demonstrates consumption of that input, not derivation of its missing title-level economics.

Opening and closing comparisons alone cannot prove a gate stayed clear throughout a period: eligible costs, returns or corrections may cause an intervening dip followed by recovery. A schedule requiring a continuously clear or after-breakeven gate needs an ordered event-path fold with every relevant receipt/cost/adjustment and declared same-event priority, or a separately evidenced attestation covering the relevant path and dates. Endpoint-only evidence supports only an endpoint calculation. A deliberately bounded opening/closing fixture must not be described as a continuous eligibility proof. Where after-breakeven wording affects a crossing receipt, excess-only, whole-crossing-row, next-row, whole-period and retrospective treatment are different policies; no compiler default selects one.

A reserve movement identifies its stage and named basis before it changes an amount: full-value gate economics, gross receipts before proxy, crossed net basis, earnings, or post-earnings payable. A basis reserve and a payment holdback require distinct state kinds and trace nodes. One reserve can affect multiple agreement-defined views with shared provenance; those projections are not multiple cash movements and must not be summed as such. Vintage, start trigger, cap unit/base, release deadline/calendar and application/release recognition require explicit policy. Passage of a liquidation deadline alone must not invent an actual cash payment. The response's LG-01 has zero reserve activity; synthetic nonzero holdback checks do not establish the sourced basis-reserve treatment.

Corrections similarly choose a scoped route: restatement from the original opening snapshot, or a prospective identified movement. Neither route is a language-wide accounting default. Preserve immutable issued statement, revised entitlement and actual cash payment separately. Payment applications reference a stable underlying obligation across statement revisions so that, for example, a revised `90` entitlement with `80` actually paid leaves `10` outstanding rather than a new `90` payment. A receipt reallocation changes an application, not the historical deposited cash. Capacity-limited fee corrections and participant overpayment offsets have distinct claim kinds, obligors, units and priority. Supplied authority must cover the chosen correction; an objection, provisional finding or calculation result does not create approval.
A sequence of periods is an external orchestration fold passing one validated closing state to the next opening. Opening state must match the expected boundary and policy lineage. An approved opening adjustment is a separate movement with evidence. A restatement creates a new run and, where later openings depend on it, a new dependent run chain; it never mutates prior issued outputs in place.

## 7. Settlement status and failure isolation

The safe initial profile is strict settlement. An atomic settlement scope contains all titles, claims, balances and participants connected by an economic pool or shared calculation dependency. A failure in any required member blocks the whole connected scope. Disjoint agreements may produce separate successful outcomes when the manifest declares separate scopes. A partial pooled payable must never masquerade as a complete result.

Validation distinguishes rejected input, unmapped facts, deliberate exclusions, eligible zero results and ordinary calculations. The transport codes are `rejected`, `unmapped`, `excluded`, `included` for input disposition and `calculated`, `calculated_zero`, `blocked`, `provisional` for outcomes, as defined in the [data contract](data-and-run-contract.md). Exclusion requires a rule and reason. A selected zero rate is a valid calculation with trace. Unknown codes and absent required references block their affected scope. Required unresolved payment policy blocks finalized payable. A scenario run may supply a named research assumption and show alternative amounts; `scenario_id` is orthogonal to final/preview execution mode. A complete final reconstruction may carry closing state forward within the same explicit scenario and policy lineage. It does not establish an approved actual settlement or historical replay. Unresolved alternatives remain blocked; preview results remain provisional and cannot supply consumable closing state.

Validate transport/schema and referential integrity first, then scope, policy completeness and opening-state compatibility, then arithmetic. Structural errors cannot be hidden by an untaken branch. Clause-conditional fields are demanded only in applicable branches. Independent validation diagnostics can accumulate in stable `(scope, code, source_id, rule_id)` order; an evaluation error stops its dependent expression. No runtime stack trace is part of the economic interface.

Suggested diagnostic families are `SPL-PARSE`, `SPL-NAME`, `SPL-TYPE`, `SPL-CYCLE`, `SPL-RULE-AMBIGUOUS`, `SPL-RULE-MISSING`, `SPL-KEY-DUPLICATE`, `SPL-REFERENCE-MISSING`, `SPL-DATE`, `SPL-CURRENCY`, `SPL-DIV-ZERO`, `SPL-POLICY-UNRESOLVED`, `SPL-STATE-LINEAGE`, `SPL-RECONCILIATION` and `SPL-RESOURCE`. Concrete suffixes and field shapes belong to the interchange contract.

## 8. Observations, trace and reconciliation

Named economic definitions, selections, assertions, movements, quantization and output fields are observation nodes. Core nodes carry stable definition IDs, source spans, clause/interpretation references and scoped business keys. Lowering preserves these annotations. Generated Lean evaluates values together with the required trace contributions, or uses a proven equivalent representation.

A trace is a finite DAG whose nodes identify operation, typed exact operands/result, contributing fact/state nodes, selected rule or branch, rejected alternatives and reason, evidence version and output references. For a lazy branch, report `not_evaluated` and its guard; do not invent a branch value. When a greater-of clause requires both candidates, both are evaluated and observed before comparison. Equal amounts require a declared branch-witness tie policy if downstream reporting or state depends on the winner.

Trace IDs derive from `(schedule_node_id, scope_key, source_or_iteration_key, observation_kind)`, using a canonical encoding. A storage digest may abbreviate that tuple, but collision handling must preserve identity. Run IDs qualify stored trace nodes; business comparisons ignore wall-clock metadata. Aggregate nodes link to all constituent contributions without repeating them as additional money. Errors link to their offending nodes even when no final statement exists.

Exact business observations include statements, detail, closing state, statuses, exception identities, reconciliation values and canonical economic trace. Physical evaluation order, temporary variable names, memory addresses, build timings and trace serialization whitespace are not observations. Trace arrays serialize in a documented canonical topological order with ID tie-breaking. Compiler optimizations may change internal nodes only if they preserve the canonical observable graph or an explicitly versioned equivalence relation.

For each source amount space and currency, reconcile control totals through rejected/unmapped, excluded, allocated and included amounts without counting the same amount twice. A row carrying multiple amount kinds has separate reconciliations. For each named basis, reconcile inclusions and deductions; for each balance kind, reconcile opening plus named movements to closing. For the pilot, additionally require `earned = recovered + payable` and `opening_advance = recovered + closing_advance`. Pooled recovery stays at pool scope unless an explicit attribution rule supplies a picture split.

## 9. Lowering obligations and Lean target

| Stage | Output and required checks |
| --- | --- |
| Parse | AST, exact source spans and surface version; reject unknown phrases and malformed syntax |
| Resolve | Stable binding IDs, explicit qualified scope keys, schema references and clause links; reject ambiguous names |
| Type and validate schedule | Unit/currency types, finite domains, declared inputs, selection strategy and DAG; reject implicit fallback or unallowed cycles |
| Elaborate | Expand `for each` to map, definitions to let/DAG nodes, scope queries to explicit filters/lookups, pooling to scoped aggregation and state equations |
| Core validation | Check every generated core node again; retain source/expansion map and interpreter-ready artifact |
| Emit Lean | Hygienic declarations, explicit types, finite folds, pure runtime calls and observation construction |
| Build | Compile with the pinned toolchain and runtime identity; reject build failures and warnings under repository policy |
| Execute | Decode/validate versioned inputs, invoke pure settlement, validate reconciliation and serialize canonical outputs |

Emission uses generated safe names derived from binding IDs; arbitrary input identifiers and evidence strings cannot become Lean code. Strings are escaped as data. The first emitter should favor direct definitions and runtime calls over optimizations. Map storage can initially be sorted association lists; later trees or hash maps must preserve abstract equality, key uniqueness and canonical enumeration. Exact rational runtime implementation and its Lean API should be selected and tested against the installed toolchain rather than assumed from the type name in this draft.

Generated pure definitions use total Lean code. Structural recursion over finite lists suffices for folds and evaluation; more complex terminating definitions require checked termination arguments. Do not introduce `partial`, `unsafe`, `sorry`, custom axioms, or `noncomputable` financial execution to bypass implementation obligations. Generated diagnostic-returning checks are executable computations, not unchecked proof assumptions.

Keep the current package organization: future core syntax/types/interpreter and front-end modules can live under `Participation/`; reusable pure arithmetic/state/trace support under a runtime subtree; semantic preservation theorems under `Participation/Proofs/`; small checked generated fixtures under `Generated/`; executable regression checks under `Tests/`. Existing `Participation/Compiler.lean` and `Runtime.lean` are toy infrastructure and should remain clearly identified until replaced deliberately. `Generated/Smoke.lean` is currently handwritten, not compiler output. Large generated artifacts belong in the external project artifacts directory.

Use the repository's pinned `leanprover/lean4:v4.35.0`, `lakefile.toml` and README setup. Code changes must pass `lake build`, `lake exe smoke` and new relevant checks. This document introduces no code changes and does not claim those commands validate its proposed language.

## 10. Correctness claims and trusted boundary

The owner selected authored Readable SPL as the starting point for the
per-contract certificate. The core-to-Lean statement below is one step in
that proof. See the [testing and verification strategy](testing-strategy.md)
for the complete source-to-artifact goal and boundary obligations.
The [certification pilot](certification-pilot.md) checks preservation from
two fixed authored schedules to their emitted Lean settlements over exact
rational amounts and empty opening state.

A future preservation target is: for each well-typed supported core program `p` and validated environment `i` satisfying its explicit input and policy preconditions, evaluating the compiled Lean calculation has the same outcome as independent core evaluation, under the versioned observation relation. Equality must include errors, selected branches, exact arithmetic, explicit quantization, closing state and required trace if these are claimed observables.

The general claim still requires formal source and target semantics, a definition of compilation, arithmetic and collection lemmas, and an observation model. The pilot proves the exact financial and closing observations of its bounded schedules. The toy preservation theorem covers natural-number literals and addition.

Separate claims are needed for surface elaboration preservation, parser correctness, typed-core validation, emitted Lean text/elaboration, input codecs, canonical serialization and any optimizing passes. A mathematical lowering theorem does not automatically verify its string emitter. Kernel checking of a theorem does not establish the truth of supplied accounting facts or the parties' agreement to an interpretation. Native Lean compilation and the execution platform remain part of the operational trusted boundary unless separately addressed.

Empirical checks compare hand calculations and an independent reference, core interpreter, and compiled execution on identical versioned values. Round-trip codec checks, source permutation checks, state carry, lazy-branch failures, overlap failures and reconciliation checks complement arithmetic examples. Performance, reviewability and compiler correctness each require their own evidence.

## 11. Freeze and extension contract

A freeze records surface grammar, core operator semantics, schema profile, diagnostics/status rules, arithmetic/rounding, trace observations, compiler/runtime/toolchain identities, approved case policies and oracle revisions. Preserve exact source and canonical core artifacts with digests. Rebuilding from the manifest must reproduce business observations even if execution timestamps differ.

Classify a new requirement as a parameter change, a new method over existing operators, a new surface expansion, or a new core capability. A surface convenience must publish its expansion and demonstrate equivalent results. A core addition needs typing, evaluation, failure, trace and validation rules before an emitter implementation. Do not claim an extension merely because a phrase becomes shorter. A held-out case that fits the frozen core is a valid result and should be reported honestly.

Unresolved implementation choices include the initial rational runtime representation/API, exact core artifact encoding and whether trace equality is exact graph equality or a defined quotient. These cannot silently alter arithmetic or financial output. Unresolved domain policies include negative earnings, advance timing and priority, Lionsgate fee-offset convention and reserve movement scope. These are supplied case interpretations or research questions, rather than gaps the compiler may fill automatically.

## 12. Evidence and local references

Design authority is the supplied `ResearchAgent/documents/Language_Design_Requirements.md` (R-02 through R-10 and the language/settlement sections) and `Screen_Participation_Language_Research_Plan.docx` (sections 7 and 8). Both are external project research records; preserve their source snapshots and digests in a case/release manifest rather than copying large research files into Git. The plan explicitly proposes controlled syntax, an independent functional core, Lean generation and a pure settlement function.

Lean implementation guidance is indexed in [Lean resources](../lean-resources.md). In the local pinned reference, `reference-manual/Manual/Defs.lean` documents total definitions and termination, and `Manual/BasicTypes/` covers integers, lists, options and maps. The installed runtime APIs still need compilation checks when implementation begins. The 20 November revision incorporates the supplied `SPL_Research_Responses.md` (November 19 verification) and `SPL_RQ05_RQ06_Accounting_Policies.md` (November 16 research response), especially the ratio/money distinction, temporal evidence, separate gates, basis-stage reserves and scoped correction routes. These are research findings and bounded synthetic policies, not completed professional approval. No held-out packet or answer key was consulted. No additional current vendor claims are introduced here.




