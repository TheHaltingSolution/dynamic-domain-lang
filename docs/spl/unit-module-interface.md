# Declared unit registration and canonical state interface

This interface consumes the immutable finite feature catalog described in the
[extension plan](unit-conversion-extension-plan.md). The selected new feature is
`spl.usage-time/1`; `spl.units/1` retains its Download and UsageMinute meanings.
The separate dictionary namespace `spl.units.usage-time/1` identifies UsageHour,
and `spl.conversions.usage-time/1` identifies the registered exact relation.
Names, definition IDs, exact endpoint scales and content hashes are compiler
catalog data, not package-supplied conversion factors.

An owner's source header determines its `DimensionAdmission`. Registration
checks matching feature capability declarations, known codecs and dictionary
entries against that source owner. A descriptor capability can record transitive
support but does not enable an input, opening, schema, export signature, source
annotation or builtin in that owner. All registered local schemas and exports
are checked, including unused signatures. A local schema cannot shadow a newly
admitted unit in the same owner. Unselected legacy domain dictionaries that
merely resemble future catalog namespaces retain their old ordinary-string
meaning.

The complete import closure determines artifact version. Any extended source
owner, including an unused USD-only dependency, requires the importing root's
`spl-ir/0.2` registration. Its base dependencies can remain `spl-ir/0.1`.
An entirely base closure retains `spl-ir/0.1`; selecting an unrelated descriptor
capability alone neither upgrades its source nor grants a new namespace.
The descriptor schema deliberately admits those two versions; the resolver
enforces their actual source/closure coherence. Package and exact/quantity codec
envelope versions retain their current shapes.

`RuntimeMeanings` is a separate verified closure context. It can serialize and
calculate an inferred foreign quantity without granting lexical permission.
For example, a base root may call the extended `to_hour` function, infer Hour,
add `h+h`, and emit the result. Its registered result contract is structurally
validated against the actual checked emitted expression type using that runtime
context. An unused extended dependency cannot justify a fabricated Hour result
contract for a USD expression. The same root still rejects an explicit local
Hour annotation, an Hour input or unused schema, and a direct call to the new
builtin. Only output contracts whose checked expressions establish the type use
the foreign-meaning path; this is not whole-closure admission for every port.

The registration checks require declared used units, literal relations and both
relation endpoints. Hour under `spl.units/1`, missing declarations, unsupported
catalog versions/entries, source features omitted from capabilities and missing
quantity codecs block. Exact relation consistency and full catalog/content-pin
checks are core/IR responsibilities. Both registry and source pins are rechecked
before canonical consumable state is exposed.

For state, `dimensioned_state_unit(type, context=BASE_MEANINGS)` accepts a checked
type or expanded AST. The existing normalized-type hash and `dimensioned:` prefix
remain byte-for-byte unchanged for base-unit types, even when an unused feature
is present. A type actually containing a new unit receives `dimensioned-v2:`
over the normalized type plus sorted used unit-definition IDs and content pins.
Collection is recursive through Record/List/Option/Tuple/Map value structure,
and identifies units only at actual Quantity/Rate positions. Opaque Id kinds
never become unit-definition use. No entire enabled catalog is hashed into an
unrelated Minute or Download state key.

The same state identity is required in the registered slot, cell, `scope.unit`
and canonical state key, with `unit` retained in the declared key fields.
Forged/missing identities, mismatched payload tags, scope and period boundaries
block atomically. An original Minute cell can pass from the base Minute program
to the conversion program without rescaling or relabeling its stored quantity.
New Hour state starts from explicit genesis and carries a definition-bound
identity. Adjacent witnesses use the actual prior emitted cell and its real
canonical `prior_result_ref`; a fixture case ID is not treated as a result digest.

Actual legacy namespace behavior is preserved, including its surprising cases.
Descriptor `_type_ast` recursively expands aliases inside `Id` arguments. Thus
a local `UsageHour` schema makes descriptor `Id<UsageHour>` become `Id<Record>`.
A source still spelling `Id<UsageHour>` then fails `MODULE_PORT_MISMATCH`; a
matching source `Id<Record>` remains accepted. The compound marker/Minute-state
hashes remain:

```text
without alias: dimensioned:035d54d28564df0f1e648dff57028a59231fd29ebd0e90fd20749e327edf3352
with alias:    dimensioned:29742617b381396f64a215c88e7153b3b3dbf4a972f3b95168f5985aaca1a4be
Download:      dimensioned:495808ae9a33038bcc29cf5b3fc3c7cff8da359bf26c7daf90e0e5852e171978
```

Likewise the existing `contains_dimension` traverses Id arguments and classifies
nominal `Id<Quantity>`/`Id<Rate>` as dimensional for legacy state validation. This
interface preserves their existing hash and unit-key requirements instead of
silently correcting that v1 classification. The new used-definition collector
still treats their kind names as opaque, preventing false unit pins and missing
argument crashes. These are compatibility witnesses, not newly recommended
namespace conventions. Any resolver/normalization change requires a separately
versioned decision and replay/migration assessment.

The new fixtures and tests live in [usage-conversion](../../cases/usage-conversion/README.md)
and `Tests/test_usage_unit_modules.py`. They compare financial values with the
unchanged independent original-fact oracle, while testing registration, state and
execution layers separately. A wrapper rejection is labeled as preflight; it is
not credited as native interpretation or emitted execution. The native method
requires actual reference/native IR/native emitted agreement after core release.
An external frozen source/import/build-origin record supplies the executed
evidence. No correctness proof or arbitrary compiler-plugin claim follows from
this finite versioned unit feature; FX remains reserved for the later authorized
tool demonstration.
