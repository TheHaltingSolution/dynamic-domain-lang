# Live C1 work after checkpoint 9f9cf31

23 November 2026. This supplements the committed
[checkpoint](completion-checkpoint.md). The project goal remains active; this is
not a complete release. No push or pull request has been made.

## Owner conversation

RR04/LD03 responses are pinned in [their index](rr04-ld03-integration.md).
Neither reviewer qualified a contract-required calculation that existing SPL
cannot faithfully express. The owner now selects mixed-currency contracts for a later self-modifying
compiler tool/skill demonstration, and explicitly asks to leave native currency/
FX support out now. Complete other current feature/performance/testing goals
first; revisit the tool and currency example when those are verified complete,
or when the owner starts that phase. Preserve successful existing-language
methods. See [owner decision](ld03-owner-decision.md) and the later
[tool plan](self-modifying-compiler-demo-plan.md). No skill or FX work starts now.

## Stable checkpoint and current core

`7c13ef2` contains 189 verified/planning files. At that checkpoint all 49 staged
file pins matched Git blobs and physical bytes. The historical `0.4.3-dev`
baseline remains byte-identical to its archive. The later accepted emitter/AO/
civil/Disney-oracle sources are recorded in local
checkpoint `9f9cf31` (47 files). All seven newly staged file pins matched Git
blobs and physical bytes; the old baseline remained identical.

The current compiler/reference wrapper pin is
`20ea52ba37b7d84b4d5d7ed62c9c38b44a928cf1ffc2287f2bec358bda31c260`;
module `a5165f5db8a42a7365afc553e6e518913ded0065389c1e0a717dd197cd6d412a`;
runtime `673bb0fe936c48a60c1cf5a1a265fb1d1f9f3cd432f380ee9b3011b7729dace9`.
Native Lean/frontend/Demos remain at the accepted memoizing generation.
The new wrapper pin includes compact publication and secondary Python-emitter memoization. Archived
old runs retain their dated identities; AO/civil used abee/daf/673.

## Isolated full regression

Exactly `7c13ef2` is archived and extracted to the short physical Windows path
`C:/spl-7c13`. Fresh94-job build and both smokes pass. The full813-method
Python suite has completed:812 pass, one stale R1 standard-library-whitelist
failure, zero errors/skips,4099.274516 seconds. All original source bytes and
end compiler/runtime/module identities stayed unchanged. The retained overall
status is FAILED. The current-tree fix uses `sys.stdlib_module_names`; all15 R1
methods pass separately (0.087s), without financial golden changes.

Logs and final verification are under
`C:/Projects/Film_TV_participation_dynamic_DSL/artifacts/spl/checkpoint-regression-7c13ef2-b/`.
Exec35269 has ended. This is the previous checkpoint, not a full regression of
the newer emitter/AO/civil/Disney work. The first full run is not retrospectively
changed to passing; a clean newer-checkpoint regression remains required. Its
background CPU load was present during the post-memo probes and is now ended.

The fresh regression of exactly `e80024d` is now RUNNING from short physical
`C:/spl-e800`, evidence `checkpoint-regression-e80024d-a/`, exec session26641.
Default94-job build, optional indexed target build and both smokes pass.
Discovery finds887 methods. Loaded repository-module paths are recorded and
asserted outside the shared main tree. This includes the promoted native memoizing compiler, accepted AO/civil integration,
Disney oracle and usage oracle. It excludes later compact publication, secondary
Python-emitter caching, Genius oracle and unfinished Disney native/unit-core work. Do not claim its Python
suite passes until the final report is observed. This new run contributes host
load during ongoing feature/benchmark work.

The earlier `...-a` launcher failed discovery before running tests because of an
unnecessary `top_level_dir` for namespace Tests. That failure and its passing
build/smokes remain archived. The corrected launcher uses existing discovery
conventions. A short physical path avoids Win32 nested-path limits; a junction
would resolve back to the long path. Preserve both evidence directories.

## Accepted subsequent evidence

Paths here are relative to the external SPL artifacts root above.

- `python-emitter-thunk-20261123-a`:34 methods pass143.525280s, build/both
  smokes, zero failures/errors/skips/source drift. Archived old/new Python emitters
  execute direct Lean and disposable C checks; actual group builds114->2, equal
  complete values. Twelve same-process input/opening variants retain fresh cells.
  No timeout increase. Current20ea/a516/673 pins apply to the next Disney attempt.
