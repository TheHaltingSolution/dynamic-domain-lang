# SPL compiler session handoff

**Active completion:** first read [the current checkpoint](completion-checkpoint.md),
the [finite plan](completion-plan.md) and [backlog](completion-backlog.json).
New independent financial slices, generated validation and measured trace
transport now supersede more of the historical absence statements below.
The older campaign and handoff retain their dated scope.

**Continuation update, 23 November 2026:** the initial feature/test matrix and
bounded validation harness described below are now implemented and verified.
Read the [current validation guide](conformance-validation.md) and
[verification index](conformance-validation-result.json) before resuming the
older planning sections. Eight generated cases, 14 mapped test methods and
19 new harness checks pass; six matrix gaps remain. Next add successful
else/short-circuit/selection templates and separate invalid-source/IR/package
generation. The historical handoff below records the earlier `3cc3600` starting
point; its statements that the harness had not started are superseded by this
continuation. Kernel baseline, proof limits and the pre-FX gate are unchanged.

23 November 2026. For the next implementation session in
`C:\TheHaltingSolution\dynamic-domain-lang`.

The native Lean compiler, typed quantities and the dated Quest half-even method
are implemented. The next proposed engineering task is a feature/test matrix
and generated conformance-validation harness. **That harness has not been
started.** The user requested this handoff instead of beginning that work.
The requirement to identify a necessary future compiler extension remains open;
native EUR/FX work is still behind the existing selection gate.

## Resume here

1. Read [AGENTS.md](../../AGENTS.md), this handoff and
   [the Lean resources guide](../lean-resources.md).
2. Check Git state before editing. The implementation checkpoint is local commit
   `18a16811b4426a0500860ab76785c85547421514` on
   `feature/spl-typed-quantities`. A documentation-only handoff commit may follow.
3. Read the current sections of [implementation.md](implementation.md),
   [conformance-ledger.md](conformance-ledger.md) and
   [development-plan.md](development-plan.md). Their historical sections retain
   earlier absence statements and verification counts; those are not current
   inventories.
4. Start with the validation phases below unless the user redirects the work.
   Preserve the existing kernel baseline, financial controls and authority limits.
5. Delegate independent work with explicit file ownership. Keep compiler and
   schema sources stable while integration runs are executing.

No implementation job was running at handoff preparation. The three most recent
child agents had completed their work. Their final messages describe their own
handoff moments, sometimes before root ran the final native comparisons; the
root verification records below are the final execution evidence.

## Mission and user decisions

SPL, Screen Participation Language, describes film/TV participation and royalty
calculations in controlled, readable contract language. It lowers through an
explicit typed core/IR to pure Lean 4 settlement calculations, with original
facts, policy selections, state, exact money, evidence and lineage retained.
The broader research asks how a domain language and its compiler can evolve
when a previously unsupported contractual requirement arrives.

The practical goals are broad calculation coverage, independently checked
results, usable audit output, measured scale and an eventual Lean correctness
argument. Vendor feature parity, historical account approval and production
payment execution have not been established.

User instructions that remain important:

- Use the native **Lean compiler frontend**. Python supplies an independent
  reference implementation, adapters, orchestration and financial oracles;
  it is not the primary compiler frontend.
- **Do not prove the whole compiler now.** Keep source/target semantics and pure
  boundaries suitable for later proofs. Never add `sorry` or custom axioms.
  The toy proof and existing scalar lemmas do not verify the SPL pipeline,
  dimensional operations, canonical wrapper or economic interpretations.
- Preserve the accepted readable direction. The user explicitly approved
  [sv01-readable.spl](../../cases/sv/sv01-readable.spl): financial clauses first,
  technical bindings in a footer. Original core `.spl` files remain regressions.
  New algorithmic libraries such as Quest have separately pinned readable
  policies; they did not add unrestricted natural-language interpretation.
- Use sub-agents heavily for sustained implementation, with root acting as
  orchestrator. Continue authorized routine work without repeated permission
  questions. Ask specific design/research questions when an actual ambiguity
  affects semantics.
- Keep source, proofs, small fixtures and documentation in Git. Toolchains,
  large traces, downloaded references and research datasets belong outside Git.
- Keep calculated, issued and actually paid amounts distinct. Missing payment
  evidence does not establish numeric zero paid. Synthetic policy selections
  do not establish professional approval.
- Do not manufacture a missing compiler capability merely to demonstrate
  dynamicity. The stronger extension-selection requirement is explained below.

## People and agents

### External collaborators reached through the user

| Role | Responsibility and current resources |
| --- | --- |
| Project owner/user | Chooses project scope and priorities. Can forward messages to the two external agents. Has Windows admin access, but routine development has not required elevation. |
| Language-design agent | Designed SPL, reviews semantics and possible old-language encodings. Main responses: [implementation-answers.md](implementation-answers.md), [release-scope-ld02.md](release-scope-ld02.md), [dyn02-design-answer.md](dyn02-design-answer.md), [quest-two-flow-fixture.md](quest-two-flow-fixture.md). |
| Royalties/rights-management research agent | Reviews actual clauses, rights-management methods/software, accounting policies, worked baselines and workloads. Its answers are integrated in the research documents and targeted follow-ups below. |
| Aditya Kistamsetty, GitHub `kspaditya` | Collaborator who reviewed/approved the first compiler PR. PR #1 was merged. Do not assume a new review request has been sent for the local follow-up commits. |

