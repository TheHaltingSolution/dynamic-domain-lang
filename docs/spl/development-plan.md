# SPL development plan: feature coverage, validation and scale

## Execution update: E1 and implemented M1a continuation

The reusable K1–K3 kernel, generic registered module boundary and selected Angel,
MQP, waterfall and authorized-revision methods now execute. The disclosed
calendar-month extension is implemented in E1 (`0.4.1-dev`) after preserving E0
(`0.4.0-dev`), its supplied-date workaround and actual unsupported-call probe.
The E1 review bundle passes 15 registered runs, six legacy runs and three direct
mechanism runs. Narrow SV receipt benchmarks are measured; useful production
capacity and distributed execution remain unestablished.

M1a now adds four reusable pure financial libraries and a registered canonical
root selecting seven bounded tier/cap/floor methods, with
[readable economic policy](../../cases/m1/policy.md),
[neutral source fixtures](../../cases/m1/fixtures/period-marginal.json),
[source/interface guide](../../cases/m1/README.md) and an independent
[financial oracle](../../oracles/ordinary_royalties.py). The seven current-source
demo cases and the generic CLI marginal template pass. Sixteen independent
oracle checks pass. Following adapter schema/sequence corrections and a driver
fixture-byte/hash regression, the final full 17-group native IR/generated/
reference/oracle comparison passes in 481.020 seconds. The final 31-check
grouped run passes in 3.642 seconds; the current 84-target build passes. These
cover 47 new distinct tests, with the existing import guard also rerun. Discovery
finds 310 tests (263 frozen E1 plus 47 new), all verified across the clean frozen
263-check run and the new checks; no combined 310-test run is claimed.
M1a is published as profile `0.4.2-dev` in the current implementation baseline.
E1's original primary record remains archived byte-for-byte as
[`baselines/implementation-0.4.1-dev.json`](baselines/implementation-0.4.1-dev.json).

Use the [current implementation report and remaining phases](implementation.md)
for executable status, demo commands and the next C1, systematic-validation and
audit-capacity work. The [execution conformance update](conformance-ledger.md)
and [extension record](extensibility-experiment.md) distinguish current support
from the retained historical inventories below. Full C1 coverage and compiler
correctness proof remain unfinished. The November 20 milestones and original
November 21 planning review are preserved here as history; their absent-feature
and unmeasured-workload statements are not the current implementation inventory.

## Selected next work after E1

