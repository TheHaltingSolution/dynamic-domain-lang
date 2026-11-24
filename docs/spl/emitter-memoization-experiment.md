# Native emitted-definition memoization experiment

Status: focused controls passed; eight current financial modules were then
deliberately regenerated and rebuilt. Promoted compatibility checks are
separately recorded below. This changes
emitted evaluation strategy, not the financial SPL sources or runtime helpers.
It does not repair the indexed source's native audit expanded-byte failure.

## Concrete defect and candidate

In the archived emitter, `SPL/Emit.lean`'s `scope` first bound definition names
to `Unit → Eval Value` closures and `emitDefinition` generated bodies against
that environment. Later declaration-order forcing rebound names to `pure`
values. Previously generated closures still captured the earlier closures,
so dependencies could be recomputed despite their earlier successful force.
Native `Interpret.resolve` and Python `Environment.get` already cache a
definition's result; this was an emitted-target discrepancy in evaluation cost.

For the old indexed generated C, the successful per-picture call graph contains
four receipt-group and three cost-group builds, and the complete picture map
is demanded twice, in addition to the two initial group builds. That gives
`2 + 14 × pictures`: 114 at eight titles, 562 at forty. These were initially
**C-derived counts**, not observed runtime counts. The focused counter below
subsequently measured the eight-title prediction.

The candidate changes only `SPL/Emit.lean`: hoisted definitions become
`Thunk (SPL.Eval SPL.Value) := Thunk.mk (fun _ => body)` and dependency reads
use `.get`. It preserves static DAG construction, lazy branch selection,
declaration-order forcing, first demanded business error and fresh
input-dependent scope bindings for calls, loop iterations and fold steps.
It uses neither `Thunk.pure` nor a global cross-input financial cache. No
`Runtime`, `Core`, checker, IR, parser, Python evaluator or financial source
was changed by this candidate. Pure successful/failed `Except` results are
memoized; there is no runtime observation counter in production finance.

## Pinned Lean semantics

The pinned Lean 4.35 toolchain's `src/lean/Init/Core.lean` lines 109–148 defines
`Thunk.mk` with the `lean_mk_thunk` external and `.get` with
`lean_thunk_get_own`. Its `include/lean/lean.h` lines 1513–1542 initializes an
empty cache plus closure and checks the cached value before forcing. The local
official reference manual `Manual/BasicTypes/Thunk.lean` lines 20–25 and 57–73
describes caching and releasing the closure after computation. These compiled
runtime operations, rather than the type's name or logical equivalence with a
function, justify selecting it. Paths and reproduction setup are indexed in
[lean-resources.md](../lean-resources.md).

## Finite verification and observed counter

`Tests/test_emitter_memoization.py` compiled temporary, freshly native-emitted
Lean to C and native executables with the pinned Lean/leanc/clang tools and
the existing Lake runtime object/link closure. It never rewrote repository
`.olean` files, production runtime objects, old generated Demos or old financial
executables. Optional dated old-emitter comparison was enabled in both recorded
cohorts using the archived pre-edit `spl.exe`; absence of that archive in future
portable runs is explicitly reported as unavailable, not credited as coverage.

The final `emitter-thunk-checks-20261123-b` cohort passed all six methods and
31 recorded observations in 59.543186 seconds, with no errors/failures/skips
and unchanged source, executable, toolchain and runtime-object hashes. It checks:

- Forward dependencies and repeated references against independent exact
  answers, Python reference, current native IR, and both freshly compiled old
  and new emitted code.
- Unselected dangerous branches, early requirements, eager failing definitions
  and first forward-dependency failure before a later requirement.
- Different loop rows and fold steps, nested imported pure functions with
  different arguments, and strict failing function arguments.