Both external agents should review a proposed required-extension candidate:
research establishes contractual necessity; design attempts faithful existing-
language encodings. Draft messages for the user to forward. Do not independently
send external messages without authorization.

### Internal implementation delegation

The latest child names were reused from the quantities work. Handles may not
survive into a new session; recreate agents by responsibility when necessary.

| Previous child | Latest owned work |
| --- | --- |
| `/root/quantity_native` | Native quantity changes and defensive IR admission; later `cases/quest/power.spl`, `charge.spl`, `Tests/test_quest_native.py`. |
| `/root/quantity_canonical` | Generic quantity codecs/module/state integration; later Quest registration, mechanical transport, descriptors, calendar/source indexes and `Tests/test_quest_modules.py`. |
| `/root/quantity_python` | Quantity reference model/checker/emitter; later independent Quest oracle, neutral fixture and `Tests/test_quest_oracles.py`. |
| Earlier mechanism agents | `/root/advance_answer`, `/root/authorized_revision`, `/root/c07_waterfall`, `/root/calendar_extension`, `/root/canonical_mechanisms` handled their named slices. Their outputs are integrated; do not assume those handles are live. |
| Root | Shared contracts/file ownership, integration, demo drivers, source fingerprints, verification, artifacts, documentation and local Git commits. |

For the validation milestone, a useful split is: inventory/matrix; independent
generators/oracles; trace coverage/mutation analysis; root owns the CLI/report,
integration and final checks. Let oracle authors work from neutral requirements
before reading the implementation being tested.

## Workspace and important resources

| Location | Purpose |
| --- | --- |
| `C:\TheHaltingSolution\dynamic-domain-lang` | Git checkout; start commands here. |
| `C:\Projects\Film_TV_participation_dynamic_DSL` | External project root. |
| `...\ResearchAgent\documents\Screen_Participation_Language_Research_Plan.docx` | Original overall research plan. Later user instructions defer whole-compiler proofs. |
| `...\ResearchAgent\documents` | Supporting research and supplied replies. Prefer integrated indexes before loading the whole corpus. |
| `...\ResearchAgent\documents\SPL_Research_Responses.md` | Controlling earlier research response index; see [compiler-handoff.md](compiler-handoff.md) for reviewed identity and limits. |
| `...\ResearchAgent\documents\SPL_RR03_Coverage_Benchmarks_and_Workload.md` | RR-03 feature/baseline/workload response; integrated in [rr03-response-integration.md](rr03-response-integration.md). |
| `...\ResearchAgent\fixtures\screen-accounting-package` | Original synthetic RQ-07 intake and dictionary. Shareable raw inputs are also in `cases/rq07/source`. |
| `...\environment\elan` | Elan/Lean/Lake installation. |
| `...\environment\python\python.exe` | Working embedded Python. |
| `...\reference\lean4` | Official local Lean 4.35.0 references. |
| `...\reference\quest\quest-ex99-1.html` | Downloaded actual SEC response body; source index in `cases/quest/source-index.json`. |
| `...\artifacts\spl` | Large run outputs, native traces, verification logs, source freezes and experiments. |
| `.lake/` | Disposable ignored build output and local helper scripts. Never rely on it as the only copy of a deliverable. |

Paths abbreviated by `...` in this table start at the external project root.
Do not import restricted Curve or detailed independently held-out evaluation
material into implementation prompts. Disclosed development examples are not
unseen holdouts. No new paid access is needed for the current engineering work.

## Reading order and design authority

| Document | Why to read it |
| --- | --- |
| [Design index](README.md) | Current entry point; points to later execution updates. |
| [Implementation report](implementation.md) | What actually executes, demo commands, scope and performance limits. |
| [Conformance ledger](conformance-ledger.md) | Feature-family/native/canonical status and witnesses. Historical absence rows remain visible. |
| [Development plan](development-plan.md) | Current staging and remaining validation/performance work. |
| [LD-02 release scope](release-scope-ld02.md) | Finite C1 family target; broad coverage is still incomplete. |
| [Language reference](language-reference.md), [core/compilation](core-and-compilation.md) | Grammar, intended semantics, Lean boundaries and deferred proof scope. |
| [Next core semantics](next-core-semantics.md), [folds/linking](folds-and-linking.md) | Implemented dimensional boundary plus retained proposals; finite folds and pure first-order modules. |
| [Module interface](module-interface-v1.md), [policy modules](policy-modules.md) | Generic `spl-module/1` registration and exact transitive dependency closure. |
| [Data/run contract](data-and-run-contract.md), [requirements/validation](requirements-and-validation.md) | State, evidence, provenance, validation and required checks. |
| [Readable language](readable-language.md), [implementation answers](implementation-answers.md) | Authoring boundary and accepted readable direction. |
| [Extensibility experiment](extensibility-experiment.md), [DYN-02 answer](dyn02-design-answer.md) | What the calendar experiment established and why no stronger necessary-core candidate is selected. |
| [Quest fixture](quest-two-flow-fixture.md), [follow-ups](dyn02-research-followups.md), [Quest guide](../../cases/quest/README.md) | Selected synthetic half-even requirement, answered questions, source/policy and actual execution. |
| [RR-03 integration](rr03-response-integration.md), [vendor evidence](vendor-feature-evidence.md) | Sourced benchmarks versus advertised features; unmeasured workload targets. |
| [Iteration log](iteration-log.md) | Dated implementation/verification history. |
| [Earlier compiler handoff](compiler-handoff.md) | Initial bounded-case policies and research provenance; its initial-task instructions are historical. |

