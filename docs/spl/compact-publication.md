# Opt-in compact canonical publication candidate

Implementation work is isolated on `feature/spl-compact-publication` in
`C:/spl-sidecar-a0`, based on integrated checkpoint `4a1300d`. This is a draft
candidate, not a release or a capacity acceptance. Main remains unchanged.

`run_package` and `run_module_package` accept `audit_profile="compact-v2"`;
the CLI exposes `--audit-profile compact-v2`. The unchanged default is
`array-v1`. Compact publication requires an artifact directory and the `lean`
or `compare` backend. A reference-only invocation cannot receive native credit.

The new marker is `spl-artifact-publication/2`; the result declares
`result_format: spl-canonical-result/2` and `audit_profile: compact-v2`.
The existing v1 loader rejects v2 markers. `load_completed_audited_result`
is the explicit v2 loader; `carry_audited_state` loads and validates the actual
publication before exporting existing canonical closing cells. Existing v1
envelopes and their loader/digest/state behavior retain their format.

The `trace` value is a reference object, never an empty array standing in for
an omitted audit. Its `spl-canonical-trace-reference/1` schema declares profile,
status, invocation-owned path, native wire format, exact wire/logical hashes,
wire/expanded/canonical byte counts, node/edge/payload counts, exact native head
hash, consumed-file pins and a declared compatibility view. Unavailable or
incomplete references may occur only with empty blocked financial/state fields.
Calculated and provisional results require a fully validated complete graph.
Preview results expose no consumable closing state.

The sidecar remains the existing lossless `spl-native-trace-stream/0.2` JSONL
format. Every original node, operand, result, type, status, skip, error,
dependency and detail reference remains logical audit data. Sharing and earlier
dependency indices are transport wrappers. `iter_audited_trace` returns the raw
native logical nodes without interpreting ordinary user records as codec tags.
The reference's view records the legacy wrapper's source-hash qualification
and policy scope, or the module wrapper's native identity view. The raw logical
trace hash always describes the native graph, independently of that view.

`iter_v1_compatible_audited_trace` explicitly reproduces the old wrapper's full
canonical-array view, including source prefixes, dependency/detail references,
scope and its historical recursive rational-record normalizer. That normalizer
is ambiguous for ordinary records named `numerator`/`denominator`; this optional
compatibility projection is not a universal lossless typed-value relation. The
raw iterator/hash remains authoritative, and v2 financial decoding uses checked
types rather than that historical projection.

`SPL.AuditMain` uses one checked/validated Program for the persisted typed IR,
`Emit.emitIR` output and interpreter outcome. It uses public native frontend,
owner-unit binding and interpreter APIs. No contract/demo dispatcher or new
financial formulas are involved. The exact private source, optional embedded
link manifest and binding bytes are consumed from invocation storage.
Existing wrapper code derives the canonical financial/state fields after
native/reference/IR agreement. Type-guided decoding follows checked output
types, preserving literal records that resemble rational/unit codec metadata.

Compilation uses the separately named `compiler1g180` profile: one child,
1 GiB sampled Windows working set and 180 seconds per compiler stage. It is
not a runtime envelope increase. The target cache pins exact consumed source,
link manifest, typed IR and emitted bytes; compiler/runtime sources, imported
objects/olean files, toolchain files, and actual Lake C/link flags. Failed cache
construction does not become a cache hit. The executed immutable cached target
and the retained invocation-owned executable must have identical hashes.

Calculation, audit generation, validation and publication workers retain
256 MiB sampled child working set, 60 seconds, 64 MiB wire/result, 1 GiB expanded
logical trace and 100,000 observations. The Windows sampler checks at 20 ms;
this is sampled child enforcement, not an OS-wide or parent-memory guarantee.
Parent source/projection preparation and descendants are separate scope.
No full expanded trace array is reconstructed for v2 publication.

Publication retains the existing private invocation and last-marker contract.
The v2 worker validates owned consumed bytes, complete graph and exact reference
before committing. Its process logs live outside the immutable invocation so
they cannot change a file after its manifest was committed. Failed/cancelled
worker completion invalidates its own invocation marker even if a child had
just finished committing. Other invocations' markers are not overwritten.
SHA256 provides consistency evidence, not authentication, external-fact approval
or a general compiler/trace proof. Concurrent writers and arbitrary power loss
remain outside the existing single-process publication contract.

## Retained baseline and draft probes

Current main a0 compiler/runtime baseline gates are retained externally as
`sidecar-current-a0-baseline-{100,1000}-20261123-a`. Both pass full independent
financial target, native audit and reader controls with unchanged dependencies.
The exact 100/1000 observation counts are 2,251/64,480; wire bytes
1,527,895/43,503,437; expanded native trace bytes 5,144,850/776,599,360.
Their logical hashes are respectively
`a9eff03a67af4a340167b440f1ad269a05ff94a03cde3b40605a4d207b3fff32` and
`2e22fd77147b96d987c36839796cdf3125171cbdf5d9daaa479a1b2a4100070b`.
Concurrent financial source campaigns were disclosed; timings are observational.
These gates alone do not publish canonical results.

Draft native literal, legacy SV and generic state probes are retained as
`sidecar-*-prototype-20261123-*`. Two initial module drafts failed publication
because Windows temporarily kept an executed owned image write-locked. Their
running markers remained nonconsumable. The corrected draft executes pinned
immutable cache bytes and retains a never-executed identical owned copy. The
generic draft then produces earned 20 and actual closing 5→25; the legacy draft
produces earned 33,000, payable 18,000 and recovered 15,000. These evolving-source
probes are not frozen acceptance or a 1,000-record canonical completion claim.

The old 20ea 33-run protocol remains dated evidence of a reconstruction failure.
The known 10,000-record graph-generation/expanded-data failures remain separate;
this work does not retry them or claim publication changes solve their limits.
