# SPL handoff: agreed finish line and saved integration

25 November 2026. Prepared at the owner's request **instead of starting more
implementation**. The project goal is paused. This is a continuation guide, not
a completed release or a request to restart every item in the old backlog.

## 1. Read this first: the owner's final scope

The owner wants to finish a bounded research implementation, demonstrate and
validate contracts, understand medium-size execution, and document limitations.
They explicitly do not need a large-scale production batch platform now.

The following decisions supersede the broader automatic work sequence in
[completion-plan.md](completion-plan.md), [completion-backlog.json](completion-backlog.json)
and older handoffs. Retain those inventories as history and useful detail;
do not treat every old open item as a release requirement.

| Finish now, after work resumes | Intended result |
| --- | --- |
| Integration and release | Integrate the already qualified candidates, verify the assembled version, and provide a reproducible, honestly scoped release checkpoint. |
| Relationship safeguards | Prevent duplicate relationships, missing references/recipients, and unintended join cardinalities from multiplying or losing money in supported workflows. |
| Reports and audit completeness | Check that supported calculations expose the required results, policy, contributions, state and lineage, with useful failure diagnostics and no false completion authority. |
| Measure the complete current workflow | Representative 100- and 1,000-record cases, repeated wall timings and memory, including four consecutive periods with genuine saved-state carry. |
| Publish a supported capacity envelope | State measured workloads, resource guards, observed failures and unmeasured limits in a form usable in the research paper. |

**Audit optimization is conditional, not a standing task.** The owner considers
about 41 seconds acceptable even if audit is a large fraction of that time.
Measure absolute cost first. Do not optimize solely to reduce a percentage, and
do not turn an acceptable result into another open-ended optimization campaign.

The following are **deferred**:

- The broader strategy for testing feature combinations: discuss carefully with
  the owner later. Routine checks needed to safely finish current changes still
  apply; this is not permission to ship unverified changes.
- General data interfaces, including the previously contemplated broad
  alias/enum/external-data model work.
- Additional sourced contract examples and the associated expanded testing or
  professional-review program, until the testing discussion.
- Native mixed currency/FX and the self-modifying compiler tool/skill.
- Convenience syntax. The already qualified readable multi-settlement change is
  saved for integration; do not start further syntax expansion.
- Large-scale batch execution, distributed/parallel throughput infrastructure,
  and large real-world data ingestion merely to claim scale.

The paper should distinguish demonstrated medium-size capacity from a plausible
future extension. Do not claim that large-scale operation is measured, supported,
or easy solely because the architecture might allow it.

## 2. Mission and intent

SPL is Screen Participation Language: a controlled language for film/TV royalty
and participation calculations. The project connects readable contract methods
to an explicit typed core/IR and pure Lean 4 calculations, with an independent
Python implementation/frontend/emitter used for comparison and validation.
Important properties include exact rational quantities, explicit rounding and
units, versioned policies, original input custody, deterministic calculations,
saved state and inspectable financial lineage.

Calculation completion is distinct from statement issuance and bank movement.
Do not invent either to make a fixture work. Source provenance, faithful encoding,
arithmetic agreement, original/prepared-data correspondence, publication
integrity and professional accounting approval are different claims.

The long-term research idea is a tool that takes a real contract, attempts a
faithful SPL encoding, identifies a missing capability if there is one, modifies
the compiler, and verifies old and new contracts. That tool is a later phase.
The owner reserves mixed-currency contracts for that demonstration rather than
implementing native FX in advance. Existing record-backed encodings remain
valid. RR04 and LD03 did not identify a qualified financial calculation that
existing SPL could not express; do not manufacture such a claim.

Read [ld03-owner-decision.md](ld03-owner-decision.md),
[rr04-ld03-integration.md](rr04-ld03-integration.md), and
[self-modifying-compiler-demo-plan.md](self-modifying-compiler-demo-plan.md)
for that history. Today's narrower finish line keeps this later phase deferred.

## 3. Reading order and important locations

Start with these, in order:

1. [AGENTS.md](../../AGENTS.md), then [Lean resources](../lean-resources.md).
2. This handoff, especially the scope, Git state, evidence limits and next steps.
3. [active-work.md](active-work.md), an extensive dated evidence index. Its older
   statements that jobs are active or candidates absent are superseded below.