- A verbatim new `compile-library` output imported by a separate native driver,
  making 22 settlement calls in one process. All nine original-fact fixture
  variants, four independently controlled varied openings (including a repeated
  opening after other inputs), and nine typed empty/order/duplicate/date/error
  cases match the complete historical compiled target. Original-fact oracle
  controls run before projection, including for each varied opening.

An isolated generated-C wrapper counted calls at the external grouping helper
boundary. It observed **114 old builds versus two new builds** for the same
eight-title/ten-receipt input, with identical complete financial outcomes.
Instrumentation affects only disposable generated C; it adds no production
counter, finance formula or timing claim. Original and instrumented C, native
executables, bindings and outcomes are retained. Forty-title 562 remains a
call-graph deduction, not an observed runtime count.

The earlier `emitter-thunk-checks-20261123-a` also passed six methods/31
observations in 59.690366 seconds. The final cohort strengthens each varied
opening with a fresh original-fact oracle calculation; it is the final test
source snapshot. Host CPU could be shared with the isolated 813-method checkpoint
regression. Neither duration is a settlement performance measurement.

## Exact pins and archived baseline

The pre-edit `emitter-thunk-baseline-20261123-a` archive retains old emitter,
old/new financial SPL sources, both generated financial Demos and executables,
old frontend, old indexed C and link response, plus their SHA-256 manifest.

| Object | SHA-256 |
| --- | --- |
| Old emitter source | `f6c5253399c357c3e154dd0fff7321b13bb3b61ff51fc3d455782f109524b409` |
| Candidate emitter source | `c59ea2af4607b9be5676f1fcb5273562f64e61fe28dda103b325931504a4822d` |
| Old compiler/reference closure | `323f0d844fe11344713523f40d83d3b67d32d1376ce89da823875d72c2a297bc` |
| Candidate compiler/reference closure | `abee14432a7a972b94a02795668d9ff8bbf97a5758f5558dc9178a7761e490eb` |
| Candidate module closure | `daf14a19e4b00bbb918583d76e73451322de8ecea1f9f1192dd3c404c1a06cde` |
| Unchanged runtime closure | `673bb0fe936c48a60c1cf5a1a265fb1d1f9f3cd432f380ee9b3011b7729dace9` |

Artifacts live outside Git under
`C:/Projects/Film_TV_participation_dynamic_DSL/artifacts/spl/`.
The final cohort's `pins.json`, `sources/`, `tests.log`, `verification.json`
and `native/` preserve the dated execution evidence, including the exact
Lean version, tool binaries and reused native runtime object hashes. Parent
`lake build spl spl_smoke` passed 47 jobs before release for this cohort.

During the focused experiment the historical generated Demos, executables and
pure benchmark library were preserved. Fresh candidate emission differed, and
no new-compiler freshness claim was made against those old generated files.
The later deliberate promotion below replaces the current generated files;
the immutable dated archives remain the old compiler baseline. Nothing here proves universal
compiler equivalence, all error/resource precedence, audit completion at
10,000 records, emitted branch coverage, or an RR03 latency/SLA target.

## Deliberate current-target promotion

`emitter-thunk-promotion-20261123-a/before/` archives all eight old financial
generated modules, the old financial executables and pure benchmark executable,
pure driver/library state, frontend, relevant test/harness state and hashes.
The promotion used only the accepted native frontend: `compile` for SV, LG,
RQ-07, their three readable counterparts and the experimental indexed SV;
`compile-library` for the original SV pure benchmark library. Every original
contract SPL file remained byte-identical. No generated financial Lean was
edited by hand. `regeneration.json` records the exact sources, commands and
old/new hashes. The core/compiler/runtime identities above stayed unchanged.

The parent subsequently reported optional `spl_sv_indexed` build (22 jobs),
full default build (94 jobs), and both smokes passed. Current Demos and targets
now belong to the memoizing compiler, while the original financial source
remains the default. Exact fresh generation and complete financial compatibility
are checked by the promoted cohort, not inferred from a successful build.

