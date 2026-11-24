# Python emitter definition reuse

23 November 2026. This repairs the secondary Python-to-Lean generator; the
primary native frontend remains authoritative. Native Emit already used cached
thunks. The Python emitter still emitted Unit-to-Eval closures, so later
references captured the original unevaluated functions even after declaration
force sites computed their values. Nested definitions could recalculate entire
financial histories many times.

The retained Disney acceptance attempt
`merchandising-reprice-checks-84046c1c` failed before its39-method cohort: native
IR/native-emitted/reference publication agreed and completed, but the separate
Python-emitted baseline driver timed out at the unchanged180s limit. That run,
old driver and original source pins remain failures. No backend is omitted and
no limit is raised to qualify the correction.

## Narrow change

`_Emitter.scope` now declares `Thunk (SPL.Eval SPL.Value)` with `Thunk.mk` and
uses `.get` for definition references. Topological construction, declaration
force positions, strict arguments and lazy branches remain in place. New cells
are constructed for each function, loop, fold and settlement invocation.
`Thunk.pure` is not used because it would evaluate the body eagerly. This is the
same mechanism already checked in [native emission](emitter-memoization-experiment.md),
using the pinned Lean4.35 caching semantics. No native IR/runtime/source program
or financial policy changes in this patch.

## Executed evidence

`C:/Projects/Film_TV_participation_dynamic_DSL/artifacts/spl/python-emitter-thunk-20261123-a/`
retains the actual pre-change Python emitter, exact source hashes/snapshot,
generated Lean/C/executables, full outcomes, source bindings and test logs.

The frozen combined34-method cohort passes143.525280s, zero failures/errors/
skips/source drift, plus94-job build and both smokes. It contains six new focused
methods, nine existing emitter methods,16 quantity methods and three native-fold/
linking methods. The focused checks execute old and new Python-generated Lean
on forward dependencies, four first-failure/lazy cases, loop/fold locals, nested
imports and strict-argument failure. Twelve varied input/opening settlements
execute in one process for both generators and match hand controls.

A disposable generated-C wrapper observes actual calls to Runtime.groupValues
for the same8-title/10-receipt synthetic typed fixture: old114, new2. Complete
values agree with the reference. The wrapper modifies neither production
financial source nor the shared runtime object. These counts are a structural
performance witness, not wall-clock latency or independent original-fact
financial truth. Hand scalar/state controls and the later independent Disney
original-fact cohort provide separate evidence axes.

Compiler/reference pin is
`20ea52ba37b7d84b4d5d7ed62c9c38b44a928cf1ffc2287f2bec358bda31c260`;
module `a5165f5db8a42a7365afc553e6e518913ded0065389c1e0a717dd197cd6d412a`;
runtime remains `673bb0fe936c48a60c1cf5a1a265fb1d1f9f3cd432f380ee9b3011b7729dace9`.
The native frontend, generated native Demos and runtime source remain unchanged.
The snapshot was copied after rechecking every frozen source hash; the indexed
fixture is retained from its unchanged9f9cf31 source.

The initial six focused working-tree methods also passed17.748s before the
archived comparison/broader run. They are not added to34 as another corpus.
The Disney driver and complete39-method acceptance must be rerun under the new
pins before source-family completion. No full latest-tree regression, arbitrary
program performance, emitted-target decision coverage or whole-compiler proof
is claimed by this finite cohort.
