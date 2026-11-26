# Independent ratio-precision and rounding-placement controls

This independent control slice addresses `B-NUM-PRECISION` and requirements
F02–F04 in the [completion backlog](completion-backlog.json). Its
[policy](../../cases/numeric-precision/policy.md) and
[original casepack](../../cases/numeric-precision/neutral.json) are specification
inputs for a different future source author. It adds no compiler, SPL, native
execution, canonical publication or professional approval claim.

The author consulted the public mathematical/mode contract in
[core-and-compilation](core-and-compilation.md#5-exact-arithmetic-and-rounding),
[language reference](language-reference.md#types-and-arithmetic),
[ratio policy metadata](data-and-run-contract.md) and the scope of the existing
[finite interaction corpus](rounding-interaction-design.md). Runtime code,
existing financial oracle implementations, projected bindings and executable
SPL were not inspected to derive these expectations.

## Original API and finite policy

`oracles.numeric_precision.numeric_precision(data)` consumes
`numeric-precision-neutral/1`. Failure raises `NumericPrecisionOracleError`
without a partial result or input mutation. Imports are only standard-library
`copy`, `fractions`, `hashlib`, `json` and `re`; the oracle has no filesystem,
clock, compiler, adapter or other financial implementation dependency.
`exact_json(result)` converts computed fractions to normalized integer/rational
strings while preserving original records. `registration(policy)` computes
only the supplied document's content reference.

The case contains one original ratio expression, zero to eight original monetary
basis rows and one explicit complete population. Agreement, participant, pool,
asset and USD scope are exact. Lines name the expression and retain unique
original identities/references, source reference and a dimensioned original
Money basis. Population IDs and signed basis total control the originals; they
are not precomputed earnings. Missing completeness is unknown, whereas an
explicit complete-empty population is known zero. Exact decimal strings and
normalized rational objects are accepted; floats, exponents, noncanonical
rational objects and pre-solved answer fields reject.

Original expressed unit is `percentage` or `fraction`. Policy separately supplies
target expressed decimal places0..6, dimensionless Ratio quantum and mode.
Percentage precision2 and fraction precision4 both require Ratio quantum0.0001;
fraction precision2 instead requires0.01. The scalar's normalized value and its
lexical number of decimal digits do not select that rule. Signed values are
explicitly admitted; this numerical policy does not infer a share range.

Money has a separately supplied positive Money<USD> quantum and mode. Ratio
quantum is never a Money quantum; foreign currency or quantity dimensions do
not become USD by relabeling a scalar. The baseline money quantum is0.01, while
other explicitly supplied positive exact increments remain valid numerical
policies. There is no ambient cent scale or implied payment denomination.

Ratio rounding occurs before monetary application. Monetary policy then selects
`row` or `aggregate` rounding. Five modes use the public names `floor`, `ceiling`,
`toward_zero`, `half_even` and `half_away_from_zero`. Invalid mode, point, dimension,
currency, nonpositive quantum or precision/quantum mismatch rejects before any
financial result, including for empty rows. A source author must implement finite
literal-mode dispatch or separate sources: the present SPL checker does not
admit a dynamically supplied mode as the `quantize` mode argument.

## Independent arithmetic and visible bridges

The independent rounding algorithm takes the exact absolute scaled magnitude,
uses integer division/remainder, chooses a whole number of quanta from sign,
distance and parity, and restores the signed quantum multiple. It does not call
a runtime rounding helper, floating-point `round` or `Decimal` context.

| Supplied policy | Exact original control | Selected result |
| --- | --- | --- |
| Percentage precision2, half-even |12.345% = Ratio0.12345 | Ratio0.1234; basis10000 earns1234 |
| Same precision, half-away | Same original expression/basis | Ratio0.1235; earnings1235 |
| Money half-even by row | Two bases0.01 × Ratio0.5 each derive0.005 | Detail sum0; statement0 |
| Money half-even aggregate | Exact sum0.01; rounded detail sum0 | Statement0.01; bridge+0.01 |
| Money half-away by row | Same two original half-cent derivations | Detail/statement0.02 |
| Money half-away aggregate | Exact sum0.01; rounded detail sum0.02 | Statement0.01; bridge−0.01 |

Ratio detail retains the original expression/unit, exact dimensionless ratio,
selected precision/quantum/mode, rounded ratio and dimensionless ratio delta.
Each line retains original basis, exact earnings before/after ratio rounding,
the ratio effect in USD, rounded display and monetary rounding delta. Statement
detail reports both exact totals, sum of rounded rows, independent aggregate
control, selected point/total, ratio effect, money-rounding effect and total
adjustment. The reporting bridge is explicitly:

```text
sum_rounded_detail + rounding_bridge = selected_statement_total
original_exact_total + ratio_rounding_effect + money_rounding_delta = selected_statement_total
```

No bridge is silently assigned to an original row. Signed cancellation exposes
directed rounding: bases+0.01/−0.01 at Ratio0.5 have exact sum0; floor detail sums
to−0.01 and needs an aggregate bridge+0.01, while ceiling detail sums to+0.01
and needs−0.01. Row rounding is permutation-invariant but not generally
split/merge invariant. Aggregate rounding permits split/merge when the original
exact aggregate and ratio policy remain the same.

## Policy custody and limits

The supplied `{id, revision, sha256}` reference must match the complete supplied
policy document. SHA256 uses UTF-8 JSON with sorted keys, ASCII escaping, compact
separators and no nonfinite constants. This pins exact document content, including
original numeric spelling; equivalent quantum values with changed spelling need
a new content reference. A changed mode/point under the old reference rejects.

The API is stateless and has no earlier registry to compare. Explicitly repinning
a changed document, even under a reused revision label, is not rejected by a
fictional immutable-registration check. External registration, authorization and
revision history require a separate original/prior-registration boundary.
Different future canonical packages must retain their actual selected policy
pins and report changes honestly. Hashes alone do not prove external authenticity.

All results are unissued calculations with payment evidence outside the profile;
no numeric paid-zero or bank execution is inferred. There is no carry, allocation
service, FX, legal interpretation or approval. The thirty targeted methods cover
all five modes for signed ratio ties, positive/negative monetary ties under both
points, signed cancellation, parity/near ties, all seven admitted precision-place
values, fractional/noncent/large exact amounts, zero/empty, wrong dimensions,
population/identity/scope failures, policy changes, raw Unicode/lexemes and
nonmutation/independence. These are finite discriminators, not an all-program
coverage percentage or native capacity measurement.
