# Explicit usage-unit extension plan

23 November 2026. **Design for review; no core implementation is authorized by
this document.** The bounded target is `B-C02-CONVERSION`: declare UsageHour and
convert exactly 60 UsageMinute to 1 UsageHour. This is supporting engineering
under the existing non-FX scope. Native EUR and FX remain reserved by the later owner decision for a future
self-modifying compiler tool/skill demonstration after the other current goals.
No currency extension is implemented now; read [the owner sequence](ld03-owner-decision.md).
This non-FX slice does not prove financial inexpressibility in the current core.

The recommended change is one finite, immutable extension catalog; an explicit
source/module admission context; and one generic exact quantity-conversion call.
Keep `spl.units/1` exactly `{Download, UsageMinute}`. Do not add UsageHour to its
global list. Default public entry points retain base-only admission. New programs
opt into a versioned extension and retain its unit/relation identity through
checking, linking, IR, runtime, codecs and state.

## Inspected implementation boundary

The inspected shared checkpoint is compiler
`323f0d844fe11344713523f40d83d3b67d32d1376ce89da823875d72c2a297bc`, module
`7a2f98f64b70cb67e5b95ecdbb0fec85536d1cce3fb9423f1dfd42c9ed1772eb`, runtime
`673bb0fe936c48a60c1cf5a1a265fb1d1f9f3cd432f380ee9b3011b7729dace9`.
Source inspection and small Python probes were used; this design ran no Lean
build, changed no shared code and opened no currency gate.

| Existing boundary | Current behavior and required alignment |
| --- | --- |
| [Lean Dimensions](../../SPL/Dimensions.lean:5), [Python dimensions](../../spl_compiler/dimensions.py:10) | One fixed dictionary/list; admission is currently global. Preserve these base meanings. |
| [Lean type parsing](../../SPL/Check.lean:146), [Python type parsing](../../spl_compiler/checker.py:113) | Quantity/Rate reject unknown units; rate currency stays USD. Add explicit context-aware variants with base defaults. |
| [Schedule header](../../SPL/Syntax.lean:61), [native header parser](../../SPL/Parser.lean:472), [Python parser](../../spl_compiler/parser.py:111) | Source currently has no dimension-feature declaration. Add one optional metadata clause; old headers remain unchanged. |
| [Lean check](../../SPL/Check.lean:563), [Python check](../../spl_compiler/checker.py:635), [elaboration](../../SPL/Elaborate.lean:222) | Prepare admission once from source declarations, then thread it through every type/expression, including unused and empty branches. |
| [Native linker builtins](../../SPL/Link.lean:64), [native complete-export checking](../../SPL/Link.lean:183), [Python linker](../../spl_compiler/linker.py:15) | Builtin reservation and signature checking are currently global. Preserve each module's owning admission, including unused exports. |
| [IR Program](../../SPL/IR.lean:61), [IR serialization](../../SPL/IR.lean:175), [defensive type validation](../../SPL/ValidateIR.lean:35), [call validation](../../SPL/ValidateIR.lean:178) | IR carries no dimension admission. Add a validated feature/unit-definition snapshot for extended IR and preserve literal target/relation arguments. |
| [Native binding decode](../../SPL/Bindings.lean:164), [binding entry points](../../SPL/Bindings.lean:249), [Python value constructors](../../spl_compiler/model.py:39), [Python decode](../../spl_compiler/evaluator.py:42) | Context must reach nested types, value construction and incoming tags; changing only checker admission cannot work. |
| [Native magnitude/arithmetic](../../SPL/Runtime.lean:59), [typed sums](../../SPL/Runtime.lean:296), [Python arithmetic/zero](../../spl_compiler/dimensions.py:43) | Properly admitted Hour values otherwise fail the old global checks. New execution uses explicit context; existing wrappers remain base-only. |
| [Native execution gate](../../SPL/Interpret.lean:666), [native emission gate](../../SPL/Emit.lean:351), [Python emitter](../../spl_compiler/emitter.py:331) | Both public native paths already validate IR. Conversion must pass the same defensive gate and both emitter paths. |
| [Tagged codec constructors](../../spl_compiler/codecs.py:126), [codec serialization](../../spl_compiler/codecs.py:197) | Unit admission also occurs while constructing/encoding tagged values. It must use the owning context, never a mutable process flag. |
| [Descriptor scan](../../spl_compiler/modules.py:141), [closure resolution](../../spl_compiler/modules.py:227), [local type expansion](../../spl_compiler/modules.py:449), [link manifest](../../spl_compiler/modules.py:515) | Validate every local schema/port/export and used literal relation under its owner, before joining the closure. |
| [State type identity](../../spl_compiler/modules.py:471), [state validation](../../spl_compiler/modules.py:607), [dimensional interface contract](module-interface-v1.md:167) | Preserve old structural hashes; bind extension-unit state to the actual used unit definitions. |

