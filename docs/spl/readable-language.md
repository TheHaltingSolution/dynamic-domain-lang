# Readable SPL

`spl-readable/0.1-dev` is a controlled readable surface over the existing
`spl/0.1-draft` source language. The native Lean frontend expands individual
statements, parses the expansion into `SPL.Syntax.Schedule`, and passes that
schedule to the ordinary checker and compiler. The original brace/semicolon
syntax remains supported.

The three executable readable examples are
[Skouras/Ventura](../../cases/sv/sv01-readable.spl),
[the separate RQ-07 posting-cost profile](../../cases/sv/rq07-readable.spl), and
[Lionsgate](../../cases/lg/lg01-readable.spl). They retain the original bounded
synthetic calculations: SV payable 18,000 and LG payable 35. These are calculated,
unissued amounts. Full compiler verification and accountant readability review
remain deferred.

The main schedule presents the financial rules first. An explicit `Bindings:`
footer supplies technical identifiers, schema versions, inputs, state keys,
collection selection, evidence references, participant scope and report fields.
Economic choices in those declarations are part of the executable agreement.
Following [LD-01-D1](implementation-answers.md), each example explicitly
incorporates a versioned readable policy: [SV incurred-date](policies/sv-incurred.md),
[RQ-07 GL-posted](policies/rq07-posted.md) or [LG already-cleared](policies/lg-cleared.md).
These sections disclose cost recognition and eligibility, funding valuation and
completeness, supplied state/evidence, applicability and actual parameter
references. They belong to the review package with the main schedule and footer.
There are no built-in Skouras, Ventura or Lionsgate rules. Altering a percentage,
selector or input changes the calculation; a title or filename never selects a
precomputed answer.

For example, the Skouras main schedule contains:

```spl
Incorporate policy "sv-incurred@1".

For each Picture distributed by Ventura:
  Require Valid Funding Share or fail "INVALID_FUNDING_SHARE".
  Cash Receipts are the amounts Ventura received under the Acquisition Agreement for that Picture during the quarter citing "SV-8-CASH".
  If Skouras contributed no Acquisition Funds:
    Distribution Fee is 25% of Cash Receipts citing "SV-8-FEE".
    Allowed Deductions are the deductions allowed by the Net Profits Schedule citing "SV-8-COST-SCHEDULE".
    Net Profits are Cash Receipts less Distribution Fee less Allowed Deductions citing "SV-8-BASIS".
    Skouras Participation Share is 20% citing "SV-8-SHARE".
    Skouras Earned Participation is Skouras Participation Share of Net Profits.
  Otherwise:
    Distribution Fee is 7.5% of Cash Receipts citing "SV-8-FEE".
    Allowed Deductions are the deductions allowed by the Adjusted Gross Receipts Schedule citing "SV-8-COST-SCHEDULE".
    Adjusted Gross Receipts are Cash Receipts less Distribution Fee less Allowed Deductions citing "SV-8-BASIS".
    Skouras Participation Share is Skouras Proportionate Funding Share citing "SV-8-SHARE".
    Skouras Earned Participation is Skouras Participation Share of Adjusted Gross Receipts.
  Require Skouras Earned Participation >= USD 0 or fail "SV_NEGATIVE_EARNINGS_OUTSIDE_PILOT".
  Report by Picture: Picture Identifier, Cash Receipts, Distribution Fee, Allowed Deductions, Participation Basis, Skouras Participation Share, Skouras Earned Participation.
```

The complete fixture includes settlement, explicit input/state declarations,
quarter validation and the bindings needed by this excerpt. Its two deduction
phrases are separate bindings. Both aggregate the supplied branch-eligible cost
view in this bounded profile; the canonical intake checks the corresponding
eligibility decisions before execution. The surface does not infer that the
underlying contractual deduction schedules are interchangeable or derive full
historical cost eligibility from accounting rows. RQ-07 explicitly uses
`SVPostingCost.recognition_date`; it does not create missing incurred dates.

## Closed grammar

A file begins with `Participation Schedule for <display title>`. Statements end
with a period. Spaces indent blocks; tabs and inconsistent indentation fail.
Whole-line `//` comments and blank lines are permitted. There must be exactly
one `Bindings:` footer after the readable rules. Each supporting declaration
occupies one line. Keywords and phrase names are case-sensitive.