4. [The previous session handoff](session-handoff.md), then the earlier
   [compiler handoff](compiler-handoff.md). These preserve mission, prior user
   feedback, kernel history, research and implementation lessons. Historical
   absence/gate statements are not current instructions.
5. [Completion checkpoint](completion-checkpoint.md),
   [completion plan](completion-plan.md), and
   [backlog](completion-backlog.json), filtered through section 1 above.
6. [C1 coverage](c1-coverage.md), [atomic variants](c1-atomic-variants.json),
   [conformance ledger](conformance-ledger.md), and
   [validation guide](conformance-validation.md).

Useful authoring and implementation references:

- [Language reference](language-reference.md),
  [readable language](readable-language.md),
  [native method source guide](native-method-source-guide.md),
  [core and compilation](core-and-compilation.md), and
  [implementation](implementation.md).
- [Policy modules](policy-modules.md),
  [module interface](module-interface-v1.md),
  [data and run contract](data-and-run-contract.md), and
  [artifact publication design](artifact-publication-design.md).
- [LD02 scope](release-scope-ld02.md),
  [RR03 integration](rr03-response-integration.md),
  [research-agent note](for-royalties-research-agent.md), and
  [language-design-agent note](for-language-design-agent.md).
- Read the newer versions in `C:/spl-next` when investigating an integrated
  candidate; main documentation/code does not yet contain all those changes.

| Location | Purpose |
| --- | --- |
| `C:/TheHaltingSolution/dynamic-domain-lang` | Main shared repository; preserve user and agent files. |
| `C:/spl-next` | Clean assembled integration checkout; next verification target. |
| `C:/Projects/Film_TV_participation_dynamic_DSL` | External resources, environment, large validation artifacts and references. |
| External `artifacts/spl/` | Dated evidence cohorts referenced throughout this handoff. |
| External `ResearchAgent/documents/` | Contract research and design responses. |
| External `reference/lean4/` | Official pinned Lean manual, programming guide and proof guide, indexed by `docs/lean-resources.md`. |
| External `environment/python/python.exe` | Embedded Python 3.12.8; see the import-path warning below. |
| External `environment/elan/toolchains/leanprover--lean4---v4.35.0/bin/` | Pinned Lean/Lake binaries. |

The exact research files are `SPL_RR04_Completion_Decisions.md` and
`SPL_LD03_Completion_Review.md`; their hashes and adopted decisions are recorded
in [rr04-ld03-integration.md](rr04-ld03-integration.md). Consult these existing
resources before asking reviewers to repeat answered questions. The language
design and royalties research reviewers are conceptual/external roles, not
guaranteed live collaboration agents in a new session.

## 4. Current Git and pause state

Rechecked during this handoff:

- Main branch: `feature/spl-typed-quantities`, HEAD **`27d8222`**, “Record
  completed correction composite and canonical reserve namespaces.” A
  documentation-only handoff commit will follow this code checkpoint.
- Main has **23 untracked prototype files**, under `cases/entitlement-burdens/`,
  `cases/ordered-gates/`, `cases/dependent-replay/`, and their three
  `Tests/test_*_modules.py` files. They are older agent drafts, not the qualified
  versions. Do not `git add .`, delete them, or overwrite them silently.
  Archive their exact bytes and inspect for later user edits before promotion.
- Main's compiler/module/runtime implementation remains the older
  **a0e5/c287/a7e** context. Candidate integration has not been promoted.
- Integration branch: `feature/spl-completion-integration` at **`C:/spl-next`**,
  clean, HEAD **`d6d04f8`**, “Add explicit ratio precision and USD rounding
  profile.” All candidate changes listed below are already cherry-picked here.
- Goal status was read back as **paused**. No implementation or performance
  work was resumed for this handoff. The current collaboration inventory lists
  only root; old environment agent names do not imply running agents.
- The c80 regression process ended successfully; do not wait on its historical
  PID54884/session52405. Other qualified cohort processes described below ended
  before the pause. Reinspect processes rather than trusting dated “active” text.
- No push, PR, deployment or external release has been made.

Computed again from the integration checkout using its own Python imports:

```text
compiler 8793a51eba96c6fd35c0b71f9194ee010b0180b5f5fd016e022d6efe0d5d7000
module   d73093a1cd8b9b5ab0976a9a7b6d423bf2e6b384b2810df1926d68c5cb47a77b
runtime  77a18c1992ab39bd97977e8b94c9ef0741f557c8c6680d243bed8dcae2b3a6f5
```

