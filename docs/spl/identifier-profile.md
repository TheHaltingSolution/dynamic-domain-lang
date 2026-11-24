# Declared typed identifier profile

`LD03-ID-1` retains the existing nonempty, case-sensitive 7-bit profile for
**declared `Id<Kind>` values**. This is the finite C1 alignment for
`B-SCHEMA-UNICODE`; it adds no normalizer, compiler primitive, schema migration
or new identifier policy. The owner adopted the declared-type interpretation
following [LD-03, lines 90–129](/C:/Projects/Film_TV_participation_dynamic_DSL/ResearchAgent/documents/SPL_LD03_Completion_Review.md:90).

Every character U+0000 through U+007F is admitted when the string is nonempty.
That includes NUL, DEL, whitespace, tabs, line endings and embedded controls;
JSON must escape characters where its transport grammar requires it. `A` and
`a`, `A` and ` A `, and `AB` and `A\u0000B` are distinct. Equality does not trim,
case-fold, normalize, transliterate or resolve a display label. This boundary
must not silently become printable-only or adopt SPL variable-token syntax.
A contract-specific narrower token rule must remain an explicit separate policy.

This rule is selected by the checked `Id<Kind>` type, not by a field name such
as `id`, `event_id` or `fact_id`. NFC Unicode business/event identities declared
as `Text` remain valid Text. The C16 settlement registry uses Text-backed event
tuples; `application:q1-é` must survive calculation, tuple history and canonical
closing state. Unicode NFC display labels such as `Café 雪` likewise remain Text.
The [existing C16 regression](../../Tests/test_settlement_modules.py) is executed
by the new profile suite without changing settlement source or policy.

Namespace separation is static and contextual. The lexical string `x` may occur
as both `Id<Asset>` and `Id<Party>`, but comparison, substitution and map lookup
must respect the checked kinds. Native runtime strings do not carry an extra
namespace tag. Generic canonical scope checks additionally constrain declared
Agreement, Pool, Participant and Asset IDs to the corresponding supplied scope;
other `Id<Kind>` namespaces still retain their declared type and lexical profile.

## Boundary checks and diagnostic precedence

[Reference decoding](../../spl_compiler/evaluator.py:88),
[native binding decoding](../../SPL/Bindings.lean:178) and the
[generic typed canonical boundary](../../spl_compiler/modules.py:491) retain
their existing checks. They recurse through records, Option, List, Map keys and
values, tuples and structured opening/closing state. Checked outputs and registered
output contracts are validated before canonical finalization.

| Supplied declared ID | Direct reference | Direct native binding | Canonical wrapper admission |
| --- | --- | --- | --- |
| Any nonempty 7-bit value | Accepted | Accepted | Accepted if its scope/references resolve |
| Empty | `INVALID_ID` | `EMPTY_IDENTIFIER` | `INVALID_ID` |
| NFC `é` | `UNSUPPORTED_IDENTIFIER_PROFILE` | `UNSUPPORTED_IDENTIFIER_PROFILE` | `UNSUPPORTED_IDENTIFIER_PROFILE` |
| Decomposed `e` + U+0301 | `INVALID_ID` | `UNSUPPORTED_IDENTIFIER_PROFILE` | `NON_NFC_TEXT` |
| ASCII Asset outside supplied asset scope | Source profile alone does not resolve scope | Source profile alone does not resolve scope | `MODULE_REFERENCE_SCOPE` |

These are actual layer differences, not reasons to rewrite the core diagnostics.
The canonical codec already requires all incoming Text to be NFC and therefore
may reject decomposed text before typed ID admission. Direct reference/native
string handling is not a promise that arbitrary raw strings satisfy the canonical
Text contract. No silent NFC conversion occurs at either boundary.

Wrapper preflight rejection has empty trace and no native financial execution.
A declared output contract is checked after calculation: the suite deliberately
registers an `Id<Item>` result contract for a Text-producing test source and
verifies a non-ASCII value cannot finalize. This is output-contract admission,
not a claim that SPL casts Text to Id. Its retained native trace identifies the
actual post-execution stage. Incoming and outgoing state use the same existing
typed contracts; the tests also serialize an actual native predecessor cell and
consume it in an adjacent run.

The outer generic package schema has many ordinary Text reference fields.
It does not declare every canonical scope, decision, provenance or source string
to be an SPL `Id<Kind>`. A Unicode NFC outer agreement reference can be admitted
when no declared typed Agreement port claims that value. Accordingly this profile
does **not** assert that every canonical field called an ID is ASCII. Broader
legacy profiles retain their separately published schemas and checks.

## External identities and compatibility

Retain raw external source bytes, their digest, original row identity, namespace
and version outside canonical typed-ID fields. Canonical NFC Text cannot preserve
a decomposed raw identifier unchanged. Link that byte-level evidence to an
explicit approved, effective and versioned mapping to a typed ASCII key.
Do not silently trim, normalize or merge two external financial events.
An approved alias policy may map two source asset aliases to one asset while
retaining their separate original financial event identities.

This alignment implements no such mapping engine and grants no professional
approval to a proposed mapping. A future NFC-ID migration needs a separately
pinned normalization/version policy, namespace/version collision reports,
explicit acceptance/rejection, and old/new replay. An unresolved collision blocks
mapping; it cannot authorize a silent identity merge.

## Verification scope

[test_identifier_profile.py](../../Tests/test_identifier_profile.py) has 15 methods exercising
all 128 single-character admitted IDs, exact case/control preservation, empty
and non-ASCII rejection at seven nested input/opening locations, namespace typing,
Map key/value recursion, NFC Unicode Text named `id`, canonical outer Text
references, source/output-contract stage distinctions and serialized state.
Native methods compare the reference, native IR, native emitted Lean and the
separate Python emitter, and run the existing C16 Text/tuple regression. No
environment switch substitutes reference execution for requested native checks.
Frozen verification evidence is reported with the handoff; this document makes
no whole-program correctness or Unicode migration claim.
