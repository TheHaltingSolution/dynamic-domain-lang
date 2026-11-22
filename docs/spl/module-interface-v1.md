# Registered module package interface v1

`spl-module/1` is a separate canonical profile. The existing SV incurred,
RQ-07 posted and LG cleared profiles retain their previous schemas, projections
and policy compatibility checks. They have not silently migrated to this profile.

The published machine-readable contracts are
[`spl-module-descriptor.schema.json`](../../schemas/spl-module-descriptor.schema.json)
and [`spl-module-package.schema.json`](../../schemas/spl-module-package.schema.json).
The implementation is [`modules.py`](../../spl_compiler/modules.py). Descriptors
contain exact file/module pins, typed ports and a finite constraint vocabulary.
Economic expressions and function preconditions remain checked SPL source.

## Registration and replay

A registration contains a namespaced ID, immutable revision, registry-relative
descriptor locator and SHA-256 of the descriptor bytes. The descriptor separately
pins its calculation source and readable economic policy. Changing source or
policy bytes requires a different content registration, even if the version label
was accidentally retained. Conflicting pins for the same ID/revision in one
closure fail. Cycles, missing exports, ambiguous import names and unsupported
capabilities fail before calculation.

Imports have exactly this shape:

```json
{
  "module_ref": {"id": "library:calculation", "revision": "1", "locator": "library/descriptor.json", "sha256": "<64 lowercase hex digits>"},
  "alias": "fees",
  "symbols": [{"export": "calculate_fee", "local": "selected_fee"}]
}
```

An exported function declares `name`, typed `parameters`, `result` and the source
`definition` implementing its result. Function dependencies use pinned source
text in a linking manifest; dependency resolution alone is not functional linking.
The source compiler checks imported functions and their calls. Imported argument
domains and other runtime descriptor constraints are currently rejected: express
those preconditions as source `require` assertions. Imported libraries cannot own
state slots. A root canonical descriptor can declare package constraints and
explicit state ports.

Both original and readable root sources require the descriptor's readable policy
pin and supplied decisions. The decisions must exactly cover every policy in the
transitive module closure and match the owning policy's ID, revision and recorded
review status. A supplied `proposed` synthetic decision remains proposed; neither
calculation nor the wrapper supplies professional approval.

## Ports, scope and constraints

Port roles are `input`, `parameter`, `evidence`, `opening`, `result`, `detail` and
`reconciliation`. Input, parameter and evidence values occupy separate named
objects in the package. Undeclared or missing ports fail. Parameter domains can
specify exact numeric bounds, finite choices and collection cardinality. A
`methodology` parameter participates in method identity as well as terms identity;
other parameter changes affect terms identity. The registered module and policy
pins always participate in method identity.

`semantic_run_digest` excludes the invocation label `manifest.run_id`. Changing
that label alone leaves calculations, logical trace and candidate closing-state
lineage unchanged. Scenario, period, cutoff, mode, inputs, openings, actual terms
and all module/policy/evidence dependencies remain in the semantic closure. The
full result envelope retains its invocation label and has its own result digest.

Types use the compiler's type AST. Descriptor-local named structural schemas
expand to inline `Record` types without adding entries to a global registry.
Tuples, maps and nested records retain their compiler transport. Explicit
`Id<Agreement>`, `Id<Participant>`, `Id<Pool>` and `Id<Asset>` values are checked
recursively against the run's declared scope, including result and state values.
Native IDs retain the current ASCII profile. Named dimensions document the
meaning of each port; data relationships are enforced by typed scope and explicit
constraints rather than inferred from a contract name.

Constraint kinds are `unique`, `references`, `member_of`, `equals`,
`conservation` and `evidence`. Paths are dotted object fields; `*` traverses an
array. They cannot execute expressions. Targets can reference package values or
`dictionaries.<name>`. Constraints on `outputs.<port>` run after evaluation and
before finalization. Exact conservation has zero tolerance. A required evidence
constraint requires at least one matching supplied event, a registered approval
reference, an evidence reference and `observed_at < cutoff`. Equality with the
cutoff remains excluded. Other conditional economic evidence belongs in checked
source assertions.