These are API identities, not individual file hashes. Preserve historical
identities in old evidence; never update a receipt to make it look current.

The historical baseline files `docs/spl/implementation-baseline.json` and
`docs/spl/baselines/implementation-0.4.3-dev.json` remain byte-identical, SHA-256
`61716b4d0540cd25af963efac3032a52065b19a94f1cd7ba02a2a6244365ed59`.
They are historical kernel evidence, not the final release result.

## 5. What has actually been verified

The strongest wide regression is **1,301/1,301 passing methods** at exact commit
`c80ac34bd7d529742a6223a06f56edd3118785b4` in `C:/spl-c1-integration`.
The evidence directory is external
`artifacts/spl/integrated-compiler-c80ac34-20261123-a/`.
`verification.json` reports zero failures, errors, skips, expected failures,
unexpected successes, source drift or compiled drift. Tests took
6,370.832129 seconds; total verification took 6,401.503619 seconds. Fresh default
and indexed builds and both smoke programs passed. Its source archive and
before/after source/build pins are retained there.

That run covers the combined compact/core optimizations, **not** all subsequently
assembled case and language additions. Its identities are:

```text
compiler 441f0e7c8cbae3da4538449abfbcf2711991d123f343507098323ec6583445fb
module   04db83fff9a18ef5157094ca5d15515006c9952118c3a2828d7f8af3b3ff95a2
runtime  77a18c1992ab39bd97977e8b94c9ef0741f557c8c6680d243bed8dcae2b3a6f5
```

The newer `C:/spl-next` snapshot had **1,547 methods discovered without import
errors** before the pause. Discovery is not a passing regression. A fresh build
at earlier integration commit `2ae49a9` passed 103 jobs; do not describe that as
a final build of `d6d04f8`. Final assembled builds, relevant interactions and a
full frozen regression remain release work.

Earlier `0b91bc7` passed 1,158 methods in 7,726.735609 seconds. Earlier 887-test
and other counts in old documents retain their own dated scopes. Do not add
overlapping cohort counts or use test counts as a language-completeness score.
The C1 inventory's 78 semantic rows (75 original required, two supporting and
one unselected) and separate engineering axes also describe an older finite
scope, not a denominator for all possible contracts.

### Qualified candidates already assembled in `C:/spl-next`

All cohort names below are relative to the external `artifacts/spl/` directory.
Consult each cohort's verification/final-audit, source pins, process reports and
archive audit for exact claims. Focused or composite qualification does not
substitute for the final assembled regression.

| Candidate and original checkout | Qualified source commits | Evidence and result |
| --- | --- | --- |
| Compact publication, old-v1 carry, narrow imports, native and Python deferred helpers; `C:/spl-c1-integration` | `323440a`, `76a6334`, `42948b9`, `7130bd2`, `cb61b0a`, `c80ac34` | The 1,301-pass regression above; copied into integration as `b98cb1b` through `8d21a6d`. |
| C10 entitlement burdens; `C:/spl-c10-c80` | `0988d0d`, `405a7d1`, `a0e68cc`, `7b5452a` | `c10-compact-integrated-20261124-a`: 46 pass, 1,423.861s tests / 1,642.568s total; actual Q1/Q2/Q3, preview and actual old-v1Q2 to v2Q3 carry. |
| C11 ordered work gates; `C:/spl-gates-f` | `dbf0d5f` | `ordered-gates-followup-20261124-a`: 23 focused pass, 566.324s; 12 lifecycle controls, actual three-period carry, seven extracted publications reload. |
| C13 dependent corrections; `C:/spl-c13f` | `ea71d0b`, `c230204`, `f263e04` | `dependent-replay-native-final-20261124-a`: 24 pass, 490.955s tests / 498.505s total; final lifecycle/boundary controls plus independent full-original replay reviews. |
| C09 reserve stages/caps/releases; `C:/spl-c09s` | `fc10100`, `575a7e6`, `b2358bf`, `70010af`, `752fde3`, `01ac033` | `reserve-stage-namespaces-20261124-b`: 45 isolated reference pass, 22 valid native publications, nine pre-source blocks, 31 bounded reloads, 263 process reports. |
| Report/intended-issue date metadata; `C:/spl-dates` | `4b1b638`, `b14e2bb` | `run-dates-frozen-20261124-a`: 51 pass / 140 subtests / 98 publications; `run-dates-digest-followup-20261124-a`: two pass / 12 publications, documentation/assertion correction only. |
| Conservative dependency components; `C:/spl-components-c80` | `18ea951`, `1a76a38` | `component-frozen-20261124-a`: 44 pass, 152.098s; actual C10 carry and standalone/batch financial/state equality. Single worker, explicit registered-profile assumptions. |
| Retained C09 native harness sources; `C:/spl-c09-retained` | `d587e3c` | `c09-harness-source-preservation-20261124-a`: ten scripts preserved verbatim, hash/ZIP/staged/Git agreement; no execution claim. |
| Readable multiple settlements; `C:/spl-ms` | `6475454`, `aa428a7` | `readable-multi-checks-20261124-a`: 23 Python checks plus compiled native unit, four positive programs across backends and eight negative controls; independent review and zero-heading compatibility below. |
| Numeric precision and USD rounding; `C:/spl-np80` | `d0cb976` | `numeric-precision-full-20261124-a`: 57 pass, 2,229.239s tests / 2,234.392s total; 209 qualified publications publicly reloaded, 128 empty blocked cases, 26 intentionally incomplete markers rejected. |