Current probes confirmed that both source `Quantity<UsageHour>` and the default
quantity codec reject UsageHour as `UNSUPPORTED_UNIT`. An old linked module that
exports a function named `convert_quantity` currently succeeds and returns its
unchanged UsageMinute input. The existing Download state identity is exactly
`dimensioned:495808ae9a33038bcc29cf5b3fc3c7cff8da359bf26c7daf90e0e5852e171978`.
These are compatibility controls for implementation, not proposed new behavior.

## Proposed declaration and finite catalog

Use an optional source-header clause, with spelling finalized during review:

```spl
schedule Usage language "spl/0.1-draft" core "spl-core/0.1-draft"
  schema "spl-data/0.1-draft" uses "spl.usage-time/1" {
  input minutes: Quantity<UsageMinute>;
  input price: Rate<UsageHour,USD>;
  define hours = convert_quantity(minutes, "UsageHour", "spl.usage-time/1:minute-hour");
  emit "hours" = hours;
  emit "earned" = hours * price;
}
```

An absent `uses` clause means the existing base profile. The clause selects a
known immutable version, not host code, user-authored type definitions or a new
numeric factor. Parse it only in header position; avoid reserving an old legal
variable token throughout the language. Unknown/duplicate declarations fail.
Represent source admission as immutable data with a base default in both ASTs.
The registered descriptor must separately declare the matching feature; it cannot
silently enable an undeclared source feature.
This implication is one-way: a descriptor may record supported/transitive
capabilities without granting its owner a new source namespace. The owner's
header still determines its unit admission; a capability list alone is never a
replacement for `uses`.

`uses` must be contextual only between the existing schema string and the opening
brace. Freeze these old valid-name controls before changing either lexer/parser:

| Unchanged base fixture | Required result under the new compiler |
| --- | --- |
| `input uses: Ratio; emit "v" = uses;` | Same binding, value, spans and IR as before |
| A legacy function exported/imported as `uses`, called as `uses(value)` | Same linking and result; no header-feature interpretation inside a body |
| `input value: Id<uses>; emit "v" = value;` | Same typed namespace and original value |
| A descriptor-local structural schema named `uses`, including an unused export signature using it | Same local alias expansion and closure admission |
| A legacy schedule or ordinary record field named `uses` | Same parse/admission behavior; no global keyword reservation |
| `uses "spl.usage-time/999"` in header position | Explicit unsupported-feature rejection |
| Repeated/conflicting header declarations | Explicit duplicate/version conflict rejection, never last-wins |

The structural schema test is descriptor-local; it does not claim that the old
source checker admits arbitrary new bare type names. New header metadata must
not be discovered by searching input, field, function or type names for `uses`.

Proposed compiled catalog records:

```text
feature: spl.usage-time/1
base: spl.units/1                     unchanged Download/UsageMinute definitions
unit dictionary: spl.units.usage-time/1
new unit: UsageHour
unit family: usage-duration
unit meaning: exactly 60 existing UsageMinute
relation dictionary: spl.conversions.usage-time/1
relation: spl.usage-time/1:minute-hour
left: 60 UsageMinute
right: 1 UsageHour
directions: both, only by explicit calls
```

