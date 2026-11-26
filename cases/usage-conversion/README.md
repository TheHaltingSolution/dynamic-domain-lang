# Declared usage-unit module fixtures

The original [neutral facts](neutral.json), [selected policy](policy.md) and
independent `oracles/usage_conversion.py` controls are unchanged. The source
fixtures implement exactly sixty UsageMinute per UsageHour through the admitted
`spl.usage-time/1:minute-hour` relation. Original 90 Minute at an original quote
of USD12 per Hour gives 1.5 Hour and USD18. The builder transports the original
tagged magnitude and quote; it never supplies the converted amount or earnings.

| Source/registration | Purpose |
| --- | --- |
| `base-minute-meter` | Existing Minute encoding, USD-per-Minute quote and original Minute meter |
| `base-download-meter` | Existing Download encoding and unchanged dimensional state identity |
| `minute-meter` | Derived Hour output while keeping original stored Minute quantities |
| `hour-meter` | Explicit Hour genesis and definition-bound Hour successor state |
| `convert-library`, `inferred-import` | Extended callee returns Hour; base caller infers, adds and emits it without lexical Hour admission |
| `usd-library`, `unused-extended` | Unused extended dependency with only USD values still requires root IR0.2 |
| `base-library`, `base-custom-import`, `extended-base-import` | Existing custom `convert_quantity` function remains available in base mode and can be renamed by an extended caller |

Each source and descriptor has an explicit content pin. `build_modules.py`
authors registrations deliberately and writes unbound package templates. Existing
issued packages are not silently repinned during execution. Source files and
generated descriptor/template JSON use LF. Recreate these artifacts from the
repository root with an interpreter that imports this checkout:

```powershell
python -c "import sys,runpy;from pathlib import Path;sys.path.insert(0,str(Path.cwd()));runpy.run_module('cases.usage-conversion.build_modules',run_name='__main__')"
```

`register_all(root)` can create an isolated temporary registry.
`usage_package(name, neutral, root=..., reference=..., bind=False)` transports a
selected original input into an unbound package. `bind_module_package` records
the actual implementation/module closure pins. The templates contain an explicit
zero genesis only; an adjacent run must transport its actual previous closing
cell and update the accounting period. The complete original measurement/quote
IDs and evidence references remain in `neutral.json` and external source
snapshots; the numerical source ports are the original tagged quantity and price.
The adapter's narrow profile checks are transport-stage failures and are not
claimed as native execution.

The interface tests verify catalog declarations, owner-local unused signatures,
source header coherence, recursive state identities, actual serialized carry,
legacy alias behavior and canonical failure stages. Native comparison additionally
requires the coordinated core release; authoring/reference checks alone do not
establish extension acceptance. The external verification record identifies
which commands actually ran, implementation pins and module origins.

No FX, new currency, timezone conversion, financial-policy default or automatic
state migration is introduced. Retagging a stored Minute cell as Hour is rejected;
conversion occurs only through the explicit source operation.
