# Selected synthetic C03/C07 composition

`waterfall.spl` executes gross-based fee, eligible costs, available funds,
competing capital recovery and weighted residual allocation. It imports the
actual pure function in `proportional.spl`. `build_modules.py` explicitly
registers typed ports, policy pins and one shared structured claim-state writer,
and transports neutral records without financial calculation. No backend
dispatch or JSON financial expression is added.

The policy is [policy.md](policy.md), with proposed synthetic status. These files
do not establish professional approval, filed-agreement interpretation,
historical execution or vendor parity. The optional RR-03 Roundlake seed is used
only for the selected synthetic two-period numbers.

| Neutral fixture | Available funds | Recoveries A / B | Closing claims A / B | Residual A / B |
| --- | ---: | --- | --- | --- |
| `priority-120.json` | 120 | 100 / 20 | 0 / 80 | 0 / 0 |
| `pro-rata-120.json` | 120 | 60 / 60 | 40 / 40 | 0 / 0 |
| `roundlake-like-p1.json` | 100 - 25 - 15 = 60 | 48 / 12 | 32 / 8 | 0 / 0 |
| `roundlake-like-p2.json` | 100 - 25 = 75 | 32 / 8 | 0 / 0 | 17.50 / 17.50 |

Matching `*-expected.json` files record independently computed exact intermediate
controls, every claim movement, residual allocations and closing ledger. The
hand-authored independent implementation is `oracles/waterfall.py`; it imports
only the Python standard library and consumes these neutral records directly.
Reduced rational strings and exact decimal strings represent the same values.

The state cell owner is `capital-beneficiary-group`, explicitly present alongside
`capital-A` and `capital-B` in canonical `scope.participant_ids`. The source
declares this group and its beneficiary roster separately; the descriptor binds
the single shared state cell to that group, project, agreement, pool and purpose.
Individual statements do not narrow or duplicate shared state. Claim priority
and sequence are supplied semantic order, with explicit identity and rejected
ties; physical row position is immaterial.

From the repository root with the pinned README toolchain setup:

```powershell
python -m unittest Tests.test_waterfall -v
```

The default compares the Python reference evaluator, native typed-IR interpreter
and generated Lean execution, then performs strict canonical finalization. The
two-period test reads the published `closing-state.json`, removes only its
movement report, and binds those serialized cells into the next period.
For isolated reference checks before rebuilding native compiler changes:

```powershell
$env:SPL_WATERFALL_BACKEND = 'reference'
python -m unittest Tests.test_waterfall -v
Remove-Item Env:SPL_WATERFALL_BACKEND
```

Fixtures select USD only, exact arithmetic, capital claims, no capital additions,
and gross-based fees before costs. They do not cover every C03/C07 variant.
Tests also cover empty/fully recovered claims, zero cash, duplicate identities,
complete-key ties, cost/claim overapplication, zero allocation denominator,
missing scope/evidence, scoped currency/period and canonical group-state isolation.