Choose immutable endpoint scales as the authority. Each admitted unit definition
has a dimension family, canonical base-definition ID and exact positive
`scale_to_base`: UsageMinute is 1 base Minute and UsageHour is 60 base Minute.
For every relation, validate the exact normalized equation
`left_count * left.scale_to_base == right_count * right.scale_to_base` in that
same base/family. The selected forward count ratio must equal
`left.scale_to_base / right.scale_to_base`; inverse conversion uses its reciprocal.
Positive counts, structural family labels and valid pins alone are insufficient.

In particular, a newly named/pinned relation claiming 59 Minute:1 Hour must reject
against the immutable Hour=60 Minute definition: 59 is not 60. Renaming the edge
does not create permission to contradict its endpoints. An equivalent registered
120 Minute:2 Hour relation is scale-consistent, but cannot replace the immutable
60:1 record under its existing content pin. Neither example adds a new accepted
catalog entry in this initial slice. A different physical meaning needs a
different unit definition and separately authorized profile, not another edge
over the same Hour identity.

Validate admitted endpoint definitions, matching physical family/base, unique
unit-name ownership, exact scale consistency and immutable ID/content pins. No
automatic graph search or implicit transitive conversion is needed. The same
known relation explicitly converts Hour back to Minute using its reciprocal.
No Download relation is admitted. UsageHour is a count of the selected usage
measure; this is not a civil-time/DST/calendar-month conversion.

The catalog can initially be pure compiled Lean/Python records with a canonical
payload/digest equality test. This avoids adding a runtime registry-file loader.
Future registered pairs require versioned data entries and acceptance tests;
the checker and conversion algorithm must not branch on the names UsageMinute
or UsageHour. That generic relation application and admission lifecycle are the
reusable mechanism. A dedicated `minutes_to_hours` builtin with another global
unit-list append would be a one-off implementation.

This is still a finite compiler extension. Implementing the new conversion
builtin requires reviewed checker, defensive-IR, interpreter, emitter and runtime
semantics and matching tests. The reusable part is explicit admission/ownership,
immutable definitions and generic application of a registered exact relation.
It does not turn arbitrary future operations into data or establish a plugin
compiler. A later operation with different semantics still needs engineering;
a later currency/FX feature additionally needs its own authorization and policy.

Keep existing `spl-quantity/1` envelope shapes: `{value,unit}` and
`{value,per_unit,currency}`. Admission is additionally selected by the explicit
versioned feature/catalog context. The codec alone grants no new unit. Existing
codec calls without a context still reject UsageHour. If implementation changes
the envelope shape instead, that requires a new codec version and is outside
this minimum plan.

## Generic conversion, contexts and defensive IR

`convert_quantity(q, target_literal, relation_literal)` accepts Quantity only.
Both strings must be compile-time literals. Infer the source unit from q's checked
type and the result unit from the selected opposite endpoint. Forward scale is
1/60 and reverse scale is 60. The relation must be admitted in this source/module
context; a dynamic Text parameter is not a versioned conversion authority.
The explicit inverse call from Hour to Minute succeeds at scale 60. Same-endpoint,
incompatible-family, unknown-relation and source/target-direction mismatches
fail; Rate/Money/Ratio are not retagged. No rounding occurs.

Reuse the existing checked/IR `.call` node and its literal-preserving validation.
There is no need for a new Conversion value type or a pair-specific IR constructor.
Add a literal-aware checker/runtime/emitter dispatch case that resolves the
generic catalog relation. Preserve ordinary tagged arithmetic: Minute+Hour and
Minute*USD-per-Hour still fail until an explicit quantity conversion occurs.
Rate<UsageHour,USD> works only under its admitted unit context; EUR stays rejected.
Money/Quantity, dimensional Map keys and unrelated operation-matrix changes stay
outside this feature.

Prepare an immutable `DimensionAdmission` from the declared known feature IDs.
Thread it through type parsing, recursive decode, constructor validation, typed
zero, arithmetic, conversion, encoding and output checks. Default-compatible
entry points delegate to base admission. New native targets embed their checked
context, rather than read a process-global switch. In Python, decoded tagged
values, `with_number`, `typed_zero`, codec encoding and Outcome serialization
must all retain/revalidate the owning context; constructor-only admission would
fail later on otherwise valid Hour results.

