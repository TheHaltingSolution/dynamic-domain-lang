# Composed Readable SPL certification cases

These authored examples exercise the comparative certificate across features
used together. The [registered share schedule](registered-share-readable.spl)
uses registered unique rule selection and exact half-even rounding. Its
[sample](share-bindings.json) applies the direct rate to USD 0.03. An exact
50% share is USD 0.015 and rounds to USD 0.02. Overlapping direct and renewal
eligibility fails with `AMBIGUOUS_RULE`.

The [quarterly recovery schedule](advance-recovery-readable.spl) combines
versioned receipt and posted-cost validators, ranked rules, linked USD
rounding, and a stateful recovery ledger. The ledger carries the remaining
advance, scope identifiers and next opening boundary. The
[policy](policy.md) states those validation and settlement rules. The
[module reference](reference.json) pins the registered source and dependency
closure, including the [validation appendices](../validation/README.md) and
[money-rounding library](../numeric-precision/money-rounding.spl).

## Worked results

The fixture opens with an advance of USD 0.20. The launch and volume rules
both apply in Q1. The launch rule ranks higher. Q2 qualifies for volume and
Q3 uses the fallback. The following results follow from the fixture's exact
receipt and cost amounts and the policy's half-even cent rounding.

| 2026 quarter | Receipts less posted costs | Selected rate | Exact share | Rounded earned | Recouped | Payable | Closing advance |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| Q1 | 0.27 − 0.02 = 0.25 | 50% | 0.125 | 0.12 | 0.12 | 0.00 | 0.08 |
| Q2 | 0.66 − 0.12 = 0.54 | 25% | 0.135 | 0.14 | 0.08 | 0.06 | 0.00 |
| Q3 | 0.06 − 0.01 = 0.05 | 10% | 0.005 | 0.00 | 0.00 | 0.00 | 0.00 |

Each close sets the next opening date to the current quarter's exclusive end.
The [series fixture](advance-recovery-bindings.json) supplies all three
quarters and the typed initial ledger. The tests also reject a later receipt
dated at the period end, a negative initial advance, an incompatible pool,
and a skipped quarter. A failed series returns no partial settlement or
closing state. [Focused tests](../../Tests/test_verification_combinations.py)

## Check and run

After the pinned Lake build, use a fresh output directory for the manifest
and certificate. One example is shown below.

```powershell
python -m cases.verification-combinations.link_manifest work/link.json
python -m spl_compiler.verification certify `
  cases/verification-combinations/advance-recovery-readable.spl work/recovery `
  --link work/link.json --mode series
python -m spl_compiler.verification run `
  work/recovery cases/verification-combinations/advance-recovery-bindings.json
```

The two fixtures enter the tracked case census as the standalone registered
share source and the quarterly recovery descriptor. The certificate claims
apply to the selected emitted artifact. The worked examples independently
check the stated economic choices for particular inputs. [Verification design](../../docs/spl/general-verification-design.md)