Integration already includes main's five independent C09 oracle files
(`bdcac46`), so skip the duplicate prerequisite `3355168`. The assembled
integration log gives the translated cherry-pick hashes; do not cherry-pick
these candidates again. Key integration boundaries are `2ae49a9` after components,
`f2c4fb6` after retained sources, `c7436b4` after readable, and `d6d04f8` after
numeric precision.

### Financial and verification details worth preserving

- **C10:** claimant entitlement100 stays100 while the separate agreement's
  amount200 less authorized charges30/15/0 becomes170/185/200. Paid basis60
  gives18 rather than accrued basis100 giving30. This is not a conserved
  transfer or bank movement. The wrapper now checks full original/prepared
  correspondence; generic prepared-input APIs are not original-custody proofs.
  Root review: `c10-root-original-review-20261124-a`.
- **C11:** independent original recomputation gives period results0/6/2,
  cumulative8. A quantity-boundary alias allowed inconsistent cell metadata;
  the wrapper now ties metadata and original period together. Economic SPL and
  originals did not change. Root review: `ordered-gates-root-review-20261124-a`.
- **C13:** simple outstanding40 versus dependent18; actual paid80 and original
  issued100/110 remain distinct. A genuine old P2 tier changes10 to8; repeating
  the correction yields zero new change. Eleven root publication reviews
  compare full state to fresh original-data oracles. No unbounded correction
  history, bank execution or general overpayment-recovery claim follows.
- **C09:** basis reserve and earned producer holdback need different canonical
  state namespaces even for the same agreement/participant/pool/asset. Six final
  templates and descriptors now enforce this. Gross100, fee10, share1/2,
  reserve rate1/5 distinguishes basis addition20/current35 from holdback9/current36;
  fee0 is not a discriminating example. Releases use original actual capped
  additions, not remaining balance. No unsupported real-source release-policy
  interpretation was inferred. Root and independent review cohorts are
  `reserve-stage-native-root-review-20261124-a` and
  `reserve-stage-independent-review-20261124-a`.
- **Dates:** supplied report/issue metadata has no implicit clock and does not
  change financial ports, graph or saved state. Default array-v1 module result
  digests include manifest metadata; bounded-v1 and both compact-v2 semantic
  digests exclude it. Do not generalize one digest rule to every profile.
- **Components:** only explicitly registered module profiles are supported;
  completeness of declared relationships is an assumption, not an inferred
  proof. Unknown joins hold the whole batch; connected distinct atomic roots
  require a real coordinator. Workers remain exactly one. Only C10 has a trusted
  production profile. This is not permission to build large-batch infrastructure.
- **Readable:** role bindings are hygienic per settlement heading. Authored
  strings, field labels, selectors, citations and report ports are preserved.
  Duplicate technical-output diagnostics still apply. A native report parser
  now splits only at the first separator, accepting record-valued reports.
  `readable-multi-independent-review-20261124-a` independently qualified this;
  `readable-zero-heading-20261124-b` compares old/new scalar no-heading programs
  byte-for-byte across relevant outputs. A prior over-budget combined Lean
  compile/run receipt is retained; AOT compilation and runtime then passed under
  their separate unchanged budgets.