| Readable form | Expansion/requirement |
| --- | --- |
| `Incorporate policy "identifier@version".` | Top-level, unique, versioned policy identity; emits a typed `Text` provenance definition with the authored span. Canonical execution resolves and pins its registered readable policy and checks declared implementation requirements |
| `Account for each calendar quarter.` | Requires an explicit `calendar quarter` binding; defines `accounting_period` and requires `is_calendar_quarter(accounting_period)` |
| `<name> is <expression>.` / `<name> are <expression>.` | Immutable `define`; a multiword target needs an explicit identifier binding |
| `... citing "rule-id".` | Preserves the citation on the definition |
| `Require <condition> or fail "CODE".` | The ordinary checked `require` declaration |
| `For each <phrase>:` | Requires an exact `Iterate` registration and an indented block ending in `Report by` |
| `If <condition>:` / `Otherwise:` | Both branches define the same unique resolved names in the same order; merged citations must agree |
| `For settlement with <party>:` | Requires an exact `Settle` registration; emits a definition typed `Id<Participant>` and its indented settlement statements |
| `Closing <name> is <expression>.` | Candidate closing state; never overwrites the opening value |
| `Report by <label>: <expression>.` | A loop's yielded record/value |
| `Report "port": <expression>.` | The ordinary checked output port |
| `Report ...: <field name>, <field name>, ... .` | Builds a record using explicit `Field` declarations, keeping all columns visible in the financial schedule |

Policy identities use nonempty ASCII names (`letters`, digits, `.`, `_`, `/`,
`-`) followed by `@` and a nonempty version (letters, digits, `.`, `_`, `-`);
each part starts with a letter or digit. Duplicate, unversioned or nested
incorporations fail. The frontend preserves a policy as an ordinary typed
`incorporated_policy_N` definition, rather than silently ignoring it. This is
provenance syntax, not an assertion that arbitrary external prose has been
executed. A direct native check/compile does not load policy files. Final
canonical runs resolve the identity using [the pinned policy registry](policies/manifest.json),
include its readable text in dependency closure and compare its declared
implementation with the actual parsed expansion. Unknown
identities and machine-checkable inconsistencies block finalization; policy
interpretation still requires human review. Actual values at the registry's
parameter paths are exposed with the review package. Arbitrary purported policy
sentences remain unsupported syntax.

The current registry deliberately pins **all executable declarations** with
`spl-policy-core/1` AST signatures. A signature removes source spans, keeps
lexical assertion order and includes nested definitions, selectors, branches,
types, state aliases, closing and output wiring. It compares the actual used
expressions, so retaining a correct expression in an unused footer binding does
not excuse changing the executed selector. Main/footer display-phrase renames,
whitespace and equivalent parentheses preserve signatures. Core identifier
renaming or a generally equivalent algebraic rewrite is not recognized by this
bounded check. A changed visible rate or method therefore needs an explicit
policy revision before canonical finalization; direct native/frontend tests can
still exercise changed calculations. Parameter values supplied through the
existing declared inputs remain variable and are exposed in review. This is
not a semantic equivalence proof or independent interpretation approval.

A calendar quarter is a Gregorian, half-open interval: January 1–April 1,
April 1–July 1, July 1–October 1, or October 1–January 1 of the next year.
A different interval fails `READABLE_CALENDAR_QUARTER_REQUIRED` and produces no
finalized result/state. Fiscal-quarter or business-calendar interpretation is not
implicit. The typed canonical period and the runtime dates remain explicit.

Financial expressions compose bound phrases, existing closed SPL expressions,
`less`, `plus`, `of`, exact percentages, and `the lesser of A and B` /
`the greater of A and B`. These last two forms occupy a complete expression;
use the core `min`/`max` calls for more complex nesting. Multiplication and
subtraction use the underlying SPL precedence, with parentheses available.
For example, `7.500% of USD 100` expands to `(7.500 / 100) * USD 100` and is
exactly 7.5. An integer percentage adds a decimal marker (`25.0 / 100`) to
select the existing Ratio type. No rounding policy is introduced.

