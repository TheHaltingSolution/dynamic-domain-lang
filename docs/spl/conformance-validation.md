# Bounded conformance validation

The later [mutation campaign](semantic-mutation-campaign.md) records separate
four/six-original-case phases and a hardened frontend followup. Four actual
backends execute; financial kills, survivors, equivalence and frontend invalids
are distinct. This does not rerun or expand the historical seeded campaign below.

Current continuation: the mutable matrix has 35 rows: 31 witnessed variations
and four explicit gaps, mapped to 49 unittest selectors. These include the
bounded original-rate returns and authorized current-entitlement transfers.
The counts and hashes below describe the original 12-row/fourteen-selector
campaign, whose matrix and source bytes remain archived. New methods and layers
have separate execution records; a new combined 49-selector campaign is not
claimed here.

`--corpus decisions` selects twelve cells over six source templates; `--corpus
combined` adds those cells to the original amount boundaries. Successful else,
Boolean short circuits, priority zero/fallback/tie, demanded failures and actual
output discard now have three-backend witnesses. The separately retained review
is `artifacts/spl/decision-corpus-review-20261123/summary.json` under the external
project root. `scripts/spl_negative_conformance.py --output NEW_DIRECTORY` retains
four rejected frontend variants, two fabricated native IR mutations plus a valid
control, and a canonical scope rejection as distinct execution layers. Its latest
saved record is `artifacts/spl/negative-conformance-20261123-c/summary.json`.
The [rounding interaction cohort](rounding-interaction-design.md) separately passes
47 configurations through three backends, with a declared160-cell denominator,
86/86 configuration pairs and all40 safe mode/stage/sign triples. These finite
cases do not establish exhaustive grammar or all-program combination coverage.

The [feature/test matrix](feature-test-matrix.json) maps 12 implemented variations
to 14 existing unittest methods and keeps six explicit gaps. `witnessed` in the
inventory means that the test's assertions and execution paths were inspected;
an execution report separately records whether it passed in a particular run.
Requirement IDs refer to the [conformance ledger](conformance-ledger.md).
This is the first bounded validation milestone proposed in the session handoff.

## Verified execution: 23 November 2026

The default campaign passed in **468.912938 seconds**: eight generated cases
through reference/native IR/native-emitted Lean, plus all 14 mapped test methods
(439.173 seconds for the witness batch). All 12 witnessed matrix rows received
passing execution credit; six rows remain gaps. No source changes were detected
during the campaign. Its compiler/runtime/module identities match the unchanged
`0.4.3-dev` kernel. The [verification index](conformance-validation-result.json)
records exact report hashes and external artifact locations.

| Bounded variation | Execution |
| --- | --- |
| K1 direct priority and registered Cedar delivery | Passed |
| K2 options/maps/grouping/joins | Passed |
| K3 ordered folds/linking and structured successor state | Passed |
| Seven M1a recipes, threshold equality and serialized carry | Passed |
| Typed quantities/rates and canonical native meter carry | Passed |
| Readable SV/LG/RQ-07 and native audit DAGs | Passed |
| Quest dated method/certificates and two rounding mutations | Passed |
| Signed-return methods, cross-contract transfer, multicurrency/FX, withholding/deferment | Gaps |
| Emitted-target decision instrumentation and whole-compiler proof | Gaps |

One combined run of **19 new harness test methods** passed in 32.266570 seconds.
The 86-target `lake build`, `lake exe smoke` and `lake exe spl_smoke` passed.
A separate single-case authority-failure replay from seed 7 passed in 5.423862
seconds, correctly recording the retained seed and leaving the matrix unexecuted.
These are supplemental checks: the historical 386-test discovery and 16 native
suites were not rerun as a full cohort. The existing implementation baseline was
not replaced. A final archive audit added `validation/` to the general
`scripts/spl_freeze.py` inventory and extended its existing regression; that
one-method check passed separately in 0.105209 seconds after the campaign.
The calculation/compiler/campaign code remained unchanged.

The generated traces contain 349 observations, 15 decision observations, eight
skipped roots and three failed observations across two expected blocked cases.
There are no discarded-output observations in this generated cohort. Successful
`else`, selection and short-circuit decisions are also absent here; existing
mapped witnesses and the separate trace tests cover selected additional paths.
The source hashes and all eight observation reports were independently rechecked
against the retained source/trace bytes. These counts establish no coverage
denominator or emitted-target branch coverage.

## Repeat the campaign

Run from the repository root, using the pinned Python/Lean setup in the README:

```powershell
& 'C:/Projects/Film_TV_participation_dynamic_DSL/environment/python/python.exe' scripts/spl_conformance.py --output C:/Projects/Film_TV_participation_dynamic_DSL/artifacts/spl/conformance-20261123
```