- **Numeric:** Ratio normalization/precision and USD quantum/rounding stay
  explicit and dimension-distinct. Original12.345% at percent precision2 yields
  fraction .1234 half-even versus .1235 half-away. Two .01×.5 lines distinguish
  row from aggregate rounding: even0 versus .01, away .02 versus .01. All five
  modes and signed cases are covered in the finite profile. The adapter does
  not do financial math. One deliberately unqualified trusted-prepared-input
  counterexample is retained separately; do not count it among the209 custody
  qualified publications. `final-audit.json` SHA-256 is
  `1123e294c80fb9bec51e00890c947fee0a67aa4bdffc0dfda801a61da70c6c03`.

The immutable financial source hashes are indexed in each case README and
cohort manifests. Important cross-checks: C10 `e9b76f27…`, C11 `a40b438e…`,
C13 `fd9905e1…`, C09 `4d658937…`. Check full manifest hashes, not these shortened
display prefixes, before reproducing or promoting anything.

Failures remain part of the record. In particular,
`ordered-gates-full-20261123-a`,
`dependent-replay-native-helper-20261123-a`, and
`dependent-replay-native-followup-20261124-a` failed for documented custody,
assertion and/or Windows retention reasons. Later focused fixes qualify the
corrected snapshots; they do not turn the old runs into passes. See active-work
and each cohort for exact failure counts and recovery details.

## 6. Performance: current evidence and the work still authorized

The read-only intake plan is external
`artifacts/spl/performance-intake-plan-20261124-a/{harness-design.md,plan.json}`.
Its `execution_started` is false. It predates today's scope reduction: reuse the
workflow and carry design, but do not automatically execute every proposed
compile study, optimization, admission stress case or larger workload.

The dated `compact-canonical-1000-20261123-b` sample measured:

| Observation | Value |
| --- | ---: |
| End-to-end wall time | 40.729368s |
| Native audit phase | 9.436637s |
| Reader phase | 5.341661s |
| Target process, including startup/decode/calculate/serialize | 0.047558s |
| Publication phase | 5.850828s |
| Additional independent consumer reload | 5.601570s |
| Canonical result bytes | 269,498 |
| Nodes / edges | 64,480 / 88,010 |
| Expanded logical audit bytes | 776,599,360 |
| Wire audit bytes | 43,503,437 |

This is one dated shared-host observation, not a final-current repeat benchmark,
pure arithmetic time, p95, SLA or proof of four-period carry. Phase observations
can include nested work; do not sum/subtract them as if all were exclusive.
Older chain experiments did not establish genuine canonical saved-state carry.
An older full protocol failed while reconstructing a 1,000-record v1 result under
the64MiB limit; retain that failure separately from compact-v2 success.

### Suggested bounded measurement protocol

After final integration is verified:

1. Freeze one coherent short-path checkout, toolchain, imported modules, source
   and compiled pins. Record hardware, OS, host load, worker count, target-cache
   status and clocks. Use unchanged financial algorithms and original fixtures.
2. Use the existing RR03 representative mixture at100 and1,000, with disclosed
   title/participant splits. Compute independent expected results from originals
   before projection, including every title, cash/fee/cost/basis/share/earned
   total, funding/advance/population, authority and lineage obligation.
3. Measure the actual public canonical workflow with `audit_profile="compact-v2"`
   and comparison, plus a separate bounded consumer reload. Report public-return
   and consumer-total times separately. Keep compile misses separate from
   cached target execution; never call a fresh process a cold OS cache.
4. Run four actual consecutive closes for each size. Reload each completed
   publication; carry its actual key, quantity, boundary and `prior_result_ref`,
   removing only the movement field when preparing opening cells. Authority
   and memberships must support continuity from the first close. Do not extend
   old dates retrospectively merely to make carry pass.
5. Preserve the original50 funding IDs/dates/amounts in the1,000-record chain,
   with950 fresh records per close:3,850 distinct originals across four closes.
   Expected recoupment is250→0→0→0, not a fresh250 every period. Stop on the
   first failure; later periods are not executed, and no invalid state is
   consumable. These remain unissued calculations.
6. Collect repeated timings and parent/child memory under existing bounds. The
   intake plan suggests three initial fresh-output observations plus30 later
   fresh-process observations per size; this is a proposal, not a user-mandated
   sample count. Disclose warmup/cache choices, successful-run denominator,
   failures/censoring, median, nearest-rank p95 and maximum. Do not invent chain
   p95 from a single four-close chain or mislabel working set as allocation.
