# Reusable policy and calculation module boundary

Proposed design for LD-02, 21 November 2026. This is an implementation target,
not an implemented import grammar, schema or policy approval mechanism. Retain
the current three registered profiles while adding this boundary incrementally.

## Problem and decision

The current `spl_compiler/policies.py` compares the complete ordered expanded
program with a registered signature, and `schema.py`/`run.py` recognize three
bounded package/projection profiles. This is a useful reproducibility gate for
those examples. It is not a reusable contract interface: a valid new method or
core-identifier rename may fail structural registration, even if the compiler
can execute it against experimental typed bindings. Exact signature equality
does not establish mathematical equivalence, economic truth or domain approval.

Introduce four distinct reusable artifacts:

1. **Interface module:** typed input, parameter, evidence, scope, opening-state
   and result ports, plus supported constraints and codec/schema dependencies.
2. **Calculation module:** acyclic pure definitions or first-order functions
   using those ports, core operators and pinned module imports. It declares its
   required capabilities and economic observations, without source-system paths.
3. **Method policy:** readable economic meaning, selected interpretation and
   evidence, parameter definitions, date/rounding/ordering choices, scope and
   references to the calculation/interface artifacts. LD-01 visibility applies.
4. **Run binding:** exact facts, parameter values, adapter/mapping versions,
   evidence, calendar/FX observations, opening snapshots, period and cutoff.

A module may export `allocate`, `tiered_share` or `recover_claims` with named
typed arguments. Initial function calls are first order and nonrecursive, and
the import/call graph is acyclic. Finite collection lambdas and folds retain
their independent semantics. There is no arbitrary Lean escape, host callback,
runtime plugin or dynamically interpreted legal text in the economic module.
Initially the compiler may elaborate imported definitions by hygienic expansion
to existing typed IR; separate linking/optimization is not required for adoption.

## Descriptor and scope contract

Before coding the descriptor format, publish a machine-readable schema for:

| Descriptor component | Required meaning |
| --- | --- |
| Identity | Namespaced module/policy ID, immutable revision and content digest; version label alone is insufficient |
| Compatibility | Surface/core/IR/schema versions, supported capability IDs, codec versions and runtime/toolchain dependency |
| Imports | Exact module revisions/digests, exported symbols and complete transitive dependency closure; reject cycles and ambiguous names |
| Inputs | Named structural schemas, finite code dictionaries, amount/unit/currency types, keys, nullability, cardinality and reference constraints |
| Parameters | Typed paths and domains; indicate which rates/dates/thresholds are run terms and which choices change methodology |
| Economic scope | Agreement, participant/role, work/group/pool purpose and effective membership; dimensional requirements on every port |
| State | Purpose, unit, scope/key schema, opening/closing boundary, vintage/history requirement and declared allowed movement kinds |
| Evidence | Interpretation and policy refs, required event/approval/attestation kinds, conditional demand and observation cutoff policy |
| Observations | Required result/detail/reconciliation ports, zero/blocked/provisional behavior and trace obligations |
| Review | Readable policy digest, decision IDs, evidence class, review status and named discriminating cases; never synthesize approval |

Exported records have explicit types; an unqualified amount is not a generic
balance. State slots cannot be silently widened from a work to a crossed pool,
or reused between reserves, prepayments and unpaid obligations. A module receives
the relevant opening cells explicitly and returns candidate closing cells and
movement records. A composed settlement has one authoritative writer for each
closing state key, or an explicit ordered composition that threads the value.
Imports cannot independently consume the same opening balance.

The interface checks structural compatibility. Authority to cross a pool,
deduct a cost or use an approval still requires the method policy and validated
evidence. A module name, matching record fields or a successful build supplies
none of that authority.

## Parameter changes versus method changes

Changing a declared rate value within its parameter domain creates a new run
terms identity; it need not require a new calculation module. If the rate is
written as an executable literal rather than an exported parameter, the module
bytes change and require a new revision. A new date selector, allocation method,
priority scheme, rounding point or gate-crossing convention is a method/policy
revision even when expressed by an existing enum or parameter type. The policy
must state the allowed variants and the review delta must show which was selected.

