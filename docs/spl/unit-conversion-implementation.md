# Explicit usage conversion candidate

This isolated implementation supplies the finite non-FX capability described in
[the reviewed plan](unit-conversion-extension-plan.md). It adds exact quantity
conversion under explicit source/module admission. The original Minute encoding
and every existing financial source remain available. Native currencies/FX,
civil-time/calendar conversion, arbitrary unit registries and implicit unit
conversion are outside this change.

```spl
schedule Usage language "spl/0.1-draft" core "spl-core/0.1-draft"
  schema "spl-data/0.1-draft" uses "spl.usage-time/1" {
  input minutes: Quantity<UsageMinute>;
  input price: Rate<UsageHour,USD>;
  define hours = convert_quantity(minutes, "UsageHour", "spl.usage-time/1:minute-hour");
  emit "original_quantity" = minutes;
  emit "original_price" = price;
  emit "hours" = hours;
  emit "earned" = hours * price;
}
```

Original 90 Minute and USD12/Hour produce exactly 1.5 Hour and USD18; original
150 Minute produces 2.5 Hour and USD30. The separate old 150 Minute ×
USD.20/Minute calculation still gives USD30. This is a typed capability and
interface guarantee, not a proof of financial inexpressibility in the old core.
Independent controls consume original measurement/price facts in
[oracles/usage_conversion.py](../../oracles/usage_conversion.py) before any
binding projection. Adapters never compute the converted answer or price.

## Catalog and contexts

The base `spl.units/1` remains exactly Download/UsageMinute. Immutable compiled
Lean/Python catalog rows define feature `spl.usage-time/1`, new unit dictionary
`spl.units.usage-time/1`, relation dictionary `spl.conversions.usage-time/1`, and
relation `spl.usage-time/1:minute-hour`. Endpoint definitions give Minute scale
one and Hour scale sixty in the same usage-duration base. The generic algorithm
selects opposite relation endpoints and divides their immutable scales: 1/60
forward and 60 inverse. No arithmetic/admission algorithm branches on the new
unit name; later registered pairs require reviewed data rows and controls.

The relation validator rejects 59:1 against those fixed meanings, and rejects
altered endpoint definitions. A proposed 120:2 edge is scale-consistent but is
not thereby registered or executable. Unit/relation IDs and content pins are
retained in extended IR and native conversion trace detail. Conversion takes Quantity
and literal target/relation strings; it cannot retag Rate/Money or convert a
price/currency. Mixed Minute/Hour arithmetic remains invalid before an explicit
quantity conversion. Rate currency remains USD only.

`DimensionAdmission` is lexical owner permission. `RuntimeMeanings` is the
verified closure's immutable meaning universe. They are separate classes/Lean
structures; no process-global flag or all-closure lexical union is used. An
extended function may return Hour to a base caller, which can infer `h+h` or
`h*2.0` and serialize that result. Its caller still cannot spell a new Hour
input/opening/local annotation or use the new builtin without its own header.
An empty list/none gets a foreign Hour type only through a verified parent/callee
signature edge; an ungrounded annotation does not acquire permission from an
unused dependency.

The header token `uses` is contextual. Existing inputs, fields, functions,
Id-kinds, schedule names and descriptor-local schemas with that spelling remain
ordinary names. `convert_quantity` is reserved only in an opting-in owner.
Legacy exports retain their meaning and need a deliberate local alias where a
new caller also uses the builtin. Existing descriptor-local alias recursion,
including its actual `Id<UsageHour>` → `Id<Record>` behavior, is preserved.
An opting-in same-owner structural alias/unit ambiguity rejects explicitly.

Default type parsers, raw quantity/rate codecs and value constructors remain
base-only. Extended tagged values retain a validated frozen context through
numeric reconstruction, typed zero, nested decode and serialization. Context
does not change equality merely because an unrelated catalog is enabled. The
`{value,unit}` and `{value,per_unit,currency}` transport shapes are unchanged.

## IR and state boundary

Unchanged base programs retain exact `spl-ir/0.1` serialization: no empty
admission fields, new annotation fields or owner defaults are added. Extended
closures use `spl-ir/0.2`, including an unused extended USD-returning dependency.
Root lexical features, per-function owners, an independent linked-signature
table and catalog pins are explicit. Base dependencies can stay v1 inside a v2
root registration.

The v2 native validator reconstructs source-level annotation/inference edges
and rechecks them under each owner. An apply's parameter/result annotations
must also match the independent linked signature, not serve as their own
authority. Arbitrary Meta types or an `inferred` flag cannot license a hidden
empty Hour container. Typed malformed programs reject before both native
interpretation and emission; the interpreter emits no observations or financial
state in these cases. This is IR coherence, not authentication of external
source provenance. Canonical pinned source/descriptor closure remains that
authority, and checked input bindings remain an execution assumption.