7. Retain exact commands, inputs, independent comparisons, process resource
   reports, actual publications and publicly reloaded evidence outside Git;
   commit a small reproducible harness/index/report. Report failures honestly.

There are four normal complete-graph validations: execution validation, owned
attachment, precommit publication and postcommit validated return. Independent
consumer reload is a fifth. Instrument original calls once, preserve temporary
logs before cleanup, and disclose inclusive timings. Do not remove required
validation to make a graph cheaper. Pure-driver timing, if useful, must remain
separate from canonical-workflow percentiles.

### Capacity envelope to publish

Current guards, not general throughput guarantees:

- Compiler-only child profile:1GiB /180s. Runtime/reference/reader child profile:
  256MiB /60s. Do not ratchet them to obtain a passing benchmark.
- Wire/result/stdout bounds:64MiB in the relevant bounded paths. Logical audit:
  1GiB; native audit observations:100,000. The dated1,000 sample already uses
  approximately72.3% of the logical-byte guard and64.8% of the wire guard.
- Raw facts plus evidence events and decoded/projected collections have their
  own100,000 guards; parent-record count alone is not capacity. A forecast of
  60,000 parents with20% eight-way splits produces96,000 allocation rows and
  144,000 projected receipts, exceeding the current collection admission bound.
  Label this an admission forecast unless actually tested.
- Component planning has64 jobs,64MiB aggregate packages,8MiB plan/resource
  metadata and16KiB resource keys, but only registered module profiles and one
  worker. Legacy SV workloads do not have an approved module profile. Do not
  substitute fixed-state-key C10 jobs for independent SV workloads or claim a
  batch benchmark that did not run.
- Existing generators select100/1,000/10,000. Do not casually request arbitrary
  99,999/100,000/100,001 financial cases without valid original facts and a byte/
  memory forecast. If a byte or memory guard rejects first, that is the observed
  limit; it does not certify the count boundary.
- Do not extrapolate a supported record maximum linearly from the1,000 sample.
  Workload shape, splits, terms, periods, graph size and source complexity matter.

Publish a table with workload, period count, backend/profile, repeats, latency,
memory, input/result/wire/logical bytes, guard proximity and failure mode. Separate
measured supported cases, known guard limits, projected admission failures and
unmeasured larger workloads. Describe possible future scaling work as future
work; today's task is to identify limitations, not implement that platform.

## 7. Remaining feature work: keep it finite

### Integration and release

The assembled candidate exists; the next step is verification, not recreating
the cases. After an explicit resume, inspect `C:/spl-next` and main again, freeze
the final source/build snapshot, run `lake build`, `lake build spl_sv_indexed`,
`lake exe smoke`, `lake exe spl_smoke`, relevant combined checks and a full
regression. Use the old external immutable runner as a pattern, not an executable
with stale hard-coded roots. Record exact discovery/pass counts for the new
snapshot. Keep source stable during a long regression.

Resolve any integration incompatibilities without repinning historical fixtures.
Verify descriptors, transitive library/policy/closure references, templates,
original/prepared correspondence, saved-state continuity and emitted targets.
Avoid registry races between dynamically imported test harnesses. Root should
independently inspect selected actual publications, not only agent summaries.

Only then promote into main after preserving the23 untracked older prototype
files and checking for user edits. Preserve the qualified source bytes, create
a new release evidence record and update current inventories honestly. Check
fresh-checkout reproduction, documented commands and effective backend/import
roots. No push or external publication was requested.

C09 historical native harnesses are retained in the integration tree at
`validation/retained-harnesses/c09/20261124/`. The Git module tests are reference
checks; portable native reproduction is still a release concern. The retained
scripts contain fixed paths and import-time behavior. Read `README.md`,
`manifest.json` and `portable-runner-proposal.md`; do not execute historical
snapshots casually. Add only the narrow portable runner needed to reproduce
the current namespace profile, if final release reproduction requires it.

### Relationship safeguards

The earlier relationship/cardinality research can inform this, but do not
resume the deferred general external-data-interface program. Identify supported
workflows where relationships can multiply amounts, disappear, or bind the wrong
recipient. Make the scope and cardinality expectations explicit.