Treat specifications as evolving documents. Later explicit user decisions and
dated execution updates govern over older future-tense proposals. A design
statement, a source-level arithmetic fit and a canonical end-to-end witness are
different evidence levels. Record ambiguities and update the appropriate docs
alongside implementation rather than quietly choosing a universal policy.

## Git and publication state

Repository: `https://github.com/TheHaltingSolution/dynamic-domain-lang`.

| Commit | Meaning |
| --- | --- |
| `2c99168ce1bad46009980f42f8eb5e2482ac74ee` | Initial large compiler implementation, pushed on `feature/spl-compiler-implementation`. |
| `018dde1434ce29708160d43268960f851de7fc64` | Merged PR #1; local `main` and last-fetched `origin/main` pointed here at handoff. |
| `38f00a2ec55c6f54adfb515cdcbf51d284e5fcd7` | Local typed quantities milestone, verified kernel profile `0.4.3-dev`. |
| `18a16811b4426a0500860ab76785c85547421514` | Local dated Quest half-even method, canonical fixture, tests and reconciled design docs. |

Current feature branch: **`feature/spl-typed-quantities`**. It contains both
follow-up milestones. Those two implementation commits have not been pushed;
there is no new PR for them. `main` was not changed by that work. Verify current
remote state before future publishing rather than treating this snapshot as live.
PR #1: <https://github.com/TheHaltingSolution/dynamic-domain-lang/pull/1>.

The user explicitly selected repository author `TheHaltingSolution`, email
`61482929+TheHaltingSolution@users.noreply.github.com`. This is repo-local Git
configuration. The connected GitHub app identity was `ssampath-rms` with read-only
access, so it could not push/create the owner's PR. Git Credential Manager was
authorized as `TheHaltingSolution` through a user-completed device flow; use that
existing login if available. `gh` was not installed. We used Git for push and
owner-authenticated REST for PR/reviewer writes. Never print credential material
or expose `git credential fill` output. A new session may need fresh auth; do not
assume cached credentials or tool availability.

## Compiler and execution architecture

| Area | Main files |
| --- | --- |
| Native surface/controlled prose | `SPL/Syntax.lean`, `Parser.lean`, `Readable.lean` |
| Static types and elaboration | `SPL/Check.lean`, `Elaborate.lean`, `IR.lean` |
| Independent defensive IR validation | `SPL/ValidateIR.lean` |
| Target runtime and bounded core | `SPL/Runtime.lean`, `Core.lean`, `Instant.lean`, `Calendar.lean`, `Dimensions.lean` |
| Native IR interpretation and audit | `SPL/Interpret.lean`, `Trace.lean` |
| Lean emission, bindings and CLI | `SPL/Emit.lean`, `Bindings.lean`, `Main.lean`; root `SPL.lean` |
| Scoped existing proofs | `SPL/Proofs.lean`; separate toy infrastructure in `Participation/` |
| Independent reference frontend/evaluator | `spl_compiler/parser.py`, `readable.py`, `checker.py`, `model.py`, `evaluator.py`, `emitter.py`, `dimensions.py`, `linker.py` |
| Strict canonical transport/runs | `spl_compiler/codecs.py`, `schema.py`, `run.py`, `modules.py`, `lean_tools.py`; `schemas/` |
| Independent neutral-fact controls | `oracles/`; these must not import compiler calculation helpers. |
| Executable financial sources | `cases/`; generated legacy Lean examples in `Demos/`. |

Public emission and interpretation validate IR; public constructors are not an
intrinsically typed syntax. Compare-mode canonical runs compare Python reference,
native IR execution and native-emitted Lean before finalization. Independent
financial oracles add another check from neutral facts. The Python mirror emitter
is exercised by selected differential tests too.

Native interpretation and the target share some casts, equality/ordering and
admitted runtime helpers. Agreement is useful evidence, not complete independence
or a trace/compiler correctness theorem. Preserve genuinely independent
neutral-fact financial controls.

Definitions can be forward/lazy; assertions run in lexical order. Unselected
branches must not evaluate demanded failures. Static binding/schema validation
still happens before calculation. Failure must not finalize provisional money
or consumable state. `spl_compiler.run` exposes profile-aware `run_package` and
`bind_package`: their second argument is a schedule path for legacy profiles,
but a registry root for `spl-module/1`, which they dispatch to the generic helpers.
For explicit generic calls, use `run_module_package`/`bind_module_package` from
`spl_compiler.modules`; that module has no `bind_package` alias.