Keep lexical owner contexts through imports and application nodes. An extended root
must not legalize an undeclared Hour signature in a base-only dependency. Check
every registered signature, nested schema and export even if unused. Validate
each function body in its owner context; strict actual arguments remain checked
against that signature. Source-spelling permission is lexical, never a union of
closure dictionaries applied to every module.

Separately retain the verified closure's immutable runtime meaning universe.
A base root may receive an inferred Hour quantity from an extended callee, scale
or add it using existing same-dimension arithmetic, and emit it. For example,
`define h = library_to_hour(minutes); define doubled = h * 2.0;` may infer Hour
without any Hour spelling in the caller's source. Runtime arithmetic, value
reconstruction, serialization and inferred-output validation must know that
callee-owned Hour definition. They must not incorrectly reject it merely because
the caller has no lexical `uses` clause.

That meaning universe grants no permission to spell `Quantity<UsageHour>` in a
base input/opening/local annotation or invoke the new conversion builtin there.
The root may call an explicitly imported function whose owner has that feature;
it cannot acquire the builtin merely by reaching that function. Inferred result
contracts are checked against the actual checked expression/callee type and its
definition provenance. A descriptor containing Hour does not by itself license
an unrelated explicit source type, unused local schema or new source annotation.

The defensive IR implementation must preserve enough annotation-versus-inference
and contextual-type provenance to re-infer such results from real callee/parent
signature edges. Do not trust a caller-supplied `inferred` flag or use the whole
meaning catalog as lexical admission. Conversely, an ungrounded Hour annotation
in an empty list/none is not justified just because an unused dependency knows
Hour. Distinguish a legitimate expected type supplied by an admitted callee
signature from a forged standalone annotation. This separation is required
engineering, not an ambient union shortcut.

Extended IR needs a versioned admission snapshot containing known feature IDs,
unit-definition and relation IDs/content pins, and application ownership. Use a
new IR artifact version for that extended shape (proposed `spl-ir/0.2`). Preserve
`spl-ir/0.1` serialization for programs that use only the base profile. Defensive
validation reconstructs the admission from the compiled catalog, verifies pins
and ownership, reparses every type recursively, and re-infers conversion calls.
Never trust a supplied factor, target annotation or unit whitelist in an IR
payload. Both interpretation and emission reject forged extended types, including
empty/none and unselected-body annotations.

Freeze raw base IR0.1 exports from the existing LF source fixtures and compare
their exact bytes after implementation: version marker, object/array member
order, source spans, node IDs, decimal lexemes and type layouts. Do not add
`uses: []`, an empty admission object, null metadata or owner-context defaults
to old serialized records. A base program's new internal defaults must serialize
through its unchanged v1 layout.

Give the internal Program an explicit artifact-version/coherence check. A v1
Program carrying extension admission, unit-definition/relation pins, a conversion
call or extension-owner metadata must fail defensive validation before both
interpretation and emission. Never silently upgrade it to v2 or ignore the extra
metadata. A small serialized-artifact version/shape gate should likewise reject
extension keys in v1 metadata positions, even if their values are empty. This
is a shape/admission check, not a new general JSON-IR evaluation feature; the
current execution boundary is typed Lean Program values plus exported JSON.
Any artifact intake must use that gate rather than silently dropping unknown
members. Record a shape-only failure at its real preflight stage.

Concrete negative controls are v1 JSON with root `dimension_admission`, v1
application metadata with `owner_context`, and a v1 typed Program with a forged
Hour annotation hidden in an empty list/Option. Each must reject. Ordinary user
record fields called `uses`, `admission` or `owner_context` remain ordinary record
data in the existing Expr layout; the gate checks metadata positions and shapes,
not arbitrary economic field spellings. V2 also rejects missing/unknown catalog
pins, a different 60:1 definition under the same ID and a forged result unit.

The format decision covers the verified closure, including an unused extended
dependency. A base-only root may explicitly import an extended function that
returns only USD; its own type admission stays base-only, while the linked artifact
and root registration must declare the extended IR format. Keep old base-library
registrations valid inside that new root. Do not require a base library to opt
into Hour merely because its caller did, or erase an extended callee's ownership
because the root does not mention Hour in a port.