Check duplicate parent identities, absent parent/recipient references, repeated
child membership, intended one-to-one versus one-to-many relationships, empty
groups, and accidental many-to-many products (a two-by-three example is useful).
Assert original-ID coverage and amount/contribution reconciliation rather than
only output row counts. Preserve established legitimate split allocations and
identity semantics. Reject at the actual appropriate stage; do not label a
pre-source binding failure as a native financial assertion.

### Reports and audit completeness

Inventory what current supported reports promise before adding new formats.
Check typed outputs, actual policy values, party attribution, row contributions,
rounding/reconciliation bridges, closing state and original-source lineage for
the supported finite profiles. Distinguish rejected, excluded and included-zero
inputs where the contract/report requires it. Make authored-source spans and
field pointers useful without changing financial error precedence merely to
make a diagnostic easier to test.

Compact-v2 must retain all owned nodes, values, dependencies, errors and skips;
do not replace it with an incomplete sampled trace. Bounded old-v1 carry is
explicitly a partial receipt, not a full historical audit reconstruction.
Check failed/incomplete publication authority, preview state absence, date
metadata, multiple-party report behavior and reload integrity. Decide any
unclear report requirement narrowly from existing promises and reviewer notes.
Do not silently turn this into the deferred exhaustive combinations campaign.

## 8. Agents and orchestration

The owner explicitly prefers sub-agents and a root orchestrator, using existing
resources and documents to preserve context. The prior local roles were:

| Agent | Work and useful context |
| --- | --- |
| `validation_trace` | Compact/v1 publication and resource plumbing, C10, dependency components, read-only performance intake plan. |
| `validation_source` | Narrow imports, native/Python helper emitters, C11 and numeric profile. Last alias/enum exploration is deferred under the new scope. |
| `reserve_source` | Independent C09 source and readable multi-settlement. Relationship/cardinality exploration can inform the retained safeguard task. |
| `validation_matrix` | Independent C02/C11/C13/numeric/C09 oracles and date metadata. Useful for scope/evidence review. |
| `validation_generated` | Earlier feature matrix/generated-validation role; historical context, not a live job. |

No child is live in the inventory checked for this handoff. A new session may
need new agents rather than follow-ups to old names. There are four active
slots including root. Assign exact owned files, short checkout, baseline commit,
evidence directory, immutable originals and completion criteria. Separate
implementation from independent original-data/oracle review. Do not let agents
edit shared compiler/schema files while a frozen integration run is active.

For resumed work, a useful allocation is: one integration/reproduction owner,
one finite relationship/report owner with explicit path boundaries, and one
performance/evidence owner once the snapshot is stable. Root manages scope,
reviews actual evidence and integrates. Do not delegate the deferred broad
interface, convenience, currency or large-batch tasks.

## 9. Practical lessons and pitfalls

- **Import isolation:** embedded Python's `._pth` injects the main checkout even
  when cwd or `PYTHONPATH` points elsewhere. Explicitly prepend the intended
  root, remove competing roots, and assert every relevant imported module's
  `__file__`, `ROOT`, `LIB` and `LEAN_PATH`. Use `-B` for read-only probes. A
  plausible command run from the right directory can still test the wrong code.
- **Lean identity:** use pinned4.35.0 and Lake's coherent `.olean`/native object
  build. Direct `lean -o` into Lake's library can change imported C symbol names
  and break linking. Compiling and then running with `lean --run` can combine
  compiler/runtime memory; AOT stages have separate declared budgets.
- **Windows paths:** use a short physical worktree, not a junction. Deep
  `.lake/module-runs/<hash>/closure/<hash>-descriptor.json` paths can exceed
  MAX_PATH while original short-root execution succeeds. Retain with relative
  ZIP entries or carefully checked extended paths. Verify CRC/hashes and bounded
  reloads. A failed copy/cleanup is still a failed protocol, not financial proof.
- **Source custody:** raw, staged and committed bytes may differ through CRLF
  conversion. Preserve `.gitattributes`, all transitive source/template/policy
  pins and original records. The frozen C13 SPL has18 whitespace-only lines;
  preserve that exception rather than rewriting financial source for style.
- **No hidden finance in adapters:** adapters may enforce custody, parse exact
  facts and bind ports. Compute financial policy in SPL, and independent expected
  results from original facts, not from the projected inputs being validated.
  Typed-only prepared APIs are not proofs of original-source correspondence.
