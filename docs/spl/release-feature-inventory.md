# Implemented SPL features and verification scope

This inventory defines the starting scope for general certification. It records
the executable language at commit `8f47311` and identifies the new work in
this phase separately. The first-release goal is certification for any
well-formed contract composed of these implemented features, including
combinations absent from the existing fixture corpus. The pinned language,
core and schema versions are `spl/0.1-draft`, `spl-core/0.1-draft` and
`spl-data/0.1-draft`. The reference also describes proposed language features.
This inventory takes its support claims from the implementation. [Language
reference](language-reference.md) · [Native entry points](../../SPL/Main.lean)

## Authored forms

| Feature | Implemented behavior |
| --- | --- |
| Core source | One versioned `schedule`, with optional `uses` declarations for implemented owner-scoped features. ASCII identifiers, JSON-escaped strings, decimal and integer literals, `USD` literals, Boolean literals, `date` literals, comments and explicit punctuation. The lexer and parser report located diagnostics and enforce resource limits. |
| Core schedule declarations | Typed `input`, typed `opening … from` with a unique state alias, `define` with optional type and `citing` metadata, `require … else` with a diagnostic code, uniquely named `emit` outputs, and typed `closing` declarations. Every opening has exactly one matching closing. A payable record must expose agreement, participant, period and pool or asset scope. |
| Readable source and bindings | `Participation Schedule for …`, indented statements and one explicit `Bindings:` footer. The footer gives `Schedule` and `Using`, may include `input`, `opening`, `require` and `define`, and can register `Bind`, `Settle`, `Iterate` and `Field`. Alias resolution uses a longest-match pass, protects quoted contents, and groups substituted expressions. |
| Readable financial expressions | `is` and `are` definitions, the `less`, `plus` and `of` forms, exact percentages, complete-expression `the lesser of … and …` and `the greater of … and …`, plus checked core expressions. `citing` retains an authored rule reference. |
| Readable control and output | `Require … or fail`, `If … / Otherwise` with aligned definitions and matching citations, `For each` with a registered iteration and final `Report by`, `For settlement with` with a typed participant, `Closing`, and `Report` by expression or registered columns. Multiple or nested settlement headings have hygienic participant bindings and retain the ordinary uniqueness rules for finance names, outputs and state writers. |
| Readable policies and periods | Unique top-level `Incorporate policy "id@revision"` records provenance. Canonical execution separately resolves registered policy identities and checks their declared implementation. `Account for each calendar quarter` requires an explicit period binding and checks a Gregorian half-open quarter. The heading operates on that period's input. |
| Authored attribution | Native expansion records origin spans for generated lines. Parsed Readable nodes and frontend diagnostics retain authored statement spans, including separate branch expression origins. Policy links, citations and rule identities participate in attribution where the selected profile promises them. |

The closed Readable grammar and footer restrictions are documented alongside
the implementation. Core expressions embedded in a Readable schedule remain
within certification scope. [Readable grammar](readable-language.md) · [Core
parser](../../SPL/Parser.lean) · [Readable expansion](../../SPL/Readable.lean) ·
[Static checking](../../SPL/Check.lean)

## Types, expressions and operations