- `publication-whitespace-20261123-a`:20 methods pass44.747635s plus94-job
  build/both smokes. Complete result.json is compact; review field files remain
  indented. All values/trace nodes and64MiB limit remain. Retained g trace size
  is65,841,102 pretty versus44,542,781 compact bytes, same17,832 nodes. Old AO
  baseline completed bundle loads with original marker unchanged. No source drift.
  Native Disney full acceptance is still pending after multiple retained failed
  source probes; that run used066/182/673 pins, before the secondary emitter fix.

- Emitter memoization: `emitter-thunk-checks-20261123-b` passes six methods/
  31 observations, including lazy/failure ordering and fresh per-call locals.
  `emitter-thunk-promoted-checks-20261123-a` passes38 methods in69.153263s,
  covering memoization8, indexed7, pure6 and mixed17. Generated current targets
  and library were deliberately regenerated from unchanged financial source;
  full94-job build, optional indexed target build and both smokes pass.
- Authorized offsets: `authorized-offsets-checks-8eac5174` passes37 combined
  oracle/module methods in481.859623s plus actual native publication/carry in
  103.920028s. Original paid80 remains80; original-rate reversal exposes20
  potential overpayment, with separate recovery authority. Three actual periods
  carry original history and claims. Final publication67,025,493 bytes has only
  83,371 margin under64MiB. No eight-period publication capacity is claimed.
- Civil days: `civil-dates-checks-67ea0b79` passes27 combined methods in
  107.193844s, with no source/core drift. Versioned supplied cells distinguish
  midnight, submicroseconds and23/25-hour days; no ambient/IANA timezone rules.
  State is empty. Reader/pool envelope labels are nonfinancial execution metadata.
- Disney repricing oracle: `merchandising-reprice-oracle-20261123-ec7a285a`
  passes26 independent checks. Q1/Q2 catch-up210, Q3new472.50/total527.50,
  actualpaid1310, dated/as-known history and Q4exactlyonce/preview controls are
  independently specified. Native source has not passed acceptance yet.
- Root inventory consistency: four matrix checks pass. Current bounded matrix
  has34 rows,30 witnessed variations, four gaps and45 selectors. These are not
  the full C1 denominator or a new combined45-selector campaign.

AO's first37-method run retained two honest64MiB publication failures. Original
anonymous period records embedded in instance identifiers caused90.8MB results.
Exposing the existing unique original `source_case_id` as a transient wrapper ID
reduced the baseline result to27.9MB without dropping observations (one actual ID
observation was added). Original IDs were already validated unique. Failed run
`authorized-offsets-checks-482ad548` and diagnostic538ae40c remain archived.

## Performance facts and remaining work

The indexed-source experiment preserves the original source, old generated
output and old executables. Small tests pass72 old/new output/error/state
observations; 1,000-record logical trace reduces64,480 to11,527 nodes and
776,599,360 to128,745,489 expanded bytes. Tiny/empty cases can grow; no universal
improvement claim is justified.

The pre-memo indexed10,000-record target timed out at60s. Its audit also failed
fixed guards. The old source target passed full financial controls in0.237s;
no completed audit/reader/state or successor results were credited. Diagnosis
found generated definition closures were recomputed on later references.
The emitter repair uses `Thunk (Eval Value)`/`Thunk.mk`/`.get`, keeping original
force positions and fresh function/loop scopes. Actual isolated C wrapper counts
show old114 to new2 group builds on an8-title fixture. Pinned official Lean4.35
sources document caching. No Runtime/Core/proof/checker/IR change was required.

Post-memo probes are now retained in
`rr03-indexed-postmemo-{100,1000,10000}-20261123-a`.100/1,000 pass, including
byte-identical prior indexed audit wires. The single10,000 probe passes complete
reference/current-original/indexed target financial controls: indexed calculation
0.323204s versus the previous60s timeout. Required audit still FAILS in21.706706s,
with RESOURCE_LIMIT empty financial/state header and COMPACT_EXPANDED_BYTE_LIMIT.
The14,237,800-byte prefix is unconsumable; reader and all4/8 successors did not
execute. Fixed60s/64MiB/256MiB/1GiB/100k guards remained. Source/core pins stayed
stable, background813-suite load is disclosed, and no SLA/percentile is claimed.

## Current verified process windows

- Main regression e80024d: exec26641,887 methods, still running at the last
  verified poll. Its isolated old snapshot excludes subsequent publication,
  Python-emitter, Genius and unit changes. Do not restart merely because logs
  are quiet; poll this handle/final verification.
- Disney cf96f81d: COMPLETED PASS, exec78966 ended,20ea/a516/673 sources stable. Six actual
  completed/loader-validated bundles have passed independent and separate
  Python-emitter controls: baseline41,187,283; Q1 10,147,582; Q2 24,742,448;
  Q3 41,925,067; Q4 55,194,678; preview32,985,527 bytes. Q4 catch-up/new
  recognition0, preview closing_state empty; full39-method cohort passed811.007496s, zero failures/errors/skips/source drift.
  Actual six-bundle phase213.527360s, total1024.575564s. Only README evidence
  changed after the run; code/test/descriptor/template hashes remain identical.
  This is selected bounded C04/trigger-period acceptance, not generalC13replay.