Use a new output directory for every run. The default command runs the eight
generated boundary cases and every matrix witness, deduplicating test selectors.
It rejects the five documented backend-override environment variables so they
cannot silently narrow the existing tests. All requested witnesses must pass;
skips, expected failures and missing test outcomes receive no passing credit.
Fixture failures and interrupted witness processes fail the campaign.
Matrix stage labels remain inspected declarations; the existing unittest methods
do not emit per-test backend telemetry. Generated cases record individual
reference, native-IR and native-emitted results directly.

`--seed 7 --count 12` changes the neutral facts reproducibly and adds four bounded
samples to the eight mandatory boundaries. Seeds range from 0 through 2^32-1;
counts range from 8 through 64. `--generated-only` runs the generated corpus and
leaves all matrix witnesses explicitly `not_executed`. Its passing status covers
only the requested generated execution.

Replay the retained list, or one retained `generated/case-NNN/case.json`, with:

```powershell
& 'C:/Projects/Film_TV_participation_dynamic_DSL/environment/python/python.exe' scripts/spl_conformance.py --generated-only --replay-cases C:/Projects/Film_TV_participation_dynamic_DSL/artifacts/spl/conformance-20261123/cases.json --output C:/Projects/Film_TV_participation_dynamic_DSL/artifacts/spl/conformance-replay-20261123
```

The generated source is a disclosed experimental schedule with direct bindings,
not a newly registered financial policy. One source template exercises exact
rational sums, below/equal/above thresholds, strict submicrosecond cutoff
equality, signed half-away cent rounding, empty inputs, lazy unselected division,
closing balances and two atomic failures. Independent controls in
`validation/generated_cases.py` use standard-library fractions and integer
timestamp ticks; they import no compiler calculation or transport helpers.
They consume the original neutral values before bindings projection. Eight cases
are boundaries, not eight independent language features or an exhaustive domain.

The command writes these artifacts:

| Artifact | Evidence and limits |
| --- | --- |
| `campaign.json` | Actual case seeds, Python/platform, actual Lean executable/version, pinned toolchain, compiler/runtime/module identities, requested backend paths, individual generated outcomes, witness status and elapsed time. |
| `source-manifest.json`, `source-freeze/` | Exact tracked source bytes plus new campaign code/tests/matrix, hashes, Git HEAD and working-tree status. Modified/deleted files and added protected source files fail the end-of-run stability check. Start with stable files: this is not transactional import isolation or an atomic snapshot under concurrent edits. |
| `cases.json`, `generated/case-NNN/` | Exact neutral facts, expectations, SPL bytes and bindings; completed backend results, emitted Lean, diagnostics and check result. Failures retain their original input without automatic minimization. These are development examples, not held-out cases. |
| `witness-selectors.json`, `witness-results.json`, `witnesses.log` | Exact existing test methods, unittest outcomes, fixture outcomes and raw combined output. Existing tests may clean temporary calculation artifacts; their original source/builders are frozen, but this runner does not retain every temporary binding or canonical package they create. |
| `feature-execution.json` | Per-row/per-witness execution, linked requirement IDs, inspected stages, properties, oracle identities and retained limitations. Gaps remain gaps. |
| `compiler-coverage.json` | Witness mapping only; compiler line/type-rule coverage is not instrumented. |
| `settlement-coverage.json`, per-case `native-ir-observations.json` | Source-hash-qualified native IR decisions, assertions, skips, failures and discarded outputs, with validated trace identities/dependencies/spans. No unobserved-path denominator or emitted-target decision coverage is claimed. |
| `domain-coverage.json` | Bounded feature combinations and pointer to domain witness execution; no exhaustive/pairwise coverage or capacity percentage. |

Read telemetry reports with ordinary JSON readers. Some trace telemetry uses JSON
`null` to denote an unavailable denominator or observation; these reports are
not strict SPL financial packages. Source/bindings and generated expectations
use exact financial transport. Interpreter observations remain separate from
emitted Lean value/state/error comparisons.

Remaining work includes malformed source/IR/package generation, additional source
templates, meaningful policy-specific metamorphic relations, systematic mutation
analysis with survivor classification, direct target coverage, more domain
families and workload measurements. Existing Quest tests map two selected
rounding mutations; they do not provide a general mutation score. The six named
matrix gaps are a sample from the broader ledger, not its complete gap inventory.
No kernel extension, baseline replacement, full compiler proof, capacity claim or
change to the pre-FX extension-selection gate follows from this harness.

## Next bounded increment

Add reusable source templates for successful `else` and Boolean short-circuit
paths (O08/U20), then priority zero/fallback/tied-top cases (O13–O15/U14/U20).
Keep exact independent hand controls and retain source/bindings per case.
Generate duplicate-field and invalid monetary-product source mutations through
both frontends; use native IR constructors for duplicate-identity admission
checks, because exported IR JSON has no public execution entrypoint. Finally,
retain an out-of-scope Cedar package mutation at the canonical boundary. Record
frontend rejection, fabricated-IR rejection and wrapper rejection separately;
none implies that a native financial calculation ran.
