# Single-process artifact publication

Backlog item `B-AUDIT-PUBLISH` has executed acceptance for this finite scope.
The helper and both runner integrations are implemented. The frozen 19-method
helper/runner cohort passes in 44.280571 process seconds, including 24 actual
interruption stages, both native positive runners, serialized successor state
and precommit missing-population labels. This closes single-process publication
acceptance; bank execution, distributed/concurrent writers and arbitrary
power-loss behavior remain outside this contract.

## Earlier failure prevented

The earlier runners wrote several files into a reusable artifact directory
and wrote `result.json` last. Existing tests established that an ordinary failed
rerun overwrites monetary files with empty blocked results. An interruption
between writes is different: a previous successful envelope could coexist with
partially replaced new artifacts. Direct JSON writes can also be interrupted.
Writing an envelope last is insufficient when an old envelope remains valid.

## Invocation and commit contract

Each invocation gets a fresh short directory under the requested destination,
for example `.runs/abcdefgh/`. Calculation, bindings, source closure, native
outputs and final financial files are written there. Historical invocation
directories are retained, never silently reused or recursively deleted.

Before calculation starts, atomically replace the destination's authoritative
`completion.json` with a versioned `running` marker for this invocation. A
compatibility root `result.json` also becomes a blocked in-progress envelope.
Consumers must use the validated completion loader; loose files and root mirrors
do not independently grant consumption authority.

When calculation ends, finalize the result in the private invocation directory.
Flush referenced files, retain their relative paths, byte sizes and SHA-256
digests, and atomically replace `completion.json` with the completed manifest
only after those bytes exist. The manifest names the invocation, result path and
all owned artifact files. A completed blocked/preview result is inspectable but
does not permit financial state carry. Existing semantic result digests keep
their current meaning; publication IDs and filesystem paths are separate.

Root JSON mirrors can remain for current review tools. They are compatibility
views written before the successful completion marker, and must agree with the
immutable invocation. The completion loader reads the authoritative manifest,
validates relative path containment and all sizes/digests, decodes the result,
then checks that the marker has not changed during the read. The default
result limit is 64 MiB and the manifest limit is 8 MiB; the writer rejects an
oversized result before commit. This is a serialized-byte limit checked after
encoding, not a bound on writer peak memory. It returns no
consumable result for a running, absent, malformed, changed or incomplete
manifest. Its result/manifest memory bounds must be explicit; hashing other
artifacts should stream bytes.

If execution raises an expected calculation or validation error, publish the
normal blocked result with empty financial outputs/state. If publication itself
fails or the process is interrupted, leave the invocation uncommitted and raise
an explicit error. An artifact I/O exception after calculation must never return
the previous calculated result with only an added diagnostic. Failed finalizing
must not recursively attempt publication until it accidentally succeeds.

Atomic replacement uses same-directory temporary files, file flush and
`os.replace`. State the supported normal-process/crash scope precisely: file
flush and rename are not a theorem about arbitrary power loss or filesystem
implementations. Do not add signing, authentication or distributed guarantees.

## Integration boundaries

- Centralize publication in a reusable helper used by both `run_package` and
  `run_module_package`; finance remains inside SPL. Keep non-artifact return
  behavior and current successful semantic digests compatible.
- The settlement adapter now selects its unknown-payment status through
  `blocked_evidence_labels` before final publication. This diagnostic-to-label
  mapping admits only payment/funding/recovery evidence-status fields and the
  unknown labels `not_assessed`/`no_event_supplied`, only on unfinalized blocked
  results. It cannot assert complete evidence or change a successful digest,
  numeric output or closing state. No postcommit result rewrite is permitted.
- Retain original source/dependency pins and end checks. Publication does not
  solve source mutation or external-fact authenticity.
- Use short invocation names because this Windows workstation has existing
  path-length constraints. Do not introduce a second long semantic-digest path
  segment beneath already long artifact directories.

## Required checks

Start with a successful invocation, then interrupt a rerun before each monetary
file and before the final marker. The validated loader must reject the new run;
no stale envelope may expose mixed money/state. Verify a complete failed rerun
has empty statements/results/closing state and a matching completed manifest.
Tamper with one referenced byte, omit a referenced file, change its size, inject
a path escape or replace the marker during a read: each must block. A clean
rerun should create a different invocation while preserving its predecessor.

Exercise both generic and legacy canonical wrappers, positive and invalid
inputs, preview versus final state, source/policy artifacts, the settlement
missing-payment label and real serialized successor state. Retain actual
interruption evidence. Tests of the helper alone do not establish runner
integration. Then run relevant existing suites and build/smokes; record changed
compiler/module fingerprints rather than repinning historical issued packages.

## Verification record

`C:/Projects/Film_TV_participation_dynamic_DSL/artifacts/spl/publication-runner-checks-20261123-a/verification.json`
retains the 19-method result, zero skips, complete logs, relevant source/dependency
snapshots and 33 actual observation rows. They include 24 interrupted private/mirror/
marker stages, explicit publication I/O failure, failed reruns, preview carry
rejection, two native positive wrappers and native missing-payment evidence.
The metadata checks reject 33 forbidden mappings and leave successful results
unchanged. This remains separate from the current full regression obligation.