The mixed-context acceptance matrix is:

| Root / dependency case | Required behavior |
| --- | --- |
| Base root + base dependency with custom `UsageHour` function, `Id<UsageHour>` kind or descriptor-local record alias | Preserve the existing custom meaning and behavior; do not reinterpret it as a quantity unit |
| Base root + valid extended dependency returning USD, or the same dependency imported unused | Validate the dependency under its own feature; require a v2 root artifact/registration, but keep the root's own unit admission base-only |
| Base root receives inferred Hour from an extended callee and evaluates `h * 2.0` or `h + h` | Succeed using the callee definition from the runtime meaning closure; retain Hour output tags and provenance |
| The same root explicitly annotates `h: Quantity<UsageHour>` or calls the new builtin without its own feature | Reject the lexical use; inferred-value support did not grant source-spelling permission |
| That base root declares `Quantity<UsageHour>` after importing the dependency | Reject the root declaration; import reachability grants no root unit permission |
| Extended root + base dependency with an undeclared Hour quantity in an unused schema/export | Reject the dependency before execution; the root's permission does not repair its signature |
| Extended root + base dependency with a valid custom `UsageHour` record alias | Retain that alias under its owner; do not capture it as the new unit |
| Extended root + unused base export named `convert_quantity` | Preserve and validate the export in its base owner; no collision merely because the symbol is not imported into the root namespace |
| Extended root imports that legacy export locally as `convert_quantity` | Explicit collision rejection, resolved only by a deliberate local alias such as `legacy_convert` |
| Extended root imports it as `legacy_convert` and also calls the builtin | Both calls keep their distinct owner/semantics and return the independent expected values |
| One opting-in module declares both a local structural alias and a new unit named `UsageHour` | Require an explicit unambiguous namespace rule or collision diagnostic; never choose silently |

UsageHour must not become a globally reserved function, variable, ID-kind or
structural-type name. The one-module ambiguity control above concerns a new
opt-in, not a reason to reject an unchanged base module. Preserve the actual v1
resolver below; introducing positional type resolution is not a free cleanup.

### Actual canonical alias behavior to freeze

[`_type_ast`](../../spl_compiler/modules.py:449) currently recursively expands
descriptor-local aliases even inside `Id<...>` arguments. A same-owner schema
named UsageHour therefore turns descriptor `Id<UsageHour>` into `Id<Record>`
under the current `type_from_ast` behavior. An extension must preserve this
existing behavior, including rejection and state fingerprints. Do not silently
implement the more intuitive position-sensitive interpretation as part of units.
An owner-normalization fix, if desired, needs a separately versioned decision,
new old/new replay controls and explicit state compatibility/migration treatment.

Actual canonical reference probes at compiler
`abee14432a7a972b94a02795668d9ff8bbf97a5758f5558dc9178a7761e490eb`, module
`daf14a19e4b00bbb918583d76e73451322de8ecea1f9f1192dd3c404c1a06cde`, same runtime
`673bb0fe936c48a60c1cf5a1a265fb1d1f9f3cd432f380ee9b3011b7729dace9`, used a compound
input/opening `{marker:Id<UsageHour>,quantity:Quantity<UsageMinute>}` descriptor:

| Canonical v1 fixture | Observed current result / required baseline |
| --- | --- |
| No local UsageHour schema; source spells `Id<UsageHour>` | Calculated; typed marker stays `Id<UsageHour>` |
| Same-owner local UsageHour schema; source still spells `Id<UsageHour>` | `MODULE_PORT_MISMATCH`, empty trace and closing state; descriptor actually resolves `Id<Record>` |
| Same-owner local UsageHour schema; source spells the existing expanded `Id<Record>` | Calculated; original marker string and 2 UsageMinute state survive |

The first compound type's exact state unit is
`dimensioned:035d54d28564df0f1e648dff57028a59231fd29ebd0e90fd20749e327edf3352`.
The actual alias-expanded compound type's state unit is
`dimensioned:29742617b381396f64a215c88e7153b3b3dbf4a972f3b95168f5985aaca1a4be`.
Freeze both accepted payload/state baselines and the intervening rejection.
Accepting the rejected case or changing the accepted expanded kind/hash would
be a compatibility change, even if described as restoring intended namespaces.