Mechanical alpha-renaming may preserve results while changing artifact identity.
Do not require general semantic-equivalence checking to register the new artifact.
Retain exact content pins for execution; use independent cases and typed interface
checks to assess a deliberate revision. Optional alpha-normalized comparison can
aid review but cannot confer economic approval or establish arbitrary equivalence.

## Canonical execution and registration

Canonical support means that a package can supply and validate the complete
declared interface and produce the required results/state/audit. It does not mean
professionally approved methodology. Experimental execution remains separately
labeled when a capability or physical profile is missing.

The next registry applies the same method/interface identity rules to readable
and original programmatic sources. Omitting an `Incorporate policy` phrase must
not bypass registration in a new canonical profile. Existing legacy profiles
retain their explicitly documented compatibility checks until deliberately
migrated; do not retroactively claim the new guarantees for them.

Implement a versioned descriptor registry keyed by exact identity, separate from
run values. Resolve its complete dependency closure before execution. Validate:

1. Syntax/types/capabilities and acyclic imports; no unresolved symbols or
   unsupported required schema fields.
2. Structural keys/cardinality/references and compatible unit/currency/scope.
3. The supplied economic policy, incorporated readable text, authority and
   conditional evidence, independently of schema well-formedness.
4. State lineage, cutoff, ordering/tie policies and single-writer state composition.
5. Reconciliation and atomic outcome publication for each connected settlement.

Use a reusable declarative constraint vocabulary for uniqueness, references,
interval membership, exact conservation, permitted movement kinds and required
evidence. Economic constraints beyond that vocabulary are pure checked module
expressions with traceable policy meaning. Do not implement a new Python
`if profile == contract_name` branch for each method or put foreign economic
code inside a JSON descriptor. Adapters may remain source-specific; adding an
ordinary method should reuse existing codecs and interfaces where appropriate.

Pinned modules are executable specification artifacts. The record of who
reviewed a synthetic policy, who approved a contract interpretation, and what
the compiler validated remains three different claims. Preserve the current
distinction between a final calculated reconstruction, unissued obligation and
actual payment evidence.

## Composition and workflow boundary

Build one acyclic dependency graph from facts, shared bases, modules and state
ports. Independent components may be evaluated separately. An allocation parent,
shared pool, gate or state key connects components; it prevents arbitrary
partitioning of their finalization. Sequential periods thread the same scoped
closing/opening state through an external run orchestrator.

Parallel scheduling is an implementation choice only when it preserves the
defined exact arithmetic, quantization, errors and logical trace. A fold over
competing claims cannot be replaced by unordered parallel updates. Concurrent
publication/retry safety belongs to the run service, not to the calculation
module's functional semantics. Do not claim database transaction safety from
pure evaluation or envelope-last file output.

## Incremental adoption and acceptance

1. Represent the existing three profiles through descriptors and reproduce their
   current reviewed interfaces and outcomes. Keep a compatibility path for their
   original source/registry; do not silently repin old packages.
2. Register a priority-rate method for a synthetic agreement with different
   entities and two participants using existing interface types. It must not
   dispatch by a familiar title, namespace or baseline amount.
3. Compose named allocation, participation and recovery modules with explicit
   state threads. Add a new method by descriptors/source/policy and cases, without
   adding a contract-specific branch to the generic wrapper or interpreter.
4. Exercise import-name collisions, cycles, incompatible ports, stale dependencies,
   undeclared parameters, missing evidence, duplicate state writers, unauthorized
   pooling and unsupported schema versions. Each blocks affected finalization.
5. Show that a parameter change affects only the intended rule/terms identity;
   a method change produces a new policy/module revision; old runs remain replayable.
6. Review main financial text, incorporated policies, actual parameters and
   support/expansion source locations together. Retain all executable dependency
   hashes, assertions, output wiring and closing ports in the run closure.

Future proofs can first relate hygienic module elaboration to the existing
finite-core semantics. Descriptor/codec validation, source text emission,
observation/trace preservation and orchestration each keep explicit boundaries.
Full proofs remain deferred under the current project plan; no new axiom or
unproved claim is introduced by this design.
