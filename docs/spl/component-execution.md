# Dependency components and atomic roots

This is supporting engineering for `B-RUN-COMPONENTS`. It does not introduce
financial formulas or a distributed transaction service. A work item is an
already prepared invocation of one registered SPL root. Source preparation has
the same trust boundary as the generic module API. In particular, callers of
the C10 fixture must run its explicit preparation validator before freezing the
package. A dependency projection does not replace that validation or authenticate
original facts.

## Selected finite interface

`plan_components(request, registry_root, trusted_profiles=...)` derives a
deterministic plan from exact referenced bytes. A `spl-component-request/1`
contains named jobs with pinned package references, optional pinned dependency
profile references, and optional additional dependency edges. Job labels are
ASCII; business Text identities retain their original Unicode code points.

The operator explicitly selects a separate trusted dependency-profile registry.
The request cannot register its own profile or assert `reviewed: true`. A profile
is trusted authoring metadata tied to exact module, source, policy and import
closure pins. **Completeness is an authoring assumption**, not a theorem inferred
from checked types. Types and concrete packages are validated independently.
Absent/unregistered profiles conservatively connect the entire batch; stale
registered profiles or changed owner bindings fail validation.

Profiles select every matching row without eligibility filters or numeric
calculation. Closed resource kinds are pool, gate, allocation parent, correction
chain and cross-contract coordination. Structural keys retain an explicit
namespace, full scope and original identity. Automatically derived state-key
conflicts join across period/boundary changes. Explicit edges may add joins but
cannot remove them. Missing selected fields fail instead of becoming empty
populations. Ordinary fields resembling codec metadata remain ordinary data.

Each connected component must identify one distinct registered root package.
Aliases of the exact same root package execute once. Connected distinct roots
are held with `COMPONENT_COORDINATOR_REQUIRED`, without execution or state. The
caller must supply a genuinely coordinated root instead of fragments. The
planner does not merge financial inputs, synthesize source, select a winning
root or sequence partial root publications as a transaction. C10's existing
cross-contract coordinator is a concrete atomic-root mechanism.

Ordered fees, rounding, corrections, errors, state transitions and logical trace
remain inside that root's SPL. Cross-period requests sharing writable state do
not become independent by changing their boundaries. Existing completed
predecessor state is still validated through the canonical APIs/source checks.
Calculation/publication completion is not issuance: the C10 witnesses remain
`issuance_status=unissued`. Original issued facts, where supplied, retain their
own evidence/status and are not created by this orchestration.

## Execution and authority

`run_components` rederives the plan and checks all consumed references before
execution. Caller mutations of a serialized plan cannot choose components or
override the registered footprints. Execution uses immutable invocation copies
of referenced package/registry/profile bytes. The initial worker count is one.

An eligible component uses the existing generic canonical runner and its
explicitly selected audit profile. The canonical completion marker is the
entire component's authority. A failing coordinated root produces no partial
financial output/state; an independent completed component remains valid.
Preview remains nonconsumable. Existing v1/v2 canonical loaders and budgets
retain their meaning. No reference-only run gains native execution credit.

`spl-component-outcomes/1` is batch metadata, not a combined canonical financial
result. It records component membership, dependency reasons, dispositions and
owned completion references/hashes. It does not concatenate financial results
or traces. A batch can be partial. There is no whole-batch atomicity, parallel
capacity, concurrency-exclusion or distributed-transaction guarantee.

The selected native audit/runtime/reader/publication limits remain unchanged.
The compiler-only profile remains separately named. Coordinator parsing and
overall host memory must not be described as covered by a child-process bound.
Finite request/footprint bounds are explicit and do not imply that every
admitted count completes. No 100,000-record capacity or speed claim follows from
this implementation.

The initial coordinator admits at most64 jobs,4096 added dependency edges,
64 MiB of package bytes in total,100,000 distinct resource keys,16 KiB per
structural key, and8 MiB of resource/plan metadata. Exceeding a bound rejects the
plan rather than shortening an identity or dropping a row. These orchestration
counts are not canonical financial-fact or native IR-observation counts. Package
JSON preparation in the calling coordinator is outside the child-process256 MiB
scope; no overall parent/host memory guarantee is claimed.