This continuation follows the finite K1-K3, M1-M3 and I1 sequence in
[the release scope](release-scope-ld02.md#finite-implementation-sequence).
K1-K3 and the bounded **M1a ordinary royalties** library are available for the
stated variants. Typed quantities, currency foundations, further financial
variants and audit integration remain planned. The table separates current
execution from unfinished validation and later deliverables.

| Workstream | Next deliverable | Acceptance boundary |
| --- | --- | --- |
| Verification baseline | Clean isolated frozen-E1 verification completed in the shorter workspace; the old freeze remains untouched. | All 263 tests pass in 1100.923 seconds, plus the 84-target build, both smokes and 15 native suites. All 287 frozen files and compiler/runtime/module identities are unchanged; no derived-fixture changes or new files outside `.lake`. Preserve the original full-run/rerun history and first long-path attempt (61 failures/two errors, 281 characters, `LongPathsEnabled=0`). |
| M1a financial library | Implemented: reusable period marginal/whole-base tiers, cumulative marginal meter, period/cumulative caps, separate nonrecoupable period guarantee, and explicit period tiers-then-cap composition. | Seven registered demo cases and generic CLI template pass financial checkpoints; 16 oracle checks pass. The final 17-group comparison passes in 481.020 seconds. Boundary/failure/state-carry checks are in `Tests/test_m1_modules.py`; published profile `0.4.2-dev` records the bounded slice. |
| M1b typed quantities | Explicit quantity and monetary-per-unit types, initially with USD results. Start with typed inputs using existing generic type syntax. | Quantity 100 at USD 1.50/unit gives USD 150; separately selected 50% participation gives USD 75. Wrong units, malformed transport and invalid dimensional arithmetic fail across native and canonical paths; zero and fractional quantities remain exact. |
| Audit transport | Experimental post-generation archive prototype implemented separately from canonical/compiler defaults; production integration remains planned. | Thirteen checks and 31 actual-trace round-trips pass. The real 100-receipt, 2,480-node trace shrinks from 7,604,969 to 2,853,622 bytes; one small priority-rates trace grows 47,096 to 48,598 bytes, so there is no universal shrink claim. Native generation memory is unchanged; no 1,000-/10,000-record scalability claim follows. Matching-workload byte/memory/timing measurements remain required. |
| M3a currency foundation | After the quantity/type boundary is established, add finite USD/EUR support and directional FX observations. | EUR 100 at USD 1.10/EUR gives USD 110. Reject mixed-currency addition, reversed/missing/ambiguous quotes and invalid date/cutoff selections. Retain exact pre-round values, explicit rounding and currency in outputs and state identity. |

M1a implements the already specified synthetic economic variants. It did not
require a new vendor session or another approval round. The modules remain core
`.spl` source with a separately pinned readable policy; no new natural-English
tier syntax or compiler/backend case branch was introduced. Quantity/FX interface
design and compact-trace design can proceed independently; changes to shared
checker/runtime/transport files need assigned ownership and sequential
integration. The clean verification run must not share files with active
development, source normalization or fixture-authoring changes. The completed
isolated E1 record is
`C:/Projects/Film_TV_participation_dynamic_DSL/e1v-949554/verification.json`.

### Implemented M1a financial acceptance cases

- A period basis of USD 150, first USD 100 at 10% and the remainder at 20%,
  produces **USD 20 marginal** versus **USD 30 whole-base**. Thresholds are
  lower-inclusive: at exactly 100 the results are 10 versus 20. Whole-base is a selected period method,
  not an implicit historical retroactive-escalation policy.
- For cumulative marginal tiers, prior basis 80 plus current basis 70 produces
  **12 current earnings** and **150 closing cumulative basis**. Split-event,
  physical-permutation and actual serialized next-period carry checks preserve the chosen economics.
- A cumulative cap of 100, opening consumption 70 and new entitlement 80 allows
  **30 currently** and closes at **100 consumed**. Period-cap consumption carries
  only within its recorded period; a new period requires explicit reset.
  Cumulative cap consumption cannot reset or inherit a different method's meter.
- Earned 80 under a nonrecoupable period floor of 100 gives **100 entitlement**.
  Keep this distinct from the existing advance-150/earnings-80 example, whose
  payable is zero and closing advance is 70.
- The selected composition reports **20 uncapped tier earnings** then **15
  capped entitlement**. Checks cover equality, zero/empty activity, exact fractions,
  invalid/gapped/overlapping brackets, duplicate identities, state scope and the
  selected nonnegative-basis restriction. There is no universal loss floor.

M1-01 requires an explicitly selected period facts view: out-of-period supplied
rows block, and fact/evidence observations must be strictly before cutoff.
The neutral schema is explicitly `m1-neutral/1`; bracket sequences must be actual
nonnegative integers, with strings, booleans and floats rejected. Duplicate
guards are within-run checks, not a general consumed-fact registry or settlement
idempotency mechanism. Direct actual closing-cell carry requires the adjacent
successor boundary; a gap requires explicit authorized boundary roll-forward.
Brackets have unique explicit nonnegative sequences, contiguous bands starting
at zero, positive finite widths and a final unbounded band; rates lie in `[0,1]`.
All declared nonempty tables are validated, including unused cap/floor tables;
cap/floor methods may supply empty tables. Meters retain method and scope and
accept only the run period or a prior period ending by the run start, preventing
future/overlapping state payloads. Read the exact
[selected policy](../../cases/m1/policy.md) and execute the review:

```powershell
python scripts/m1_demo.py --reuse-registration --output C:/Projects/Film_TV_participation_dynamic_DSL/artifacts/spl/m1-royalties
```

Guarantee/cap/advance precedence, retroactive escalation, crossing-event
alternatives and minimum-payment bookkeeping need an explicit selected policy
before they are combined. These are later method variants rather than hidden
defaults in M1a. The implemented M1a witnesses update the specific C04/C05
rows in the [current coverage matrix](conformance-ledger.md#current-c1-family-coverage-e1),
without marking either entire family complete. The compact archive experiment
is [separate tooling](../../scripts/spl_trace_transport.py), not a canonical
trace-format migration or a solution to native trace-generation memory.
Its [measurement driver](../../scripts/measure_trace_transport.py) pins schedule,
bindings and native executable hashes and relies on a prior successful
`lake build spl` for source/binary correspondence.

### Validation and later capacity work

Every added method gets its own canonical inputs, independently calculated
intermediates/final values and failure cases as it is implemented. Add selected
pairwise interactions and bounded histories, followed by emitted-program branch
measurement and mutation tests. Do not postpone this work until full C1, or
describe a finite corpus as every possible feature combination.

The first quantity slice needs no new readable literal grammar; economic policy
text must still identify the units, rate and separately applied share. FX must
extend the checker, bindings, canonical codecs, state scopes/keys and output
validation together. Accepting an EUR literal alone is not multi-currency
support. Use an explicit initial quote-date policy with no inferred fallback;
research supplies a different policy only for a named sourced contract.

Once compact audit transport passes compatibility checks, run the RR-03 mixed
synthetic workloads at 100, 1,000 and 10,000 records with separate compile,
validation, settlement, audit and serialization measurements. Characterize
ordered histories and hot pools as well as receipt-only cases. Larger cohorts
follow measured memory/storage headroom. Distributed execution and million-row
capacity remain later work; whole compiler proofs remain deferred until after
the demo as requested.

## Original next-stage plan: 21 November 2026

Language-design response now available: [LD-02 finite release scope](release-scope-ld02.md),
[conformance ledger](conformance-ledger.md),
[precise next core semantics](next-core-semantics.md) and
[policy/module registration](policy-modules.md).
The proposed C1 target covers the named ordinary royalty, period-accounting,
currency/calendar and settlement-calculation families through staged gates.
This refines the scope; it does not mark Phase B or canonical feature integration
complete. Evidence recommendations in the [vendor inventory](vendor-feature-evidence.md)
are inputs to that design decision, not claims of vendor-equivalent execution.
The [RR-03 response integration](rr03-response-integration.md) now records the
supplied answer and finite first R1 scope. Angel is the next independent public
development family; MQP supplies the selected ordered-accounting candidate and
Roundlake is optional for the waterfall slice. Workload budgets remain proposals.
The [extensibility experiment](extensibility-experiment.md) explicitly preserves
an intentionally deferred capability for a frozen-baseline extension demonstration;
it remains separate from routine gap completion and custodied held-out evaluation.

The readable direction is accepted. The next objective is a deliberately scoped
feature-complete release, stronger independent accounting evidence and measured
capacity. The current `spl-implementation/0.3.0-dev` baseline demonstrates the
bounded SV/RQ-07/LG methods and three separate mechanisms. It does not implement
the entire design draft or establish large-input capacity. Its recorded 132-test
result is the November 20 result; the planning review did not rerun the suite.

This plan follows three delegated read-only reviews of design conformance,
testing and performance. It also uses the existing external language-design
requirements and compiled-language testing guide. Earlier implementation phases
below remain the historical milestone record. This planning update does not
rewrite the earlier content-pinned baseline or its fingerprints.

### Preliminary coverage and gaps

| Area | Current capability | Next decision or gap |
| --- | --- | --- |
| Readable language and compiler | Controlled readable syntax, typed IR, checking, pure Lean generation, native interpretation and diagnostics | Maintain readability as capabilities grow; full draft conformance needs a feature-by-feature inventory |
| Financial methods | SV funding branches/pooling and LG proxy/gates/greater-of; exact USD amounts, five rounding modes, Date and Instant | Priority-rule tables required by RULE-01 are absent; broader tiers/waterfalls need explicit semantics and fixtures |
| Collections and relationships | Lists, records, options, map/filter/sum/sort and comprehensions | Typed keyed maps/lookups, grouping/joins and general deterministic ordered folds are not implemented |
| State and timing | Prepayment carry, funded advance and reserve-vintage mechanism tests | General event histories, gate crossings/dips, losses, competing offset priority and contractual reserve stages remain incomplete or policy-dependent |
| Corrections and actual payment | Supplied revised entitlement less independently supplied payment | Full historical restatement/replacement/replay and separately authorized prospective adjustment are additional work |
| Canonical execution/configuration | Three bounded physical profiles; source/policy/evidence pins; registered readable methods | Separate compiler expressiveness from wrapper profile support. A method edit needs a deliberate policy revision; arbitrary new contracts are not automatically canonical profiles |
| Broader currencies/calendars | USD, half-open dates and readable Gregorian quarters | FX, other currencies and fiscal/business calendars are release-scope choices, not current capabilities |
| Independent validation | Authored expected checkpoints plus Python reference, native IR and generated Lean comparisons | A separate handcoded financial oracle, systematic coverage reports and held-out evaluation are still needed |
| Scale and concurrent execution | Small reproducible fixtures and fixed resource guards | No measured capacity or distributed settlement infrastructure; the 100,000 combined fact/event cap is a guard, not a throughput result |

This is a preliminary inventory, not the final conformance ledger. Phase A must
trace every design requirement, grammar form, primitive, setting and diagnostic.

### Work phases and acceptance

| Phase | Work and deliverable | Completion condition |
| --- | --- | --- |
| A. Define the next release | Build a requirement/feature ledger: semantics, source form, IR/runtime/checker support, canonical profile support, limitations, tests, evidence and priority. Tag missing primitive, missing sugar, missing adapter/configuration, unresolved policy and out-of-scope workflow separately. Send LD-02/RR-03 handoffs through the user. | Every requested feature has an explicit status and disposition; a finite release scope and deferred list exist. No blanket claim of industry feature completeness |
| B. Add case-driven capabilities | First resolve the existing RULE-01 priority-selection gap. Select the smallest subsequent extensions supported by clauses and numeric discriminators: keyed lookup/grouping and ordered state transitions where needed; integrate selected mechanisms into canonical profiles. Keep policy questions attached to their particular cases. | Every accepted capability has semantics, readable syntax, native checking/IR/emission/interpreter support, canonical boundary or explicit experimental status, and positive/boundary/failure/composition tests |
| C. Build independent validation | Extend public development evidence; add separate financial oracles; generate valid/invalid schedules, bindings and state histories; measure compiler, emitted-execution and domain coverage; use mutations and constrained combinations. | Every in-scope feature has executed witnesses and reviewed expectations; all required interactions pass, failures minimize to regressions, and arithmetic disagreements are resolved rather than goldens overwritten |
| D. Establish and improve capacity | Begin measurement in Phase A, then optimize after correctness anchors exist. Benchmark stages and realistic workloads; remove algorithmic bottlenecks, cache/execute compiled schedules, then consider safe independent parallelism and distribution. | Measured latency/memory/storage budgets are published for named hardware/workloads; optimized/parallel results preserve exact business/state/error behavior and required audit semantics; retries/failures cannot advance state twice |
| E. Freeze, evaluate and demonstrate | Freeze grammar/core/schema and corpus; perform independently custodied held-out encoding, reproducible demo and extension assessment; document compatibility/versioning and unresolved limits. | Frozen release reproduces the accepted corpus and measured workload envelope; evaluator protocol is completed and reported honestly. Full compiler proofs follow the demo as requested |

Phases B and C repeat together for each feature. Public-case research and oracle
authoring can start during Phase A. Establish a small performance baseline early;
deep optimization and distribution follow correctness evidence. Do not postpone
all testing until a feature-complete compiler exists.

### Research and feature selection

The researcher should compare the feature ledger with relevant public material
and legitimately accessible subscription/private evidence. Return a dated source
and product/version/context for each finding, distinguishing documented,
observed and merely advertised behavior. Classify calculation semantics,
input/output adapters and external operational workflow separately. Signing,
licensing administration, portals and payment execution are outside the current
calculation-language objective unless a chosen calculation needs supplied facts.
Vendor feature parity is not the completion definition for SPL.

For each proposed addition return its economic meaning, minimum contract/fact
example, expected intermediate and final values, competing interpretation if
material, relevance to film/TV and priority. The language-design agent then
determines whether existing expressions suffice, reusable sugar is enough, a
new primitive is needed, or the change belongs in data/configuration. No syntax
is chosen by a vendor feature name alone. LD-02 and RR-03 in
[implementation-questions.md](implementation-questions.md) now have linked design
and user-supplied research responses. Remaining targeted evidence gates and
held-out custody rules remain in force; no outreach is implied.

Prioritize extensions that add materially different methods to the existing
corpus. Full correction/restatement, contractual reserve treatment, ordered
waterfalls/dynamic gates and loss carry need selected cases and explicit answers.
FX or further calendars enter the release only when evidence and scope justify
them. Preserve Lean compiler/runtime boundaries and pure settlement functions.

### Baselines, oracles and systematic testing

The original research target is three to five reproducible public cases overall
with at least two materially different calculations. Count contract families
and economic methods, not original/readable spellings or multiple reconstructions
of the same Skouras example. Add cases for coverage gaps rather than volume.

Prefer paired contract provisions and independently supported expected accounting
results. A complete case package contains source/version/clause and permitted
locator, interpretation and assumptions, facts/events and original opening state,
SPL, configuration, expected fees/bases/earnings/offsets/payable/closing state,
diagnostics and review status. A worked calculation lacking a full contract is a
mechanism baseline; vendor UI/workflow evidence alone is not a contract oracle.
Private evidence may inform a permitted research record while portable public
fixtures remain project-owned and reproducible without an account.

Write small Python financial oracles directly from neutral source facts and
interpretation records. They must not import `spl_compiler`, parse SPL, consume
compiled IR, call `project()` or share economic helpers with the implementation.
Use their own date selection, grouping, exact arithmetic/rounding and state logic;
sharing a neutral file schema is acceptable. Review hand examples first. Feeding
only compiler-projected bindings to the oracle would miss projection errors.
Compare all material intermediates, scope, state and errors, not just payable.
The user's Python choice is compatible with independence; a different host
language is not by itself a guarantee of independence.

Maintain three separate coverage reports:

1. Compiler coverage: grammar productions, type rules, IR variants, emission,
   runtime operators, diagnostics and wrapper validation/finalization paths.
2. Actual generated-settlement coverage: branch arms, lazy evaluation/skips,
   selection outcomes, empty/nonempty collections, assertions and state updates.
   The existing interpreter trace is not evidence of emitted-code execution;
   add direct target instrumentation or a validated target coverage mechanism.
3. Domain coverage: receipt recognition, fees/bases/shares, pool isolation,
   priority, gates, reserves, payments/corrections, authority and timing histories.

Generate both well-typed contracts with matching data and deliberately invalid
source/IR/packages. Record seeds, size bounds and minimized failures. Use
exhaustive enumeration for specified small finite domains, constrained pairwise
coverage across supported features, and stronger targeted interactions for
rounding/aggregation/sign, laziness/missing input/forward references,
state/scope/period/duplicates and gates/bases/timing. Every possible program or
feature combination is unbounded; line coverage alone is not correctness.

Use mutations such as `<` to `<=`, changing recognition date, wrong fee base,
duplicated cash, wrong reserve vintage or eager branch evaluation. Require a
test witness or explanation for surviving equivalent/unreachable mutants.
Apply permutation, exclusion and split/merge properties only where the selected
semantics permit them; caps, rounding and event-sensitive rules invalidate some
otherwise plausible properties. Generated method variants use explicit
experimental binding runs until deliberately registered as canonical policies.

### Scale experiment and architecture sequence

Measure 100, 1,000, 10,000 and 100,000 combined facts/events, plus the current
small fixtures. A million rows is a later target requiring a new resource
profile and evidence; raising the guard does not establish support. Independently
vary pictures, schedules/pools, hot-pool skew, allocations, periods, trace
fan-out and rational operand sizes. Derive realistic distributions and service
targets from the research workload; keep worst-case stress tests separate.

Measure cold/warm source compilation, validation/projection/hashing, decoding,
pure compiled settlement, reference/IR execution, audit ordering/serialization
and end-to-end publication. Record latency/CPU, peak memory, input/output bytes,
trace nodes/edges and scaling curves. The current `lean` wrapper backend still
runs reference and native-IR comparisons; it is not an isolated native benchmark.

Known candidates for profiling include picture-by-fact scans, insertion sorts,
linear graph/cache lookups, repeated trace ordering, whole-JSON copies and
repeated compiler/process startup. Optimize measured costs with indexed pure
structures, efficient builders/stable sorting, deterministic graph ordering,
compiled-schedule caching keyed by complete dependencies and actual native
execution. Keep exact arithmetic and required provenance. Trace volume must be
budgeted and stored efficiently rather than silently omitted.

Parallelize independent dependency components before distributing them. A pool,
shared gate, allocation parent or state dependency may connect many titles;
arbitrary row/title chunks are not necessarily independent. Preserve ordered
events and sequential state across periods. Distributed execution additionally
needs idempotent retries, global duplicate/conservation checks, invocation-specific
staging and an atomic final artifact/state commit. Current envelope-last output
and semantic-digest directories do not provide concurrent transaction safety.

### Immediate work and delegation

Use the new feature ledger and integrated LD-02/RR-03 responses, with executed
validation still to be recorded as features are added. In parallel, draft one independent SV financial oracle and a stage
benchmark harness, with no new claim of feature completeness or capacity.
Then implement RULE-01 against its designed semantics and independent boundary
cases, and select the next method from the reviewed evidence.

Keep separate agent workstreams for design/conformance, domain evidence,
independent oracle/corpus, native compiler and benchmark/runtime work. Use one
integration owner for shared interfaces and final verification. Each iteration
updates the feature ledger, case expectations and change record together.
Use a fast targeted check set during iteration and the full build/smoke/differential
suite at integration. Compiler proof work remains deferred until after the demo;
future optimizations should retain a simple pure specification for refinement.

## Completed implementation phases: 20 November 2026

Working plan, 20 November 2026, implementation profile `spl-implementation/0.3.0-dev`.
This continues the executable synthetic milestone with the supplied language-design
and rights-management research answers for the named cases.
Full compiler correctness proofs are deliberately deferred until after the demo.
The author's readability target is the English-like Skouras participation schedule
supplied in the conversation, including named financial definitions, conditional
funding methods, pooled recoupment and separate picture/participant reports.

## Phases and acceptance

| Phase | Deliverable | Acceptance | Status |
| --- | --- | --- | --- |
| 1. Establish the authoring contract | Controlled readable grammar, actual SV source, explicit supporting bindings, phrase expansions and question log | Main source follows the user's flow; percentages and multiword financial names compile; ambiguous/unsupported text gets a source-local diagnostic | Implemented; user confirmed direction and requested refinement |
| 2. Complete the current typed core | Explicit typed immutable IR for every currently supported expression, source/citation mapping and inspectable JSON artifact | Both old and readable sources elaborate through this IR; unsupported forms fail; typed IR is an actual compiler boundary | Implemented; independent annotation/scope validation also guards public entrypoints |
| 3. Native explanation | Independent native IR interpretation and deterministic trace DAG | Emitted execution, native interpretation and Python reference agree on values/state/error codes; native trace records dependencies, exact values, lazy branches, decisions and zero outcomes | Implemented and integrated; full trace proof remains deferred |
| 4. Integrate and iterate | Readable SV, RQ-07 and LG examples; CLI/wrapper, reports and regression suite | Existing 18,000/18,000/35 baselines, strict LG timing and serialized carry preserved; standalone parameter/method edits work; primary errors point to readable source | Implemented; canonical finalization of a changed method requires an explicitly revised policy registration |
| 5. Extend selected accounting scenarios | Explicitly named positive advance, correction/payment and reserve scenarios, plus required policy/data questions | Each mechanism has distinct event/state kinds, independent expected intermediates, atomic failures and source or named synthetic policy; no disputed policy becomes a default | RR-01 funded-date/separate-observation policy and RR-02 V1/V2 reserve separation incorporated; supplied-entitlement/payment reconciliation retained; full authorized CORR-01 restatement remains future |
| 6. Demo and stabilize | Reproducible native executables, pinned review bundles, revised docs and next-iteration ledger | All required build/smoke/regression checks pass; user can read source alongside English and inspect generated results; limits and remaining review gates are explicit | Reconciliation iteration delivered with incorporated-policy pins, whole-core signature validation, source/parameter review and external `research-reconciliation` bundle; current fingerprints/check records are in the implementation baseline and iteration log |

## Work boundaries

- Readable authoring is controlled syntax with documented deterministic expansions.
  Execution never asks an LLM to interpret natural-language clauses.
- Technical input/state/evidence bindings remain inspectable supporting material;
  they should not obscure the main participation schedule.
- Financial choices remain explicit: receipt dates, distinct deduction schedules,
  qualifying funding/valuation, pool authority, rounding and state purposes.
- Existing programmatic sources remain executable regression inputs.
- Incorporated readable policies pin both their documents and registry entries.
  Complete ordered expanded-core signatures guard the bounded registered methods;
  review artifacts expose financial-rule and supporting-expression locations plus
  the required parameter values. Structural agreement is not a semantics proof.
- Actual advance funding selects the quarter; separate issue and supporting
  evidence `Instant` timestamps must be strictly before the pinned cutoff.
  Exact offset normalization preserves subseconds. Pooling follows selected
  additions before nonnegative earnings without choosing FIFO or intraperiod order.
- Reserve state retains scope, purpose, currency and balance for V1 and V2
  separately. Applications and releases cannot borrow another vintage's balance.
- Do not broaden historical interpretation, claimed agreement coverage, expert
  approval or held-out evaluation by completing an engineering stage.

## Delegation and integration

The readable-surface agent owns `SPL/Readable.lean`, its independent Python
counterpart, readable cases and grammar tests. The typed-IR agent owns `SPL/IR.lean`,
`SPL/Elaborate.lean`, native emission and checker integration. The native-trace
agent owns `SPL/Trace.lean` and `SPL/Interpret.lean`. The orchestrator owns CLI,
canonical run integration, accounting-case selection, review artifacts and this
plan. Shared-file changes require direct coordination between owners.

Each implementation iteration records interfaces, checks, decisions and remaining
work in a short handoff. New compiler behavior needs an observable positive case
and a meaningful failure or boundary case. Main gates remain `lake build`,
`lake exe smoke`, native SPL checks, independent numeric expectations and the
Python/native differential suite.

## Questions and review

The first user review accepted the main readable SV direction. Bindings stay in
the footer for this iteration. The source is not frozen; contract-reader and
accountant review, broader economic policies and held-out evaluation are separate
remaining gates. The next iteration should be driven by concrete reader tasks
and new selected clauses, preserving the existing regression calculations.

Questions for the external language-design or royalties-research agents are
recorded in [implementation-questions.md](implementation-questions.md). The supplied
answers and their bounded dispositions are recorded in
[research-answers-2026-11-20.md](research-answers-2026-11-20.md) and
[implementation-answers.md](implementation-answers.md). A question
states the decision, alternatives, affected observable behavior and smallest
discriminating example. The user forwards questions; no external messages are
sent automatically. Broader contractual video-reserve stages/caps, dynamic gates,
negative earnings/losses, historical restatement and competing offsets remain
unresolved or unimplemented. Reader/accountant review, held-out evaluation and
full compiler proof remain separate future gates. See the
[implementation baseline](implementation-baseline.json) and
[iteration log](iteration-log.md) for the current verification record.