These are actual generic canonical paths. The canonical
[`linking_manifest`](../../spl_compiler/modules.py:515) already expands aliases
before the raw linker consumes export signatures. A direct raw-linker probe
with unexpanded alias input is not evidence of a canonical alias-linking blocker;
that review concern was retracted. Preserve and test the real canonical
descriptor/manifest/linking route and its existing owner-specific expansion.

## Registration and namespace compatibility

The existing descriptor shape already permits capability strings and named
string-array dictionaries. The proposed new declaration uses:

```json
{
  "compatibility": {
    "ir": "spl-ir/0.2",
    "capabilities": ["spl.core/1", "spl.quantities/1", "spl.usage-time/1"],
    "codecs": ["spl-exact/1", "spl-instant/1", "spl-quantity/1"]
  },
  "interface": {
    "dictionaries": {
      "spl.units/1": ["UsageMinute"],
      "spl.units.usage-time/1": ["UsageHour"],
      "spl.conversions.usage-time/1": ["spl.usage-time/1:minute-hour"]
    }
  }
}
```

This is a focused fragment, not a complete descriptor. Validate actual used units
and literal relations, and also all declared entries under the selected extension.
UsageHour under `spl.units/1` remains invalid. Missing support for a source feature,
an owner unit/relation declaration without its source admission,
unsupported version, conflicting ID/content pin or missing endpoint declaration
must fail before execution. Include extension catalog content in implementation/
method provenance and audit the exact relation in conversion trace detail.

The existing [IR compatibility field](../../schemas/spl-module-descriptor.schema.json:17)
is currently const `spl-ir/0.1`; implementation must deliberately extend that
schema/validator to admit both reviewed artifact versions. Require `0.2` for a
root closure containing the new admission metadata, retain `0.1` for unchanged
base closures, and allow old `0.1` base dependencies within a `0.2` root. This
is an explicit compatible schema change, not an assumption that the old enum
already accepts the new IR. Package envelope `spl-module/1` need not change.

Two existing compatibility traps require explicit tests:

1. Both linkers currently reserve builtin names globally. Reserve
   `convert_quantity` only for modules opting into this feature. The unchanged
   old module exporting/importing that name must still link in base mode. A new
   opting-in caller must explicitly rename a colliding legacy import; it cannot
   silently capture it as a builtin.
2. Descriptor dictionaries currently allow ordinary domain dictionaries with
   arbitrary keys. Do not start reinterpreting/rejecting every old key that merely
   resembles a future unit-dictionary name. Validate extension semantics only
   after explicit source/descriptor admission. This follows declared semantics,
   not spelling heuristics. New extended closures still reject unsupported or
   contradictory declared catalog versions, including unused declarations.

## State identity and old behavior

For types containing only existing base units, preserve the exact existing
`dimensioned:<sha256>` normalized-type algorithm. Merely selecting an extension
or importing an unused catalog must not rename a Download or Minute state key.
Old Money-only and structured state keep their established rules.

For a type that actually contains an extension-defined unit, use a separately
versioned dimensional identity (proposed `dimensioned-v2:<sha256>`) over the
complete normalized type plus the canonical **used unit-definition** IDs/content
pins. Include recursive Record/List/Option/Tuple/Map-value occurrences and keep
AST/checked-Type helper equality. Do not hash the whole enabled catalog: unused
features must not rename unrelated state. Require the resulting identity in slot,
cell, scope.unit and state_key, with the existing unit key-field requirement.
Definition drift or a changed meaning under the same nominal Hour cannot reuse
old Hour state silently.

The initial demo should keep its original Minute meter in Minute and emit a
derived Hour quantity. This consumes an actual old Minute cell without relabeling
or rescaling it. A separate new Hour-meter witness starts from explicit genesis
and carries its new definition-bound identity. Converting an existing stored
meter's meaning requires a separately selected migration; retagging its old cell
is not conversion.