## Completed compiler and financial capabilities

The current kernel includes readable expansion with source mapping, typed IR,
defensive validation, native IR audit DAGs, exact arithmetic, explicit rounding,
priority selection, records/options/tuples, finite maps/grouping/joins, ordered
folds and acyclic pure first-order imported functions. Generic descriptors bind
source, policy, interface, evidence, scope, state and output contracts. Canonical
Instant precision was repaired to preserve submicrosecond cutoff distinctions.

| Slice | Sources and controls |
| --- | --- |
| Skouras/SV and RQ-07 | [Readable SV](../../cases/sv/sv01-readable.spl), original SV and separate RQ-07 posting-date-cost profile. Earned 33,000, advance recovered 15,000, payable **18,000**, closing prepayment 0. RQ-07 has a real bounded canonical adapter/run. Missing incurred dates stay missing. |
| Lionsgate | [Readable LG](../../cases/lg/lg01-readable.spl), original source. Explicit hurdle/history attestations; payable **35**. Hurdle effective date must be **strictly before** period start. |
| Advances/reserves/payments | [Mechanisms](../../cases/mechanisms/README.md). Actual-funded advance: opening0 +15,000 against10,000 earnings -> recovered10,000/payable0/closing5,000. Reserve V1:12-7-5=0, V2:0+20=20. Revised90 less independently evidenced paid80 -> outstanding10. |
| Angel/MQP | [R1 guide](../../cases/r1/README.md). Guild allocation85 versus42.50 under changed denominator; agreement-date versus actual-date fee40/50. |
| Waterfalls | [Guide](../../cases/waterfall/README.md). Funds120: priority100/20 versus pro-rata60/60; serialized two-period carry also tested. |
| Authorized revision | [Guide](../../cases/revision/README.md). Bounded replacement-fact restatement100->90, actual paid80, outstanding10; uses original opening and scoped authority. Not general dependent-period replay. |
| Calendar months | `cases/extensibility`, `SPL/Calendar.lean`. Explicit clamp/reject policy, years0001..9999; January31+1month clamps to February28. Preserve E0 rejection and legitimate supplied-date method. |
| M1a royalties | [Guide](../../cases/m1/README.md). Reusable tiers/cumulative/cap/guarantee modules. Basis150 -> marginal20 versus whole-base30; opening80+70 -> current12/closing150; cap100 consumed70 permits30; separate nonrecoupable floor100; explicit tiers20 then cap15. |
| M1b quantities | [Guide](../../cases/quantities/README.md). 100 Download ×USD1.50/Download =150, separate50% participation =75. Actual successor adds0.5 to meter100 ->100.5 and earned0.375. |
| Quest | [Guide](../../cases/quest/README.md), [SPL](../../cases/quest/charge.spl), [readable policy](../../cases/quest/policy.md). Proposed synthetic dated half-even method; details below. |

These selected witnesses do not complete every C1 family or establish whole
historical-contract compliance. The conformance ledger keeps remaining variants
visible, including broader loss/gate/transfer/calendar/replay methods.

### Quantity and defensive validation details

`spl.units/1` admits exactly `Download` and `UsageMinute`. Source types are
`Quantity<U>` and `Rate<U,USD>`, supplied through existing generic syntax and
typed parameters. Exact tagged transport retains units through containers,
outputs, state and traces. Same-dimension arithmetic, scaling, matching
quantity×rate -> Money USD, typed empty sums and matching explicit quantization
execute. Scalar/tuple sorting supports the new dimensions; dimensional
Map/group/ordered-fold keys remain rejected. Money/Quantity and FX are unsupported.

Every relevant descriptor in the full import closure must declare capability
`spl.quantities/1`, codec `spl-quantity/1` and its used admitted units. Unused
schemas/exports are checked too. Dimensional domain/conservation bounds require
matching tags, including empty collections. Nested dimensional state uses the
complete normalized checked-type hash in slot/cell/scope unit and economic key;
see `dimensioned_state_unit` in `modules.py`. AST built-ins must be expanded
through the checker so nested `Period` hashes agree with checked types.

An audit reproduced forged unknown Quantity/unsupported-rate-currency types
hidden in empty lists or `none`. The fix validates every IR metadata and explicit
binder/parameter type; 15 negative native IR cases exercise validation,
interpretation and both emitters. Money/Ratio still share legacy numeric runtime
representation and depend on checked-IR assumptions. Existing scalar proofs do
not establish correctness of the tagged dimensional paths.

### Quest details that must survive the handoff

Policy: `DYN02-QUEST-TWOFLOW-NEAREST-EVEN@1`, proposed synthetic research
assumption. Exactly one USD obligation, one full principal payment and one
application; all original identities, dates, scope and evidence are retained.
The adapter validates ordinary Gregorian facts, but **SPL** looks up both
endpoint ordinals and subtracts them. No elapsed-day answer or solved charge
enters the financial calculation.

The method computes the mathematical ACT/365 target-return component and rounds
the **additional charge once with half-even**, using exact rational integer
powers/search and certified cent bounds. It does not round principal+charge
before subtracting principal. Key results:

- USD1,000 at20%, January1 to July2,2026 ->182days, additional **95.17**;
  separate minimum-cent-at-least-target detail **95.18**.
- USD0.01 at50% over365days ->exact0.005 ->additional **0.00**.
- USD0.03 at50% over365days ->exact0.015 ->additional **0.02**.
- Due June30 ordinal180, paid July2 ordinal182 ->2days ->additional **1.00**.

For charge cent index `m`, compare target `(1+r)^d` with
`((P+bound)/P)^365`. Even `m` includes both half-cent endpoints; odd `m` is strict
at both. `m=0` uses the nonnegative-charge domain boundary. The SPL method asserts
its minimum/predecessor and rounding-cell certificates before output.

`cases/quest/power.spl` is an ordinary imported SPL library, not a new `pow`
builtin. `calendar_date` is a mechanical source-field rename: `date` is reserved
by the existing grammar. The profile pins five calendar facts: January1, June30,
July2 of2026 and January1/2 of2027, ordinals0/180/182/365/366. New dates need a
deliberate calendar/profile revision. Numeric domain: principal≥USD0.01,
nonnegative rate, integral days0..365, and `ceil(P*r/.01)<2^24`; nine power slots
and24 search slots are engineering budgets, not agreement terms or a universal
capacity proof.

The independent oracle was written before reading the new SPL. Decimal
logarithms/exponentials nominate a cent cell; exact Fraction powers certify it,
including exact/near ties. It shares no compiler search implementation.

Actual principal paid remains USD1,000 in the baseline. Additional-payment status
is `no_event_supplied`; monthly status `not_computed`; combined status
`unresolved_not_computed`. There are no financial state slots or payment-execution
claims. Partial flows, monthly/combined liability, Excel operational equivalence,
professional approval and owner acceptance of this adjacent patent-rights domain
remain open. The user-supplied replies were sufficient for this bounded fixture:
**do not ask the same four acceptance questions again.**

## Verification truth and saved evidence

| Checkpoint | What passed | What must not be inferred |
| --- | --- | --- |
| `38f00a2`, kernel `0.4.3-dev` | One combined run of **352 Python tests**,1638.702s;86-job build,both smokes,16 native suites;35 review paths (24 prior +7M1a +4quantity). | Not a proof or full C1 coverage. An earlier calendar helper-test fixture error was corrected; its interrupted run remains archived. |
| `18a1681`, Quest supplemental work | One combined **34 new test-method** run,402.120s:20oracle+9canonical+5direct; nine Quest comparison scenarios; nine compatibility cases;86-job build,both smokes. | The old352 suite and16-suite cohort were not rerun as a combined current-tree run for Quest. |
| Current discovery | **386 tests discovered** when preparing this handoff. | Do not report a single passing386-test run. Discovery is not execution. |

The Quest tests include ten direct valid scenarios,26 invalid-input mutations,
and two deliberate incorrect-rounding source mutations. The demo separately
checks all certificate fields in nine scenarios through compare-mode canonical
runs. Compatibility checks retain18,000/35 and advance/reserve/correction
controls5,000/20/10. All45 kernel/schema source pins, compiler/runtime/module
identities, original half-away probe and `implementation-baseline.json` remained
unchanged during Quest work.

Current identities, matching the `0.4.3-dev` kernel record:

```text
compiler/reference 1ec2ca5ec6df9ae844348d9fe5961c58ecb3dab614b0e01cfdea741ace93a20a
runtime            673bb0fe936c48a60c1cf5a1a265fb1d1f9f3cd432f380ee9b3011b7729dace9
module             f65e6bec55269c3baf49ea856710f4e3202bc7c1cc2e6f229a742ab695f79a01
```

Below, artifact paths start under
`C:/Projects/Film_TV_participation_dynamic_DSL/artifacts/spl/`.

| Artifact | Purpose |
| --- | --- |
| `quantity-0.4.3/review-index.json` | Kernel milestone, actual logs, packages and review hashes. |
| `quantity-0.4.3/checks/verification.json` | Successful352-test run +16 native suites/build/smokes. |
| `quantity-0.4.3/checks-initial-calendar-fixture-failure/` | Preserved interrupted initial attempt; original recorded paths may precede its relocation. |
| `quest-two-flow/review-index.json` | Latest completed method checkpoint at18a1681 and source freeze. |
| `quest-two-flow/checks/final-verification.json` | Final34-test/9Quest/9compatibility summary and unchanged-kernel checks. |
| `quest-two-flow/checks/quest-verification.json`, `quest-tests.log` | Exact supplemental command, results and source pins. |
| `quest-two-flow/review/summary.json` | Nine full comparison cases; subfolders hold original neutral facts, oracle controls, canonical packages, emitted Lean, results and traces. |
| `quest-two-flow/compatibility/` | Six original/readable runs and three direct accounting mechanisms. |
| `dyn02-design-probe/` | Original half-away supplied-day program/bindings/results/certificate checker; preserve unchanged. |
| `dyn02-compiler-review/review.json` | Root replay of that earlier probe:four positives/three negatives,both backends. |
| `freezes/quantity-0.4.3/` | Immutable340-file source archive;tree SHA256 `e600f02b344fa30ef647bc314c6b6bfc6fe8f0f3387ec92cd3248c19bdfe1142`. |
| `freezes/quest-two-flow-method/` | Immutable359-file archive at18a1681;tree SHA256 `786956ee22e6dd6a589bd074f76997b014f8e4ca38af03637db0f94fd32674f6`. |
| `freezes/m1-ordinary-0.4.2/`, `freezes/r1-calendar-e1/` | Earlier method/kernel source freezes. |
| `freezes/r1-core-e0-r2/` | Corrected complete E0 archive. The original `r1-core-e0` omitted schemas and remains preserved as a failed packaging history. |