Conditional blocks currently contain financial definitions, rather than
arbitrary nested control flow. Each matched definition lowers to a lazy `if`
expression. The same resolved names/order rule makes the merge explicit: in
SV, `Net Profits`, `Adjusted Gross Receipts`, and the report's `Participation
Basis` are visibly bound to the same technical `basis`. Collection loops and
settlement blocks can contain the supported statements. Multiple settlement
blocks currently collide on the generated `settlement_participant` definition
and are rejected by the normal duplicate-name check.

## Supporting declarations

The footer must explicitly declare the schedule identifier and all three
underlying language/core/schema versions. It may contain the existing one-line
`input`, `opening`, `require` and `define` declarations, plus:

```spl
Bindings:
  Schedule Example.
  Using language "spl/0.1-draft" core "spl-core/0.1-draft" schema "spl-data/0.1-draft".
  input policy: SVPolicy;
  input pictures: List<SVPicture>;
  Settle "Skouras" with policy.participant_id.
  Iterate "Picture distributed by Ventura" as picture in pictures into title_results.
  Bind "calendar quarter" to policy.period.
  Bind "Cash Receipts" to cash.
  Bind "Participant" to settlement_participant.
  Bind "Picture Identifier" to picture.asset_id.
  Field "Picture Identifier" as asset_id.
  Field "Cash Receipts" as cash.
```

`Settle` connects a readable party label to an explicit expression checked as a
participant identifier. An unknown heading label fails at that authored heading;
a pool identifier supplied in place of a participant identifier fails typing.
`Iterate` similarly connects its complete phrase to the explicit collection,
item binder and result name. Proper names are not looked up or inferred from
prose. The display title itself does not establish economic scope.

`Bind` phrases are nonempty and unique. Expressions use one longest-match pass
at identifier boundaries, with string contents excluded. Expression replacements
are parenthesized so a bound subtraction remains one operand of a percentage.
Bindings are not recursively expanded; their right-hand sides use the existing
core identifiers and expressions. Definition targets must resolve to a single
core identifier. Unsupported prose fails parsing or ordinary name/type checking.
A report list requires a `Field` declaration for every displayed name; record
field duplication and output structure remain ordinary checker concerns.

Receipt/date selection, eligibility, proportionate funding share, prior-period
state and every policy parameter must be supplied explicitly. The main rules
show rates, branch-specific bases, pooled recovery, closing balance and report
columns. The footer shows how those names connect to data and scope. It remains
part of the reviewable source and its digest, not an untracked policy registry.

## Compiler boundary and checks

`SPL.Readable.expand` returns expanded source plus an origin span per generated
line. `SPL.Readable.parse` parses it with `SPL.Parser.parse` and remaps all syntax
nodes and parser diagnostics to authored statement spans. Branch expressions
retain the respective true/false source lines. Spans are statement-level spans,
not a character-by-character alignment of inserted technical expressions.
Citations survive into the ordinary checked syntax and later trace. No host
language evaluation, file lookup or full-file template recognition is involved.

`spl_compiler/readable.py` independently implements expansion, parsing and span
remapping as the Python reference frontend. It uses the existing independent
Python parser/checker/evaluator, not native parse output. Differential checking
still requires separately authored numerical expectations; agreement between two
implementations alone is not an accounting-methodology oracle.

Run with the pinned environment from the repository README:

```powershell
lake exe spl check cases/sv/sv01-readable.spl
lake exe spl compile cases/lg/lg01-readable.spl .lake/spl/ReadableLG.lean
lake exe spl expand cases/sv/sv01-readable.spl .lake/spl/ExpandedSV.spl
lake exe spl ir cases/sv/sv01-readable.spl .lake/spl/TypedSV.json
lake env lean --run Tests/SPLReadable.lean
python -m unittest Tests.test_readable -v
```

Tests compare emissions and closing state with all three original schedules,
check independently expected 18,000/35 payables, rename parties, change a rate and
receipt, check exact percentages and expression precedence, preserve both branch
spans and quoted text, reject unsupported syntax/indentation, reject unbound or
wrongly typed settlement parties, and block non-quarter intervals atomically.
The old source grammar and its tests remain in place.

The `expand` command also writes a `.map.json` file with authored statement spans
for every generated line. This permits review of the deterministic expansion
without accepting that expansion as a proof of accounting interpretation.
