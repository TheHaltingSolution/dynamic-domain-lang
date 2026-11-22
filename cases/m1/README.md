# M1a financial library

This bounded synthetic witness adds reusable exact USD functions rather than a
compiler/backend branch. Read [policy.md](policy.md) for the selected economic
meaning and exclusions. The registered modules are `tiers.spl` (marginal and
period whole-base), `cumulative-tiers.spl`, `cap.spl`, and `guarantee.spl`.
`ordinary.spl` validates facts and scope and composes those functions. Imported
functions own no state; the canonical root owns one structured, scoped meter.

Neutral source facts live in `fixtures/*.json`. `m1-neutral/1` contains `scope`
(contract, participant, pool, asset, USD), half-open `period`, strict `cutoff`,
`facts` (identity, amount, effective and observation dates, evidence identity),
`evidence`, selected `policy`, and `opening_state` (scope, method, balance,
period). Tiers declare identity, unique nonnegative sequence, exact lower and
upper thresholds, and ratio rate. JSON null means only an unbounded neutral
upper threshold; canonical transport uses typed `Option` tags. Amounts and rates
are exact strings or integers; floats and booleans are rejected. A fact can
explicitly supply scope, which must match the run. No financial arithmetic
occurs in `build_modules.py`.

The neutral schema version must be exactly `m1-neutral/1`. A tier sequence is
an actual nonnegative JSON integer; a string such as `"1"`, a boolean or a
floating-point value is rejected rather than coerced. The demo retains and
hashes the fixture bytes loaded before execution.

The public adapter API is `register_m1()` and `m1_package(fixture,
reference=reference)`. Registration is an explicit authoring action; execution
does not silently repin issued packages. Run from the repository root:

```powershell
python -m cases.m1.build_modules
python -m unittest Tests.test_m1_modules -v
```

Checked-in `*-canonical-package.json` files are deliberately unbound. Call
`bind_module_package(package, ROOT)` before `run_module_package(package, ROOT)`.
The default comparison backend checks reference evaluation, native typed IR and
generated Lean execution. `SPL_M1_BACKEND=reference` is a fast development check.
`Tests/test_m1_modules.py` compares every accepted result with the independent
`oracles/ordinary_royalties.py` oracle and includes serialized canonical carry.

The same templates use the generic CLI, without a new M1 backend command:

```powershell
python -m spl_compiler module-bind cases/m1/period-marginal-canonical-package.json .lake/m1-bound.json --registry .
python -m spl_compiler module-run .lake/m1-bound.json --registry . --output .lake/m1-cli
```

Named `results.comparison` fields are `basis`, `uncapped`, `entitlement` and
`closing_balance`. `results.settlements` supplies the participant statement.
The `meter` state cell stores tagged USD balance, method and recorded period,
with canonical scope/purpose/boundary/provenance and predecessor reference.
Carry actual serialized closing cells into a successor after removing their
`movement` field, as exercised by the tests. Cumulative cap never resets;
period cap requires an explicit reset at a new period. Reusing a different
method's balance fails.

Direct serialized carry requires adjacent canonical boundaries. A gap needs an
explicit authorized opening/boundary roll-forward. Duplicate fact guards apply
within one run; the meter is not a consumed-fact registry or a general replay/
idempotency mechanism.

These checks establish finite synthetic calculation witnesses. They do not
complete all C04/C05 variants, approve commercial terms, implement recoupable
guarantee/cap precedence, or prove compiler correctness or production capacity.