| Feature | Implemented behavior |
| --- | --- |
| Scalar and opaque types | `Bool`, `Int`, `Nat`, `Ratio`, `Rational`, `Text`, Gregorian `Date`, explicit-zone `Instant`, and `Id<Kind>`. Distinct ID kinds are preserved in checking and linking. Typed ID admission uses the current nonempty ASCII profile. |
| Monetary and dimensional types | Exact `Money<USD>`, `Quantity<U>`, and `Rate<U,USD>`. `spl.units/1` admits `Download` and `UsageMinute`. Opt-in `spl.usage-time/1` adds `UsageHour` and `convert_quantity` with the explicit `spl.usage-time/1:minute-hour` relation. Feature permissions are lexical to the schedule or module owner. Runtime meanings allow tagged values to pass through linked interfaces. Dimensional arithmetic uses the checker’s operand combinations, including quantity multiplied by a matching rate, ratio scaling, and ratio results for like-dimension division. |
| Structural and collection types | Inline records, `List<T>`, `Option<T>`, `Tuple<…>` with at least two components, and `Map<K,V>`. Ordered map and fold keys use `Bool`, `Int`, `Nat`, `Date`, `Id<Kind>` or tuples composed of admitted key types. Named records provide the built-in schema listed below. |
| Values and binding | Name references, field projection, record and list literals, contextual numeric literals, expected types for empty lists and `none`, immutable definitions, finite dependency resolution, and checked binder scopes. A lambda binds one item inside its supported collection call. |
| Scalar operators | Exact arithmetic `+`, `-`, `*`, `/` for the admitted type combinations, signed unary negation, `not`, ordered scalar/key comparison, equality and inequality, `abs`, `min`, `max`, and `quantize`. Division can fail on zero and subtraction of `Nat` is outside the admitted operator profile. `quantize` requires a positive same-dimension quantum and a literal `floor`, `ceiling`, `toward_zero`, `half_even` or `half_away_from_zero` mode. |
| Dates and time | `instant` converts explicit-zone RFC3339 text with exact fractional seconds. `in_period` checks half-open date membership. `is_calendar_quarter` checks a Gregorian quarter. `add_calendar_months` takes a `Nat` month count and the `clamp_day` or `reject_invalid_day` policy. |
| Control flow and failure | Lazy `if … then … else`, short-circuit `and` and `or`, and top-level or local `require` assertions. `choose unique` selects a unique applicable arm. `choose registered unique` and `choose priority` check rule IDs and evaluate predicates in ID order. Priority uses the greatest matching integer rank. Ties or a missing applicable arm without a fallback fail. A selected body or fallback alone is demanded. |
| Lists and iteration | `filter`, `map`, typed `sum`, stable `sort_by`, `append`, `concat`, and `for each … yield` with local definitions and assertions. A typed sum has a zero for its result type, including an empty input list. |
| Options and tuples | `none`, `some`, `is_some`, `get_or` with a lazy fallback, `require_some` with an explicit failure code, `tuple`, and `tuple_get` at a checked natural literal index. |
| Indexed collections | `make_map`, `lookup`, `entries`, `group_by`, `join`, and `left_join`. Map keys are ordered and duplicate keys fail. Grouping retains row order within each group. Joins preserve matching multiplicity and left/right input order. An unmatched left row has an empty right option in `left_join`. |
| Stateful list processing | `fold` is a finite strict left fold over list order. `ordered_fold` checks all projected identities and ordering keys before running the first step, rejects duplicate identities independently of dates and rejects tied ordering keys under the explicit `ties "reject"` policy. Steps can contain local definitions and assertions and must return the same state type. |

The built-in record types are `Period`, `SVPicture`, `SVReceipt`, `SVCost`,
`SVPostingCost`, `SVPolicy`, `LGReceipt`, `LGCost`, `LGPolicy`,
`LGHurdleAttestation`, `LGGateHistoryAttestation`, `SettlementScope`,
`AdvanceIssue`, `AdvanceEvidence`, `ReserveVintage`, `ReserveMovement`,
`ReserveEvidence`, and `PaymentApplication`. Their fields and exact types are
defined by the static checker. Generic contracts can also use inline schemas.
[Type and builtin checking](../../SPL/Check.lean) · [Unit catalog](../../SPL/Dimensions.lean) ·
[Runtime primitives](../../SPL/Runtime.lean) · [Fold and list operations](../../SPL/Fold.lean)

## Linking, artifact paths and reporting

| Feature | Implemented behavior |
| --- | --- |
| Function linking | Versioned source modules with typed exports and exact transitive imports. A linker manifest binds call aliases to exports. Module bodies can contain inputs, definitions and assertions. Interface matching, collision detection, acyclic imports and nonrecursive calls are checked. Features and typed linked signatures retain the defining owner's context. |
| Typed IR | `spl-ir/0.1` and feature-extended `spl-ir/0.2`, including types, node identities, spans, citations, explicit collection binders, rule alternatives, calls and, in the extended format, owning feature sets, unit and relation pins and signatures. Independent IR validation is a structural check on annotations and shape. |
| Execution and compiler entry points | Native `check`, `expand`, `ir`, `interpret`, `compile` and `compile-library`. Native interpretation yields value/error results and an observation trace. `compile` emits standalone Lean over typed bindings and `compile-library` supplies an embeddable settlement calculation. Python supplies an independently implemented frontend, evaluator and emitter for differential testing. |
| Typed admission | The standalone binding envelope supplies named inputs and openings. Native decoding checks exact fields, strict JSON, canonical exact-number representation, dimensions, currency, dates, timestamps, IDs and recursively typed collections. There are narrower existing identity checks on certain named event/evidence records. Contract-level requirements can already use authored assertions. |
| State and calculated output | A period accepts explicit openings and produces emissions and candidate closings in its pure settlement result. The pre-phase multi-period harness advances outside the artifact using publicly reloaded predecessor state. A source `fold` already advances state within a single settlement expression. |
| Operational transport | Bounded legacy canonical package profiles and the generic `spl-module/1` interface cover dependency identity, parameter approval, typed/opening inputs, declarative package constraints, output roles, reconciliation, period/cutoff, subsequent state and semantic digests. Array and compact audit/publication paths apply their own integrity, compatibility and resource checks. |
| Financial policy library | Existing schedules and modules compose the language to implement the qualified participation, ordinary royalty, advance, reserve, tier/guarantee, deduction, correction, allocation, reporting and other financial cases. The financial coverage ledger catalogs policy variants and their independent controls. Their presence in the library does not make each a new language primitive. |