Native/Python artifact shape gates reject extension metadata in v1 positions,
including empty payloads, and check v2 snapshot pins/signatures. Ordinary record
fields named `uses`, `admission`, `owner_context` or `meta` remain data. The JSON
gate is explicitly an artifact preflight; it does not execute serialized JSON
IR or replace native typed-Program validation.

Base dimensional state keeps the exact `dimensioned:<sha256>` algorithm. New
state whose complete recursive type actually contains an extension unit uses
`dimensioned-v2:<sha256>` over normalized type and **used** unit-definition
IDs/pins. Unused catalogs do not rename old state; Id-kind arguments are opaque
and never counted as units. The original Minute meter remains Minute while
emitting derived Hour. A separate Hour-meter witness starts from genesis and
uses its new definition-bound identity. Existing meters are not silently
retagged or migrated. Registered source/interface/carry details are in
[unit-module-interface.md](unit-module-interface.md).

## Dated finite evidence

Artifacts are outside Git under
`C:/Projects/Film_TV_participation_dynamic_DSL/artifacts/spl/`.

| Archive | Observed scope |
| --- | --- |
| `usage-units-baseline-20261123-a` | Pre-edit abee/daf/673 frontend/source/state evidence; nine raw base IR exports, names/legacy-function controls, actual old Download first/successor state |
| `usage-unit-core-20261123-a` | Initial 11-method frozen core cohort; zero failures/errors/skips/drift |
| `usage-unit-interface-20261123-b7594415` | 25 methods, nine actual canonical native/reference/IR/emitted comparisons, 36 Lean commands, 68.728105 s; zero failures/errors/drift |
| `usage-units-oldstate-replay-20261123-a` | Actual old abee-produced serialized Download cell replayed under new backend compare: 100 → 100.5 Download, earned .375, unchanged state unit |
| `usage-unit-build-native-abi-20261123-a` | Deliberate build_native → temporary Python-emitter AOT grouping → full build/smokes order check; .olean/C object hashes unchanged by helper |
| `usage-unit-final-bounded-20261123-a` | 99 methods, 299.548871 s, zero failures/errors/skips/source/executable drift; rebound after upstream publication/Python memo integration |
| `usage-unit-contextual-none-20261123-a` | Test-only follow-up for foreign contextual []/none and explicit context constructor rejection |
| `usage-unit-final-guard-20261123-a` | Final immutable-context argument guard: 29 Python admission/canonical methods and nine exact historical v1 IR byte replays passed |

The 99-method cohort includes both emitters and selected temporary AOT targets,
19 hostile typed IR cases checked at native validator/interpreter/emitter
boundaries, two negative serialized shape controls, direct native catalog scale
and definition-drift checks, ordinary metadata-spelling record data, actual
canonical carry, and existing scalar/quantity/link/publication regressions.
Each archive records its actual implementation pins; historical archives are
not repinned after later changes. The initial clean default build passed 98
jobs, optional indexed target 22 jobs, and both smokes passed.

Nine frozen base IR exports also matched exactly after the source/context/IR
changes. Download state remains
`dimensioned:495808ae9a33038bcc29cf5b3fc3c7cff8da359bf26c7daf90e0e5852e171978`.
Both actual alias-dependent compound state fingerprints from the reviewed plan
are preserved, along with the intervening rejected source/descriptor mismatch.

The isolated candidate additionally incorporates the verified compact complete
publication encoder from upstream `b3c5ff0` and Python definition memoization
from `c35f274`, retaining unit-context integration. Complete result envelopes
use compact bytes under the same 64 MiB cap; field mirrors remain readable.
The public native-check helper now uses pinned Lake to keep `.olean`/native
symbol contexts coherent, followed by explicit `-DwarningAsError=true`
read-only checks with no `-o`, `-i` or `-c` output paths.

No new axioms or `sorry` are introduced. Existing scalar core proofs retain
their scope; these finite checks are not a general compiler-correctness proof,
economic/legal authority, emitted branch-coverage percentage or performance SLA.
A broader candidate regression is required before final integration acceptance.

The final bounded guard snapshot has compiler/reference identity
`5269e1bf4384e329b5b29773fbe5400bb87efa7c08907a5d1e9aa7f5a90bca85`,
module identity `2dd2755b679435fb38ec56dfba2c970d3234cc3e7dd28c12ae0ea617aa4cf723`
and runtime identity `a7e4f8e55815ea72abfb1903b2578a5db95d6f505f582f8a67ded9880ac119ba`.
It additionally rejects mutable/unvalidated objects passed as explicit contexts;
it does not change native calculation. Full broad discovery at this stage finds
931 methods; discovery is not execution credit or a coverage percentage.