## Required acceptance

Cover transitive joins for all five resource kinds, structural/Unicode identity,
permutation stability, cross-boundary state conflicts, unknown/absent/stale
profile bindings, caller-plan tampering, and mutable consumed references. Actual
native witnesses must compare a coordinated C10 root and an independent existing
root against independent original-fact controls and standalone whole outcomes.
Retain failed-component/independent-success, preview, interruption and stale
publication controls. Raw logical graphs and ordered source behavior must agree;
no financial source rewrite, raised guard or fabricated canonical result is
permitted to obtain acceptance.

The finite frozen implementation is qualified below. Main promotion and the
broader integration regression remain separate; the latter runs in an immutable
checkout without this new component code.

## API example

Bind and validate each root package using its existing preparation API, write
the reviewed bytes into the registry, then pin those exact package files:

```python
request = {
    "format": "spl-component-request/1",
    "jobs": [{
        "id": "CloseA",
        "package_ref": {"locator": "prepared/close-a.json", "sha256": package_hash},
        "dependency_profile_ref": reviewed_profile_ref,
    }],
    "additional_dependencies": [],
}
operator_registry = registry_root / "cases/component-profiles/registry.json"
plan = plan_components(request, registry_root, trusted_profiles=operator_registry)
outcomes = run_components(
    request, plan, registry_root, trusted_profiles=operator_registry,
    output=output_directory, backend="compare", audit_profile="compact-v2",
    workers=1,
)
```

The profile registry is an explicit operator argument. It is not accepted as an
extra request field. Request/profile/outcome schemas are closed and versioned.
Profile paths use lists of field names, nonnegative array indices and `*` for
all list members. Key fields choose `from: row` or `from: package`. No selector
filter, arithmetic, normalization, callback or code evaluation is supported.

`load_component_outcomes(output_directory)` validates the owned snapshot,
metadata and every referenced canonical component bundle. Each completion path
is relative to this exact batch invocation. Use the existing recognized
canonical loader/carry API at that completion file's parent directory. A
completed calculated state remains calculation state; this API does not issue
statements or create payment evidence. Resource/plan keys and copies of literal
records are structural JSON data, including names resembling codec metadata.

## Frozen finite evidence

`component-frozen-20261124-a` qualifies code/profile commit `18ea951` in the
isolated `C:/spl-components-c80` worktree. All44 methods pass in152.098009
seconds:19 component methods,8 legacy-publication methods,9 compact-publication
methods and8 runner methods. There are zero failures, errors or skips. All734
source pins and102 compiled pins remain unchanged; exact source ZIP, commands,
build flags, original facts, actual opening cells and four owned publication
archives are external. Default/indexed Lake builds and both smoke checks pass.

The actual native aggregate compares the coordinated C10 root to its independent
original-fact oracle, checks complete financial/state equality, and compares its
whole outcome and raw logical graph hashes with standalone execution. A separate
root returns its independently controlled20. Actual completed C10 Q1 cells and
prior references feed Q2, whose complete result/state match the original-fact
oracle. A paid-basis-unknown C10 failure leaves the independent20 root complete.
These are completed calculations/state carry, all `issuance_status=unissued`.

All123 bounded-process reports have their expected outcomes:108 successful
processes and15 explicit hostile-control rejections from the existing compact
publication suite. The terminal audit records their exact stages/codes, with no
unexpected failure, timeout, memory or output overflow. Measured child working
set peaks are88,064,000 bytes for `runtime256` and626,819,072 bytes for the
separate `compiler1g180` profile. This is not a parent/host memory bound or a
quiet-host latency result. Prototype tuple-admission/fixture failures and the
earlier native-development record remain preserved and separately pinned.

This evidence supports the selected finite interface under trusted profile
completeness and prepared-input assumptions. It proves neither completeness of
arbitrary authored footprints nor arbitrary contract correctness. Parallel
workers, uncoordinated connected roots, distributed publication/exclusion,
large-batch capacity and performance SLAs are outside this acceptance. Main
integration and source-owner review of additional financial profiles remain
explicit follow-ups.