The primary [implementation baseline](implementation-baseline.json) is still
`0.4.3-dev`; Quest did not silently overwrite it. Older records live in
[`baselines/`](baselines/). Documentation added after a freeze naturally differs
from that archive. Verify its recorded checkpoint, not whether all current
documentation still matches every historical pin. Old freezes and review outputs
must remain immutable; write new artifacts to a fresh directory.

## Proposed next work

The last recommendation was systematic conformance validation, then measured
workloads, while the necessary-extension research remains separate. The user
requested a handoff before implementation began. There is no existing general
feature-matrix/generator/coverage campaign to resume halfway through.

### Phase one Map requirements to executable witnesses

Build a machine-readable feature/test matrix, anchored in the ledger's actual
requirement IDs and implemented variants. Separate parser/checker admission,
reference evaluation, native IR, emitted Lean, canonical validation, state and
audit evidence. Start with K1-K3, selected M1a methods, quantities, readable SV/LG
and Quest; mark unsupported variants as gaps, not passes or silently skipped tests.
Map existing tests before adding duplicates. A filename or an expression's
arithmetic expressibility is not evidence of end-to-end integration.

Exit: a readable matrix/report and a repeatable command linking every claimed
supported row to its input, expected property/oracle and exercised backend.

### Phase two Generate controlled independent cases

Use reproducible seeds and bounded domains. Generate neutral facts and selected
SPL variations with independent expectations. Compare reference, native IR and
emitted execution; use the Python mirror emitter where that adds an independent
path. Make failures reproducible with the exact seed, source/binding bytes,
versions, diagnostics and smallest practical failing case retained externally.

Prioritize financial boundaries and interactions: zero/empty inputs, threshold
equality, half-cent ties, fraction arithmetic, strict cutoff equality, tuple/map
keys, duplicate identities, wrong scope/currency/unit, branch laziness, atomic
failure, serialized state carry, tier/cap order, allocation conservation and
actual-payment separation. Use metamorphic relations only where policy permits:
physical permutation, split/merge facts, identifier renaming and equivalent exact
numeric notation. Rounding and event ordering can legitimately invalidate a
naive permutation or split invariant.

Exit: bounded, deterministic generated suites with independent controls and
explicit feature-combination coverage. Do not promise every combination.

### Phase three Measure coverage and test the tests

Native traces already record branches, selections, errors and `not_evaluated`
paths; inspect `SPL/Interpret.lean` and trace tests. Use source-hash-qualified node
identities and spans when deriving a source/IR decision-coverage report.
**That is not emitted-Lean branch or compiler line coverage.** Instrument and
validate target execution separately before making those claims.

Extend meaningful mutation checks beyond Quest's two hand-selected rounding
mutations:wrong fee/base/order,boundary comparisons,unit/quote orientation,
duplicate counting and state transition mistakes. Distinguish killed,survived,
invalid/equivalent and unexecuted mutations. A mutation outside the declared
input/policy domain is not automatically a useful test failure.

Exit: honest coverage/mutation reports that expose gaps rather than producing
an impressive unsupported percentage. Keep core changes minimal; a post-run
trace-analysis harness can initially leave kernel identities unchanged.

### Phase four Measure realistic workloads

Use [RR-03](rr03-response-integration.md) to select representative mixes, skew,
allocation fan-out and ordered history lengths. Measure direct calculation and
native audit separately, with time, output bytes, memory, resource failures and
independent financial controls. Start with bounded cohorts and increase only
after prior measurements justify it. Define useful single-process capacity
before distributed execution.

Existing tools: `scripts/spl_benchmark.py`, `measure_trace_transport.py`,
`spl_trace_transport.py`. Trace transport is experimental post-generation
archival interning, not a native memory fix. A100-receipt trace shrank from
7,604,969 to2,853,622 bytes; a smaller case grew. Earlier E0 warm1000-receipt
non-audit timings were about0.0425s median/0.0445s empiricalp95, while full native
audit wrote459,333,400 bytes in10.487664s for23,180 nodes. A separate comparable
memory observation was about1.56GB, not a measured p95. Keep these historical
cohort/version/scope qualifiers. The100,000-row guard is not a capacity result;
million-row and distributed processing remain unmeasured.

## Required extension and FX gate

The user wants a withheld capability genuinely needed by a contract and not
faithfully representable using existing SPL. The [selection gate](extensibility-experiment.md)
is still active before native EUR/FX work. **No capability is selected or
reserved yet.** Do not lift the gate merely because Quest engineering finished.