Preserve old source acceptance/rejection, financial values, units, state payloads
and state type identities. New compiler/runtime pins necessarily change after
implementation; cross-build semantic/result digests are not promised identical.
Retain issued packages and old pins instead of repinning history. Versioned
replay under the new build must use unchanged old source/facts and actual old
state, with differences in implementation provenance disclosed.

## Acceptance and implementation window

| Fixture/control | Required result |
| --- | --- |
| 90 Minute → Hour, separately supplied original USD12/Hour price | Exactly 1.5 Hour and USD18, with both original quantity and price retained |
| 150 Minute → Hour, original USD12/Hour price | 2.5 Hour and USD30; original quantity/evidence and conversion identity retained |
| Existing alternative 150 Minute × USD.20/Minute | USD30 with unchanged old core encoding; the new feature adds typed conversion guarantees |
| 0, empty Minute sum, 1/3 Minute | 0 Hour, 0 Hour, 1/180 Hour; tagged zeros and exact fractions |
| Explicit inverse and round trip | 1.5 Hour → 90 Minute; 150 Minute → 2.5 Hour → 150 Minute exactly |
| Signed core quantity | −90 Minute → −1.5 Hour; a selected nonnegative contract policy may reject separately |
| Wrong unit/target or Rate/Money argument | Static dimensional/type failure; no implicit price or currency conversion |
| Newly named 59:1 edge over immutable Minute1/Hour60 endpoint scales | Reject exact scale inconsistency even if the new edge has positive counts and a valid distinct pin |
| No feature, empty List/Option<Hour>, unused local/imported Hour export | Reject before execution, even with an extended root elsewhere |
| Forged IR annotation/context/factor/pin | `INVALID_IR` or the reviewed admission diagnostic before either native path |
| Unknown/duplicate/conflicting extension or relation declaration | Deterministic preflight rejection; no partial outputs or closing state |
| Old exported `convert_quantity`, old extra domain dictionary, actual Id-argument alias cases above | Unchanged base-mode link/admission behavior, including actual v1 acceptance/rejection and both state hashes |
| Old Download/Minute actual state under unchanged source | Same financial values, payloads and exact existing state type identity |
| New Hour state | Actual serialized adjacent carry; wrong definition/type/tag/cell key fails |

Additional conversion negatives must distinguish unknown relation ID/version,
an undeclared endpoint, input Minute with target Minute under this two-endpoint
relation, Download with target Hour, wrong incoming unit tag, and a manifest/IR
claiming 59 Minute:1 Hour or a mismatched unit-definition digest under the fixed
relation ID. Forward 90 Minute must never use the inverse factor and produce
5,400 Hour. The correct inverse is selected only for an actual Hour input and
Minute target. Admission/shape/typed-binding failures must be labeled at their
actual stage; preflight rejection is not native financial execution.

Tests must cover recursive inputs/results/state, empty and unused closure paths,
tagged parameter bounds and conservation. A conservation target in Minute cannot
silently reconcile Hour; compare after an explicit source conversion into the
same declared dimension. The adapter transports original usage/evidence/price;
it never computes the converted amount or strips/changes source tags.

Implementation should occur only in the coordinator's next shared core window:

1. Freeze old source/state/control cohorts and agree the header/catalog/state
   identity spellings above.
2. Introduce immutable admission plumbing with base defaults; replay old checks
   before enabling any new unit.
3. Register the one finite usage-time catalog and generic call; align per-owner
   linking, IR validation, runtime, both emitters and recursive codecs together.
4. Add canonical descriptors, independent Fraction controls, adversarial IR and
   actual old/new state carry. Preserve complete closure checks.
5. Perform a clean coordinated native build, both smokes and frozen old/new
   conformance. Do not mix changed Lean structures with stale olean/native symbols.

No foreign-currency types, FX quotes/rounding, generic runtime plugins, graph
conversion search, arbitrary new unit definitions, broad unit algebra or old-state
migration are needed for this bounded implementation. The admission/context and
relation-application mechanism can be reused by later approved extensions; each
such extension still needs its own economics, units, policy and compatibility
evidence. The owner-selected later currency/tool sequence remains separate from this non-FX implementation.