`emitter-thunk-promoted-checks-20261123-a` passed **38 methods** in 69.153263
seconds with zero failures/errors/skips and unchanged core, source, executable,
toolchain, runtime-object and historical-archive hashes. It combines memoization
eight, indexed seven, pure-timer six and mixed-generator/gate seventeen methods.
Its 45 memoization observations include all eight exact fresh emissions, the
six current SV/LG/RQ-07 original/readable targets compared against complete
Python reference/native IR/historical executable outcomes, the same-process
22-call library controls and observed 114-to-two group builds. The six fixture
comparisons also assert the independent original 33,000 earned/18,000 payable
SV/RQ-07 controls and LG 35 payable. The indexed methods retain the 18-case,
four-native-backend comparison (72 invocations, with decode failures qualified
separately); pure methods check current library freshness and complete original
fact controls. Existing 100/1,000 original generator bytes and generation-gate
rejection tests pass. This is compatibility verification, not a new performance
measurement. The host retained concurrent regression/financial work.

The promoted original SV target executable SHA-256 is
`23cb4df5d94d12754976f89513fa8af69f337b0ca0be995b58be48a7aa55e684`;
the indexed target is
`91d3e34c08831d585e08d7c69e40ca7db7d46e78de38bb1a9a92cd758e534004`;
the pure driver is
`bc285fdd62c51959a647778cee6c7e05887bbbad0932a59b131e21d76e15e27a`.
The cohort manifest retains every other current target hash and all generated
source hashes. Its `memo-native/` and `indexed-native/` retain complete backend
results, financial inputs, original facts, projections and comparison evidence.

The mixed harness records `target_generation: spl-native-definition-thunk/1`
and requires it in a scale prerequisite. `legacy` names the original SV
**source implementation compiled by the current compiler**. For indexed runs,
the compatible `old_target`/`old_native_emission` field names refer to this
current original-source algorithm baseline, not the historical pre-memoization
compiler. Historical targets are separately qualified archives and are not
silently substituted into a current benchmark. The new test hooks explicitly
distinguish an available historical target directory from a current target.

## Separate observation counts

The indexed source's earlier Python 10,000-reference run completed with 11,467
observations while its native IR run reached the 100,000-observation guard.
Python's evaluator returns literal/name/field values without uniformly adding
nodes; its projection loops also lack the native interpreter's complete
instance observations. Native `evaluate` records each IR expression and
`iteration` adds the full collection operand for each row. These are different
observation alphabets. Their counts cannot serve as reciprocal coverage
denominators or establish emitted-target coverage. The source-only failure and
resource limits remain recorded in [indexed-sv-experiment.md](indexed-sv-experiment.md).

## Post-promotion bounded completion probe

The separate current-generation
`rr03-indexed-postmemo-{100,1000,10000}-20261123-a` probes kept every guard and
all compiler/module/runtime pins above. Both smaller cohorts passed, including
complete financial controls and byte-identical archived indexed audit wires.
The single 10,000-record/40-title compiled indexed target completed in 0.323204
seconds (0.296875 CPU seconds, 46,964,736-byte peak working set), agreeing with
the independent original-fact oracle on every title/pool/closing result and the
current original-source target. This is new completion evidence under the
memoizing compiler. The separately pinned old emitted indexed target's
60-second timeout remains a failed historical result.

The full audited close **still failed** after 21.706706 seconds of audit work:
native `RESOURCE_LIMIT` with empty money/state, then
`COMPACT_EXPANDED_BYTE_LIMIT`; a 14,237,800-byte prefix and no completion record.
Reader and all dependent four/eight-close successors were `not_executed`.
No retry or guard increase occurred. The isolated 813-method regression was
active, so these single observational process times establish no quiet causal
speedup ratio, pure calculation median, p95 or RR03 SLA. The full exact results,
source/input byte checks and prefix qualification are in the indexed experiment
document and external `postmemo-verification.json`.