The interpreter, emitted Lean executable and public canonical reader each have
their own observations and limits. Keep traces and source locations in the
contract claim where promised, and associate process limits and physical bundle
integrity with their deployment path. [Native linker](../../SPL/Link.lean) ·
[IR definition](../../SPL/IR.lean) · [IR validation](../../SPL/ValidateIR.lean) ·
[Native emitter](../../SPL/Emit.lean) · [Native bindings](../../SPL/Bindings.lean) ·
[Canonical module interface](module-interface-v1.md) · [Publication contract](artifact-publication-design.md) ·
[Compact publication](compact-publication.md) · [Financial coverage ledger](c1-coverage.md) ·
[Bounded release evidence](release-checkpoint-2026-11-25.md)

The generic module registry recognizes `spl.core/1`, `spl.instant/1`,
`spl.priority/1`, `spl.tuple-map/1`, `spl.group-join/1`, `spl.fold/1`,
`spl.modules/1`, `spl.calendar-months/1` and `spl.quantities/1`, with the
owner-scoped `spl.usage-time/1` extension. The capability list describes
requirements of the registered source and its interface. [Registration checks](../../spl_compiler/modules.py) ·
[Source-owned time extension](unit-conversion-implementation.md)

## Existing evidence and release criterion

| Evidence at the baseline | Scope |
| --- | --- |
| Lean arithmetic preservation | `SPL.Core.lower_correct` covers its intrinsically typed arithmetic/control-flow expression domain. `numericBinary_correct` and `numericUnary_correct` connect the scalar helpers on the generated path. |
| Lean pilot certificate | Two exact Readable source files and the pinned rounding module. It proves preservation of settlement outcome and empty closing state for every exact rational pair and connects the generated standalone entry to that settlement. |
| Lean admission lemmas | Distinctness of the supplied IDs returned by the pilot admission and distinct disbursement IDs for successfully checked advance-issue rows. |
| General compiler and financial tests | Parser, checker, linker, IR validation, interpreter and emitter tests, plus conformance, mutation and independent original-fact controls. Publication, public reload and predecessor carry have qualified finite witnesses. |

Full release certification requires a reusable proof construction over the
implemented grammar and type rules above. Track the proof coverage for each
feature family and the observations it supports. Require each well-formed
in-scope contract to compile and obtain a certificate within the declared
development and execution budgets. The feature test matrix is a witness
inventory. The proof construction must also handle compositions beyond its
examples. [Arithmetic lemmas](../../SPL/Proofs.lean) · [Pilot proof](certification-pilot.md) ·
[Admission theorem](../../SPL/RoyaltiesAdmission.lean) · [Feature test matrix](feature-test-matrix.json) ·
[General verification design](general-verification-design.md)

## Additions in the verification phase

- `compile-series` emits the existing settlement step with an in-artifact
  period driver. The kernel checks ordered success, exact state carry and
  first-failure semantics of the pure loop. [Series proof](../../SPL/Series.lean)
- `spl-comparative-certificate/1` checks native source/IR correspondence with
  the independent Python frontend and Lean equality of the emitted settlement
  and entry point against the Python-generated Lean reference. The independent
  frontend and shared runtime meanings remain dependencies of that claim.
  [Comparative verification](../../spl_compiler/verification.py)
- The linkable validation examples supply separate versioned `SVReceipt`
  and `SVPostingCost` feed policies, a Readable consumer and rejection
  controls. A Lean theorem covers half-open membership over the actual
  emitted date-guard operations. [Validation appendices](../../cases/validation/README.md) ·
  [Admission soundness](../../SPL/ValidationProofs.lean)
