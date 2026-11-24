# Finite rounding interaction controls

The disclosed development corpus in
[interaction_cases.py](../../validation/interaction_cases.py) has five finite
dimensions: five supported rounding modes, row/aggregate rounding, positive/
negative/mixed/empty-zero populations, split/merged original rows, and safe/
demanded-failure execution. Their complete Cartesian product is **160 feasible
configurations**. Modes are source literals, as required by the current SPL
checker; a supplied dynamic mode is not silently admitted.

The deterministic selector retains all **40 mode/stage/sign triples** with safe
split input. It adds the two actual half-even split/merge discriminators, then
greedily covers the remaining feasible pairs with enumeration-order tie breaks.
The resulting **47 configurations cover all 86 required pairs**. The attached
contract enumerates the domains, selected count and uncovered pairs. A pair
count describes supplied configuration values, not financial policy adequacy or
compiler decision coverage. Failed configurations cannot substitute for the
mandatory safe financial triples.

The original amounts are two USD0.01 rows, two negative-cent rows, a mixed
USD0.01/USD0.01/USD-0.01 population, or an empty population. Merging supplies their
original exact sum. The selected half-rate and USD0.01 quantum expose positive
and negative half-cent cells. Controls derive rounding using integer quotient,
remainder, sign and exact `Fraction` arithmetic, without SPL calculation,
projection or rounding helpers. The separately implemented finite-control JSON
encoder is reused only for exact output representation.

Every successful case checks exact unrounded half-rate earnings, selected
rounded earnings and closing balance from an exact one-third opening. Demanded
division failure must discard the earlier raw output and all closing state.
The native interpreter's observation report remains distinct from emitted-target
decision instrumentation.

Policy-conditional metamorphic controls check input permutation for all 40 safe
triples. Aggregate rounding also permits split/merge invariance. Row rounding
does not: two positive cent rows at half-rate and half-even produce zero when
rounded by row, versus USD0.01 when merged first. This discriminator is retained
through native execution rather than declared an invariant that would erase
the intended policy difference.

## Executed evidence

`C:/Projects/Film_TV_participation_dynamic_DSL/artifacts/spl/interactions-20261123-a/summary.json`
records all 47 selected cases passing reference, native IR and native-emitted
Lean in **163.763243 seconds**. It retains exact source/bindings/independent
controls, emitted source, every backend outcome and native observation report.
All relevant source pins and compiler/runtime/module identities remain unchanged
before and after execution. Unrelated case authoring and standalone-driver
changes are explicitly outside that run's dependency freeze. Matrix witnesses
were not executed by this cohort.

The denominator/reference/metamorphic checks also pass separately. They do not
establish arbitrary state/scope/gate combinations, canonical payment semantics,
all grammar/type/operator paths, a mutation adequacy percentage, holdout
performance or a compiler proof. Those remain separately inventoried work.

The general command now supports this corpus:

```powershell
python scripts/spl_conformance.py --corpus interactions --generated-only --output NEW_DIRECTORY
```

That CLI also freezes the broader working checkout, so run it when unrelated
captured files are stable. `--corpus combined` retains its earlier meaning:
amount boundaries plus decision cells. Historical campaigns are not redefined.