FX arithmetic/quote selection, complete-period rational compounding and the
bounded Quest rounded charge have existing-language routes. Currency-tagged
records can be legitimate. A new static currency guarantee is useful, but it
must be classified as type/interface work rather than proof that old arithmetic
could not represent the contract. Same-currency Money/Money already yields
Ratio; future EUR generalization could allow normalization/reconstruction.
Do not remove a cancellation rule or reject valid alternative encodings to
manufacture a gap.

The earlier calendar extension demonstrated practical API/compiler evolution
with preserved compatibility. Its acknowledged supplied-date alternative means
it does not establish the user's stronger financial-necessity claim. A slower
method or missing `XIRR`/`pow` name is insufficient. Mathematical impossibility
of every encoding requires more than an unsuccessful prototype.

Research should identify a precise required residual and supply original facts,
outputs and policies; design should attempt faithful reusable encodings. Accept
successful methods as legitimate results. Keep openly researched development
material separate from independent held-out evaluation.

Remaining C1 work also includes broader units/conversions, deduction/threshold/
tier variants, signed returns/losses, reserve stages/caps, cross-contract movement,
dynamic gates, dependent-period replay, fiscal/business calendars, supplied
withholding/payment thresholds and further integrations. Consult the ledger;
do not equate arithmetic support with complete business-family support.

## Commands and execution workflow

From a fresh PowerShell terminal:

```powershell
Set-Location 'C:\TheHaltingSolution\dynamic-domain-lang'
$env:ELAN_HOME = 'C:\Projects\Film_TV_participation_dynamic_DSL\environment\elan'
$env:PATH = "${env:ELAN_HOME}\bin;$env:PATH"
lean --version
lake build
lake exe smoke
lake exe spl_smoke
```

Pinned toolchain: `leanprover/lean4:v4.35.0`. Warnings are errors. Official
references and setup reproduction are in [lean-resources.md](../lean-resources.md)
and the root [README](../../README.md).

Focused Quest checks and actual demo, with a fresh artifact destination:

```powershell
Remove-Item Env:QUEST_REFERENCE_ONLY -ErrorAction SilentlyContinue
Remove-Item Env:SPL_QUANTITIES_REFERENCE_ONLY -ErrorAction SilentlyContinue
Remove-Item Env:SPL_REVISION_REFERENCE_ONLY -ErrorAction SilentlyContinue
Remove-Item Env:SPL_M1_BACKEND -ErrorAction SilentlyContinue
Remove-Item Env:SPL_WATERFALL_BACKEND -ErrorAction SilentlyContinue
& 'C:/Projects/Film_TV_participation_dynamic_DSL/environment/python/python.exe' -m unittest Tests.test_quest_oracles Tests.test_quest_modules Tests.test_quest_native -v
& 'C:/Projects/Film_TV_participation_dynamic_DSL/environment/python/python.exe' scripts/quest_demo.py --reuse-registration --output C:/Projects/Film_TV_participation_dynamic_DSL/artifacts/spl/resume-review/quest
```

The three `*_REFERENCE_ONLY` flags were authoring shortcuts; the M1/waterfall
backend variables can override their default `compare` execution. These settings
can omit native/emitted paths without appearing as skipped unittest methods.
Clear all five before a full `scripts/spl_check.py` run or a claim of the complete
default comparison scope. Record actual backend choices in future harness reports.
The demo defaults to compare mode,
calculates real scenario outputs and certificates, and writes statements, detail,
bindings, policy review, traces and emitted Lean. It does not just compile.

Other useful commands, each with a new output location:

```powershell
python scripts/m1_demo.py --reuse-registration --output C:/Projects/Film_TV_participation_dynamic_DSL/artifacts/spl/resume-review/m1
python scripts/quantity_demo.py --output C:/Projects/Film_TV_participation_dynamic_DSL/artifacts/spl/resume-review/quantities
python scripts/spl_demo.py --skip-baseline --output C:/Projects/Film_TV_participation_dynamic_DSL/artifacts/spl/resume-review/legacy
python scripts/r1_demo.py --derived-calendar --output C:/Projects/Film_TV_participation_dynamic_DSL/artifacts/spl/resume-review/r1
```

Here `python` means the pinned executable above if it is not already on PATH.
Some builders deliberately regenerate registrations. Run them before freezing
test inputs, not concurrently with canonical calculations.

Full Python suite when justified by a core change or integration milestone:

```powershell
& 'C:/Projects/Film_TV_participation_dynamic_DSL/environment/python/python.exe' scripts/spl_check.py
```

`scripts/spl_check.py` inserts the current checkout into `sys.path`. The embedded
Python's fixed `._pth` can otherwise import the original checkout while testing
an extracted archive or worktree. Use this bootstrap for isolated reproduction.
The previous full352 run took about27minutes; Quest's extra34 took about7minutes.
Record actual counts/exit codes; do not infer a current combined pass by addition.

The16 native suite commands are in
[`.github/workflows/lean.yml`](../../.github/workflows/lean.yml), ending with
`lake env lean --run Tests/SPLTraceScaling.lean --quota`. Build/smokes plus relevant
new checks are required for code changes. Broaden/repeat checks only when new
changes, failures or unresolved concerns justify it.