- Failed Disney84046c1c retained the180s Python-driver timeout before39 tests.
  After c35f274, separate followup331b80a7 passes11.592059s at the same180s cap.
  Failed9e70aa8b retained a mechanical carry-helper unknown movement field.
  Corrected actual carry JSON-round-trips the validated cell and removes only
  output movement. Pure helper followup5970c3c9 verifies all three transitions,
  unchanged previous results/artifacts and exact actual prior_result_ref.
- Isolated units: initial clean98-job build/indexed22/both smokes plus11 core
  methods pass, and consumer b7594415 passes25 methods/nine native comparisons/
  36 Lean commands in68.728105s without source or artifact drift. Baseline unit
  pins were a982a108/d63a8fc8/a7e4f8e5, distinct from main. Source remains
  uncommitted while trace strengthens guards, integrates verified upstream
  encoder/Python-memo patches, replays actual old state and prepares broad checks.
  The old abee-produced Download state now replays to100.5 with earned0.375,
  unchanged495808ae unit identity. No final unit release/cherry-pick credit yet.

## Delegated ownership and next steps

- `validation_matrix`: finished AO/civil cohorts; completed the atomic C1 variant
  catalog, completed native Disney acceptance; next Genius source after checkpoint.
  Root reviewed78 stable semantic IDs:75 required C1, two supporting, one unselected alternative; nine engineering entries are a separate axis. This is a planning denominator, not passing evidence or72tasks/195rows/testcount.
- `validation_generated`: Genius basis-reserve oracle frozen32 methods with five
  actual serialized periods, artifact `basis-reserve-oracle-20261123-5ed65f08`.
  Native source remains pending; excess-vintage returns remain an explicit source
  gap. Its isolated unit consumer files are frozen with passing evidence; trace now
  integrates the complete unit candidate. The agent now owns NEW main mutation
  generator/runner/tests/design files for B-VAL-MUTANTS, with finite independent controls. That task is now frozen/accepted: initial4
  and strengthened6 case phases preserve exact sources/policy/mutants, four
  actual backends and honest class/stage distinctions;17 isolated tests plus
  seven-process native-negative followup pass. The agent now authors independent
  C10 entitlement-burden controls from original receipts/terms/paid evidence,
  while a different source author will implement them later. No core edits.
- `validation_trace`: owns the isolated usage-unit compiler/context/IR/runtime/
  codec/emitter implementation. Its baseline archive `usage-units-baseline-20261123-a`
  retains39 files, nine raw v1 IRs, old namespace controls and actual base quantity
  state carry. Initial targeted checker/parser/linker builds pass; full alignment
  and extension acceptance remain pending. Root required generic feature-catalog
  admission instead of spreading a single Hour-name/Boolean switch through code.
  Shared main wrapper now uses20ea/a516/673; native compiler sources remain unchanged during Disney native work.
- Root: independent usage conversion controls now pass8 methods from an isolated
  source snapshot, `usage-conversion-oracle-20261123-642e47f0`; this earns no
  compiler/native/codec/state credit. Integrate evidence/backlog, review unit/context compatibility, maintain
  stable shared core, inspect full regression, create verified checkpoints.

An isolated short physical worktree `C:/spl-units-9f9` on
`feature/spl-usage-time-c1` starts from9f9cf31. Unit implementation is now authorized in this isolated checkout only, with
baseline freeze before owner/context/IR changes and no FX. The shared main wrapper
now stays20ea/a516/673 for financial native runs, with native Lean unchanged. The final plan is committed in
8892329, which also fixes the stale standard-library guard. Embedded Python has a main-repo
`._pth` entry, so isolated launchers must explicitly insert their checkout path
before imports and record loaded module paths; cwd alone is insufficient.

The non-FX [unit plan](unit-conversion-extension-plan.md) requires explicit
owner-local admission, old namespace/IR/state compatibility, generic exact
relation checks, and an independent baseline before implementation. Shared main sources
are stable at20ea/a516/673. Do not change it during another native freeze.

Remaining work is in the73-item backlog, including separate C10 burden,
cent allocation, sourced reserves/gates/repricing, replay and schema/transport/
diagnostics/reporting variants. The backlog records25 complete items; task
counts do not measure language coverage. Whole-compiler proof, professional
approval and external custody remain separately scoped obligations.