- **Alias and state custody:** compare cell metadata, quantity metadata, raw
  period and retained `prior_result_ref` independently. A shared mutable object
  can make a two-sided comparison pass while both sides were altered together.
  Distinct economic state purposes need distinct canonical namespaces.
- **Error layers:** module-reference scope checks can reject before native
  execution. Public compact loading wraps incomplete child stages; C13 observed
  `AUDIT_INVALID`/load with cause `AUDIT_STAGE_FAILED`, rather than the unwrapped
  message initially expected. Record the actual stage/cause and running marker.
- **No forced uniformity:** C02/C09 accept known UTC with unknown local offset
  (`-00:00`) in selected profiles; frozen C13 rejects it. Do not broaden a frozen
  source profile to make all examples look alike.
- **Typed audit decoding:** ordinary user records resembling ratios must remain
  records unless checked types say otherwise. Helper extraction must preserve
  deferred evaluation and errors/skips; no global cached settlement values.
- **Publication scope:** completion markers and hashes protect bounded
  single-process custody/integrity. They do not authenticate external facts or
  prove distributed transactions, concurrent-writer safety or power-loss recovery.
- **Verification claims:** no `sorry` or custom axioms. Existing scalar/toy
  compiler proofs are infrastructure with explicit assumptions, not a proof of
  the entire participation compiler or every contract interpretation.
- **Communication:** use plain language. The owner objected to jargon-heavy
  approval questions and to work expanding beyond clear requirements. Existing
  instructions authorize normal finite implementation after resume; do not ask
  the same currency-gate question again. Keep progress updates meaningful and
  report uncertainty/failures honestly.

## 10. Ordered next steps and stop condition

1. Read the resources and scope above and the owner's newest instruction. This
   handoff leaves the goal paused; a new instruction to continue is sufficient
   to resume, without asking for redundant confirmation.
2. Inspect Git, imports, worktrees and processes. Preserve the older untracked
   drafts before any overlapping promotion; keep current user edits intact.
3. Verify the assembled integration snapshot with pinned builds, smokes,
   relevant combined checks and frozen full regression. Fix actual defects,
   retain failed records and qualify the final exact source.
4. Finish the bounded relationship safeguards and report/audit obligations,
   updating the actual current requirement inventory. If these change code,
   verify the resulting final snapshot rather than relying on the earlier run.
5. Measure100/1,000 and actual four-close carry, repeats and memory on that
   stable snapshot. Publish the reproducible capacity/limitations report.
   Only revisit audit optimization if measured absolute cost warrants it.
6. Complete local integration/release documentation and evidence. Clearly
   distinguish measured capabilities, assumptions, unsupported cases and future
   work. Leave the testing-combinations discussion and all explicit deferrals
   for later; do not start another feature cycle automatically.

The finish condition is a verified local release checkpoint for the retained
scope, a reproducible complete-workflow measurement and a supported limitations
statement, with remaining deferred work clearly listed. It is not “every row
in the old backlog is done,” nor “the compiler handles every real contract.”

## 11. Copyable prompt for the next session

> Continue SPL in `C:/TheHaltingSolution/dynamic-domain-lang`. Read AGENTS.md,
> docs/lean-resources.md and docs/spl/session-handoff-2026-11-25.md, then follow
> its resource pointers and previous handoffs. The owner requested this handoff
> before more work; the goal was left paused. A new instruction to continue
> authorizes resuming without another confirmation. The saved candidate is clean
> C:/spl-next, branch feature/spl-completion-integration, HEAD d6d04f8; main is
> 27d8222 plus documentation and has23 untracked older prototype files to preserve.
> 1,301 tests passed at c80ac34; the newer1,547-method discovery is not a final
> passing regression. Finish integration/release, finite relationship safeguards,
> reports/audit completeness, complete100/1,000 workflow measurement with actual
> four-period saved-state carry, and a supported capacity/limitations report.
> Do not optimize audit solely because its percentage is high; about41s is
> acceptable to the owner. Defer general data interfaces, additional source
> examples, convenience syntax, native FX, the self-modifying skill and large-
> scale batch infrastructure. Discuss the broader combinations-testing strategy
> later, while still running checks needed for present changes. Use sub-agents
> with exact ownership, existing research/style resources, short worktrees and
> independently reviewed original-data evidence. Do not repin historical runs,
> overstate proof/scale/approval, push remotely, or silently expand the finish line.
