# Bounded authorized Q4 restatement

`neutral.json` is synthetic neutral accounting input, not derived compiler output.
`restatement.spl` computes the original 100 and restated 90 from applications 500
and 450 at 20%, validates retained bank cash 500 = 450 + 50, and reconciles the
independently disbursed 80 to 10 outstanding as of the February cutoff.
`oracles/revision.py` independently calculates those values using its own exact
number/date/Instant code and no project financial/compiler helpers.

`build_modules.register_revision()` explicitly registers the source, proposed
synthetic policy, interface and single-writer state slots through the generic
canonical module API. `revision_package()` mechanically transports the source
records, binds the registered descriptor and pins the full inputs. It computes
no entitlement or outstanding amount. Original-run and opening-snapshot references
are typed source fields because this manifest version has no original-run field.

```python
from cases.revision.build_modules import ROOT, revision_package
from spl_compiler.modules import run_module_package

result = run_module_package(revision_package(), ROOT)
assert result["status"] == "calculated"
assert result["results"]["comparison"]["outstanding_asof"] == "10"
```

Run `python -m unittest Tests.test_revision -v` with the README Python and pinned
Lean setup. The default compares independent reference, native interpretation and
emitted Lean. `SPL_REVISION_REFERENCE_ONLY=1` selects a fast reference-only check
for development while native code is changing; it is not native acceptance.

Entitlement and recognized correction are affected-period candidate state. Actual
paid/outstanding outputs explicitly use the observation cutoff; January payment
is not presented as December cash. Repeating the immutable reconstruction is
deterministic; consuming the original run's closing instead of original opening,
or attempting a second recognition, blocks. Preview never publishes consumable
state. All results remain unissued and no new cash or prospective offset occurs.

This is one selected synthetic authorized restatement route. See `policy.md` for
its exact assumptions and rejected variants. It does not implement arbitrary
historical dependency replay, a universal contractual approval or transaction
safety for concurrent commits.