The required manifest resource profile is `{"max_input_rows":100000,
"lean_timeout_seconds":180}`. Input rows count top-level array values separately
in inputs, parameters and evidence, plus arrays in structured state-cell payloads;
nested records and their fields do not add rows. `input_statistics` reports the
category counts and total. Additional transport guards permit at most 1,000,000
nested array elements, 1,000,000 scalar fields and 128 levels of nesting. These
guards are not measured throughput claims and use a different denominator from
the legacy profiles' facts-plus-evidence guard. No guard truncates data. The
180-second timeout applies to each native process invocation. No additional
intermediate-collection or trace-capacity guarantee follows from this manifest;
compiler/runtime guards have their own explicit scope.

## State and finalization

Each declared opening has exactly one supplied cell and one authoritative closing
writer. The canonical state key is the compact sorted JSON object containing the
slot's declared key fields. Keys must include agreement, participant, pool and
purpose, with an optional vintage dimension. Cells retain their purpose, scope,
unit, scenario, provenance and boundary; history-required slots also require an
exact prior-result reference. A period starts at the opening boundary and ends
at the candidate closing boundary.

Money state uses its currency unit and the declared `net_change` movement.
Structured state uses unit `structured` and movement `transition`: the audit
retains opening and closing payloads without inventing monetary subtraction.
Nested money values are converted back to tagged input transport for a successor
run. An external orchestrator supplies the next period and original opening or
successor lineage; the wrapper does not invent a replay authorization.

Native interpretation and emitted execution must agree with the reference
evaluator on status, emissions, closing state and diagnostic codes. Registered
output ports and types, declared output constraints, Boolean reconciliation ports,
closing writers and dependency pins are checked before finalization. A final
success exposes candidate state; a preview exposes results and reconciliation
with no consumable state. A blocked result exposes no business results or closing
state. All calculations remain unissued; actual payments are supplied facts.

Named emitted values are in `result["results"]`. `statements` and `detail`
flatten one array level from their corresponding port roles. Reconciliation ports
retain names. Review bundles include `results.json`, the pinned source/policy/
descriptor closure, typed bindings, native artifacts when requested, diagnostics
and an envelope written last. This file publication is not a database transaction
or concurrency guarantee. Profile build pins include both machine-readable schema
files in addition to the compiler and runtime identities.

`policy_review` and `policy-review.json` retain the actual supplied parameter
values, their declared domains and methodology flags, and the corresponding
source declaration locations. A transitive module map includes every source and
readable-policy pin, declaration spans, exported definition/argument locations,
and readable binding/footer support where applicable. `function_sources` maps an
existing application-trace function label to its pinned exported definition.
These links support human review; they do not establish semantic equivalence or
approve the selected interpretation.

## Cedar synthetic witness

[`priority-rates`](../../cases/modules/priority-rates/) registers different entities
and two participants without a new contract-name branch in the wrapper. Its
independent expectations are US 20, Canada 40 and France 0 on cash 100, split
equally between the two participants. Missing rules, a tied greatest priority,
the half-open effective end and unauthorized participants block atomically.

The checked-in package is deliberately unbound to an evolving build. Bind it to
the current implementation before running:

```python
from spl_compiler.codecs import read_json
from spl_compiler.lean_tools import ROOT
from spl_compiler.run import bind_package, run_package

package = read_json(ROOT / "cases/modules/priority-rates/package.json")
result = run_package(bind_package(package, ROOT), ROOT)
assert result["diagnostics"] == []
assert [row["earned"] for row in result["statements"]] == ["20", "20"]
```

`Tests/test_modules.py` covers the generic interface and registered witness.
These are synthetic calculation and integration checks, not proof of a wider
commercial platform, a historical settlement, or the complete C1 target.

## Exact timestamp compatibility repair

Canonical `codecs.instant` now returns the exact ordered `InstantValue` used by
the SPL reference implementation, rather than Python `datetime`. Fractional
seconds retain every decimal digit; equivalent explicit offsets compare equal
and serialize to normalized UTC. `-00:00`, leap seconds, invalid offsets and UTC
normalization outside years 0001–9999 are rejected. Lowercase `t`/`z` match the
native profile. Raw package strings and issued identities are not rewritten.

Host consumers requiring a civil day must use an intentional projection.
`instant_utc_day` preserves RQ-07's existing rule that date-precision posting
records require `posting_date < UTC cutoff day`. This is not a subsecond
availability rule. `Tests/test_canonical_precision.py` records the T10
counterexample and canonical/reference/native/generated cutoff checks.