## Fingerprints and Windows lessons

- Compiler/runtime/module identities hash source/schema dependencies. Changing
  `SPL/*.lean`, `spl_compiler/*.py` or schemas during a run can produce legitimate
  dependency-change or stale-manifest errors. Freeze those files, build, deliberately
  register/bind fresh development packages, then run. Never silently repin issued
  historical results during execution.
- Generic packages use `module_identities()`; legacy packages use the wrapper
  `identities()`. Preserve exact transitive source/policy/descriptor pins. The
  Quest and quantities disk packages and seven M1a templates are deliberately
  unbound; bind a fresh invocation before execution. Follow the explicit module
  helpers or the profile-aware `run.py` dispatcher with the correct second argument.
- Existing snapshots need deliberate refresh after a real kernel change.
  `scripts/r1_demo.py --legacy --derived-calendar --refresh-snapshots` covers its
  registered/legacy set; dedicated mechanism, M1 and revision builders cover
  their own files. Read the builders before refreshing. Preserve old baselines
  and freeze records; do not update hashes just to silence a mismatch.
- `.gitattributes` uses LF. Windows writes once introduced CRLF into new Lean
  files; Git would normalize on commit and invalidate raw-byte pins. Ensure LF
  **before** registration, build identities and final runs. Compare filtered
  `git hash-object --path <file> <file>` with `--no-filters` if necessary.
- Explicit `-text` exceptions preserve raw RQ-07 source files, archived baseline
  JSON and `docs/spl/policies/manifest.json`. Do not normalize those bytes or
  trim old pinned files casually. A broad whitespace check can be noisy for
  intentional historical CRLF/blank EOF; understand the attributes.
- Windows `LongPathsEnabled` was0. A long isolated E1 replay hit descriptor I/O
  failures at281characters; a shorter extraction path passed at about235.
  Use a short workspace path before interpreting those failures as semantic bugs.
- Native executables can be locked during execution; do not rebuild them while
  running comparisons. Direct `.olean` compilation mixed with stale Lake C output
  once caused linker symbol failures. A disposable `lake clean` plus fresh build
  restored coherence. Do not delete source, fixtures or frozen artifacts.
- Smart App Control was turned off by the user during earlier toolchain startup
  troubleshooting. Lake now works without elevated VS Code. Diagnose actual
  startup errors rather than assuming filesystem permissions or requesting admin.
- PowerShell `*>` can wrap unittest stderr in `NativeCommandError` text despite
  success. Prefer Python `subprocess.run` with stdout/stderr captured to a raw log,
  and record the actual exit code. End shell wrappers with the child exit status.
- Financial codecs reject binary floats, numeric JSON tokens in strict contexts,
  malformed rationals and unknown fields. Use decimal strings or reduced rational
  objects. Telemetry seconds may be serialized as strings when embedded in strict
  records. Quest transport uses `codecs.exact`; the older R1 `_q` helper accepted
  raw integers and rejected rational objects, which was wrong for this new fixture.
- Extreme rational precision can create enormous365th-power certificates/traces
  and hit current Python integer serialization/resource limits. Oracle-only
  `1e-110` near-tie tests are not a demonstrated native/canonical capacity result.
  Do not quietly change global numeric limits or claim unbounded useful capacity.
- Audit serialization repeats collection operands in many nodes. Preserve logical
  lineage while optimizing. `spl_trace_transport.py` packs/unpacks after generation;
  it does not remove native materialization cost or replace the default trace.
- Keep exact source bytes used by a demo. M1 has a regression for a fixture edited
  mid-run. A current file hash after loading is not necessarily the consumed bytes.
- Use literal argument arrays, temporary body files and careful PowerShell quoting
  for multiline text. JSON serialization is not shell escaping. Avoid printing
  credentials and avoid repurposing system variables such as `$HOME`.

## First actions for the next session

Confirm branch/status and read the current plan, then design a bounded validation
milestone before modifying the compiler. Reuse the checked-in independent oracles
and source examples. Establish explicit ownership and a stable test interval.
The first useful deliverable is a machine-readable feature/test matrix and a
single reproducible validation command with source/seed/backend/coverage evidence.
No pending research answer blocks that generic work.

Do not reopen the already resolved Quest synthetic choices, overwrite the
0.4.3 record, label386 discovery as a full pass, extend FX past the gate, or claim
the whole compiler is proved. Keep user-visible updates concise and show exact
remaining questions only when they affect the selected next behavior.

A suitable starting prompt for the new session is:

> Continue SPL compiler work in `C:\TheHaltingSolution\dynamic-domain-lang`.
> Read `AGENTS.md` and `docs/spl/session-handoff.md` first. The implementation
> checkpoint is `18a1681` on `feature/spl-typed-quantities`; do not reset to main.
> Begin the proposed feature/test matrix and generated conformance-validation
> harness, using sub-agents with separate ownership. Preserve the verified kernel,
> scoped financial policies, immutable evidence and the pre-FX extension gate.
> Update the plans and ledger with actual execution evidence and explicit gaps.
