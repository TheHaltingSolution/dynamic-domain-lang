# Synthetic Download participation

Implemented M1b in the verified local `0.4.3-dev` baseline on
`feature/spl-typed-quantities`, based on merged `018dde1`. `main` is unchanged;
this local baseline record includes no GitHub release or push. The historical
M1a `0.4.2-dev` record is [archived](../../docs/spl/baselines/implementation-0.4.2-dev.json).

The independent neutral input is `neutral.json`. The proposed policy computes
100 Download times USD 1.50/Download = USD 150, then applies the separately
declared participation of 50% to obtain USD 75. `adapter.py` only transports
facts, normalizes exact numeric notation and constructs registration bindings.
`download-participation.spl` performs the economic calculation.

Each supplied usage row belongs to the half-open selected period, has a unique
record identity and references a supplied evidence event. Every supplied usage
and evidence observation must precede cutoff, including unused evidence. This
is a selected period view, not a claim to ingest or filter a raw ledger.
Nonnegative quantities, rates and opening meter are explicit case policy.
Empty usage and empty evidence are valid zero activity; supplied usage still
requires its evidence. No rounding or payment occurs.

The opening and closing meter use tagged Quantity transport. Its complete type
hash occurs in slot unit, cell unit, scope unit and state key. A successor is a
separate invocation consuming the actual prior closing cell (remove its
audit-only `movement` field), with explicitly supplied new period and facts.
Nested dimension-containing state requires the same full-type identity rule.

The generic core dictionary `spl.units/1` admits Download and UsageMinute; this
source selects Download. Its descriptor explicitly declares `spl.quantities/1`,
codec `spl-quantity/1` and the used unit dictionary. These declarations and all
local/export signatures are checked across the full import closure. Prices are
typed `Rate<Download,USD>` parameters; no English literal grammar was added.
See the [operation matrix](../../docs/spl/next-core-semantics.md#m1b-implemented-dimensional-boundary)
and [module/state boundary](../../docs/spl/module-interface-v1.md#m1b-dimensional-interfaces-and-state)
for matching bounds/conservation, typed zero, explicit rounding, containers,
sorting/key restrictions and the AST/checked-Type hash helper. Money/Quantity
and FX remain unsupported. The new paths do not extend existing scalar proofs.

Reproduce from the repository with the pinned Python environment:

```powershell
python scripts/quantity_demo.py
python -m unittest Tests.test_quantities Tests.test_quantity_modules Tests.test_native_quantities
```

The demo writes a review bundle to the external project artifacts folder
(override with `--output`). All four cases passed comparison and independent
financial controls: 100 Download, a serialized successor carrying another
0.5 Download, empty activity and one-third Download.

The checked-in package deliberately has unbound implementation identities.
For direct Python use, bind immediately before execution:

```python
from cases.quantities.adapter import ROOT, quantity_package
from spl_compiler.modules import bind_module_package, run_module_package

package = bind_module_package(quantity_package(), ROOT)
result = run_module_package(package, ROOT, backend="compare")
```

The demo compares reference, native interpretation and generated Lean results
with the independent `oracles/quantities.py` controls; it also consumes actual
serialized successor carry. Policy status remains proposed and calculation
unissued.

Focused verification passed the 86-target native build, both smokes/native
quantity suite, 15 dimensional reference checks, one actual Python-emitted Lean
regression, 13 canonical module checks and eight independent oracle checks.
Five comprehensive checks passed in 36.712 seconds across independent reference,
native interpretation, native-generated Lean and Python-emitted Lean, including
tuple dimensional sorting/comparison. Native/reference/generated runs agree
with neutral controls for 100, zero and one-third Download. The actual native
successor gives 100.5 Download carried and USD 0.375 earned. These focused
results are recorded separately from the final combined verification.

Final verification passed all 352 Python tests in a single combined run
(1638.702 seconds), 16 native suites, the 86-target build and both smokes.
All 35 review paths passed: 24 legacy, four quantity and seven M1a paths.
Implementation identities and source pins remained unchanged. The external
`quantity-0.4.3/checks/verification.json` records status `passed`; the result
does not extend compiler proof scope or the supported dimensional vocabulary.
