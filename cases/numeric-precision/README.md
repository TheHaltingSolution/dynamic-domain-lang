# Explicit ratio precision and USD rounding

This finite source implements the independently frozen [policy](policy.md),
[original cases](neutral.json) and
[design](../../docs/spl/numeric-precision-design.md). It calculates ratio
normalization, declared precision, rounding, earnings, totals and reporting
bridges in SPL. The adapter supplies exact original facts and supplied-document
content hashes; it supplies no rounded ratio, earnings or selected total.

`ratio-rounding.spl` and `money-rounding.spl` independently dispatch the five
literal modes `floor`, `ceiling`, `toward_zero`, `half_even` and
`half_away_from_zero`. The root derives fractional precision from the original
expressed unit. Percentage precision2 requires Ratio quantum0.0001; percentage
precision6 requires0.00000001. Fraction precision2 requires0.01. Original lexical
decimal places never choose the numerical policy. Both positive and negative
ratios and monetary bases are admitted without an inferred share range or floor.

The six supplied scenarios discriminate ratio half-even1234 versus half-away1235
on basis10000, and monetary row/aggregate placement on two original bases0.01
at Ratio0.5. Half-even gives row total0 and aggregate total0.01 with bridge+0.01.
Half-away gives row total0.02 and aggregate total0.01 with bridge-0.01. Both exact
totals, ratio effects, monetary effects and each complete original line remain
visible. No bridge is silently assigned to a row.

## Original and prepared interfaces

`build_modules.py` consumes the frozen `numeric-precision-neutral/1` originals.
Physical profile `numeric-precision-original-json/1` carries separate typed facts
and complete original snapshots. Identity codec `unicode-utf8-hex/1` uses strict,
canonical lowercase UTF-8 hexadecimal and preserves original scalar strings,
including composed/decomposed distinctions and embedded delimiters. Original
JSON is escaped canonical Text; its restoration and typed correspondence are
checked mechanically before execution. Currency and enum meanings remain
unencoded. Exact decimal strings and normalized rational objects are decoded
without floating-point conversion; wrong dimensions or currency are rejected
rather than relabeled.

The wrapper reconstructs all prepared inputs from the full original document
immediately before execution. It rejects altered typed facts, policy/raw tables,
scope, metadata, added evidence or state. Preparation errors publish an atomic
empty blocked result in either supported publication format. Cancellation,
invalid profiles and interrupted publication invalidate an earlier completion
marker while preserving prior invocation files.

SPL checks original-ID populations, supplied content-reference equality, complete
population membership and signed basis totals, scopes, expression authority,
positive quanta, modes, precision/unit agreement and the finite eight-row bound.
The financial program does not parse original JSON or prove document
authenticity. The generic module API trusts prepared typed inputs; bypassing the
case wrapper with coherently altered typed facts can therefore calculate a
different financial result beside unchanged raw Text. Tests expose that boundary
separately from original-qualified case results. Wrong physical dimensions and
currency are tested at canonical/native binding admission, with no financial
source credit.

The supplied policy reference hashes the complete supplied policy document,
including original numeric spelling. A changed document under an old hash
rejects. This stateless profile permits an explicitly repinned changed document
under a reused revision label; it has no earlier external registration history
with which to establish immutability or authorization.

The original numerical facts contain no economic dates. The default execution
period2026-01-01..2026-01-02 and cutoff2026-01-03 are explicit canonical transport
metadata. Safe alternate execution dates must leave every numerical result
unchanged. No economic date is inferred from them.

## Finite validation and limits

The tests first run the independent oracle on complete originals, then compare
every financial/original output and empty closing state. Reference controls
cover all five signed modes, near/odd ties, every declared precision0..6 in both
units, row/aggregate bridges, signed cancellation, rational/noncent/large amounts,
zero/complete-empty, eight rows/ninth rejection, permutation and policy-conditional
split/merge, content pins, Unicode/raw lexemes and invalid populations/authority.
Native controls additionally require actual IR interpretation, emitted native
C compilation/link/execution, canonical publication loading and a separate
Python-emitted embedded AOT calculation. Wrapper and binding negatives are
explicitly distinguished from native source guards.

Default `array-v1` remains available; audited native tests explicitly select
`compact-v2`. Compiler1GiB/180s, runtime256MiB/60s and publication64MiB limits are
unchanged. Relative ZIP custody avoids Windows long destination paths. These
tests are finite discriminators and do not establish general capacity or an
all-program coverage percentage. The dated terminal qualification below uses
the same frozen financial source and test bytes throughout.

All outputs are unissued calculations. Payment evidence, bank movements, carry,
FX and legal/professional interpretation are outside this selected policy.

## Retained qualification, 24 November 2026

The isolated base was `c80ac34bd7d529742a6223a06f56edd3118785b4`, with compiler
`441f0e7c8cbae3da4538449abfbcf2711991d123f343507098323ec6583445fb`, module
`04db83fff9a18ef5157094ca5d15515006c9952118c3a2828d7f8af3b3ff95a2` and runtime
`77a18c1992ab39bd97977e8b94c9ef0741f557c8c6680d243bed8dcae2b3a6f5`.
All five independent controls remain byte-identical to oracle commit `165212e`.
The 21-file pre-native freeze records LF bytes and 20 transitive locator pins.
This README evidence update happened after the terminal run; financial source,
descriptors, templates, adapter and tests were not changed afterward.

External evidence under
`C:/Projects/Film_TV_participation_dynamic_DSL/artifacts/spl/` includes:

- `numeric-precision-authoring-20261124-a`: final 44 reference/adapter/oracle
  methods passed in 52.843s, with complete source snapshot and pre-native `freeze.json`.
  The earlier 41-method authoring draft is separately retained.
- `numeric-precision-native-20261124-a`: fresh default 103-job Lake build,
  indexed target and both smokes PASS, then actual native and independent
  embedded Python AOT baseline PASS; complete original comparison and extracted
  loader audit retained. Total 46.531340s, with no source/compiled drift.
- `numeric-precision-full-20261124-a`: all 57 methods passed in 2234.391634s total,
  zero failures, errors, skips, expected failures, unexpected successes or
  source/compiled drift. Full ZIP custody has 26,581 CRC-valid entries.
  After extraction to short external `np24b`, 209 original-qualified successful
  publications reloaded and matched the complete independent oracle outputs and
  empty closing state; 128 blocked publications were empty and 26 intentional
  interrupted markers rejected loading. One deliberate trusted-physical
  counterexample is separately labeled and receives no original-fact credit.
  `archive-audit.json` retains these distinctions and full recomputed controls.

The full process audit deduplicates 1,307 actual records: 423 compiler and 884
runtime stages. All passed unchanged budgets; maximum measured compiler child
working set was 366,231,552 bytes and runtime 88,117,248 bytes. Measurements exclude
descendants and parent JSON decoding. Validated native cache reuse is identified
in the retained commands; it is not a fresh-compilation timing. Concurrent
integration/C10/C13 work prevents a quiet-host performance claim. These counts
include preserved and loader-checked publications, not 209 independent methods.

With the pinned repository setup and required builds, the finite cohort is:

```powershell
python -m unittest Tests.test_numeric_precision_oracle Tests.test_numeric_precision_modules
```
