# Proposed Quest two-flow additional-return fixture

This disclosed synthetic method implements
[`DYN02-QUEST-TWOFLOW-NEAREST-EVEN@1`](../../docs/spl/quest-two-flow-fixture.md).
It calculates only the additional target-return component for one USD obligation,
one full actual principal payment and one linked application. Project-owner
acceptance of the adjacent patent-rights domain remains pending. Monthly and
combined liability are unresolved; the additional charge is calculated and
unissued, with no additional-payment event supplied.

Compare the [financial SPL](charge.spl) with its [readable policy](policy.md),
the [original neutral facts](neutral.json), and the [fixture specification](../../docs/spl/quest-two-flow-fixture.md).
The [source index](source-index.json) records the actual SEC filing fingerprint;
the original downloaded HTML remains outside Git in the project reference folder.
Fixture amounts, transaction dates and evidence are synthetic.

The existing compiler executes the entire calculation. A pure
[integer-power library](power.spl) uses finite folds and exact ratios. The root
method looks up original due/payment dates in evidenced calendar observations,
subtracts their ordinals, performs an internal cent search, chooses half-even
parity from the **additional-charge** cent index, and asserts exact lower/upper
rounding-cell and minimum-cent certificates before returning results. It adds
no power, root, XIRR or date-difference compiler primitive.

The [adapter](build_modules.py) copies original facts and validates Gregorian
calendar normalization. It does not calculate elapsed days, target powers,
charges or candidate payouts. The [independent oracle](../../oracles/quest.py)
derives days separately from original dates, nominates a cent cell with Decimal
logarithms/exponentials and accepts only exact Fraction certificates. It imports
no compiler helpers and does not feed a solved value into SPL.

The baseline derives 182 days from January 1 to July 2, 2026, keeps actual
principal paid at USD 1,000 and calculates additional USD **95.17**. Minimum
qualifying USD **95.18** remains an alternative/bounding detail, not the selected
result. Mandatory full-year ties distinguish the new method:

| Principal and target | Exact additional | Half-even additional |
| --- | --- | --- |
| USD 0.01 at 50% | 0.005 | **0.00** |
| USD 0.03 at 50% | 0.015 | **0.02** |

These also detect half-away rounding and rounding principal-plus-charge before
subtracting principal. The earlier half-away probe is preserved unchanged.

Run from the repository root with the pinned toolchain/Python setup:

```powershell
lake build
python scripts/quest_demo.py --reuse-registration
python -m unittest Tests.test_quest_oracles Tests.test_quest_modules Tests.test_quest_native -v
```

The demo defaults to native IR/generated Lean/reference comparison plus the
independent neutral-fact controls. It writes a review bundle under the external
`artifacts/spl/quest-two-flow/review` folder. It includes nine original-fact
scenarios: baseline, both exact ties, nearby values, zero days, a full year,
alternate principal/rate, and a non-origin due date that must yield two days.
Use `--backend reference` only when intentionally selecting reference execution;
its summary identifies that narrower scope.

`power-module.json` and `charge-module.json` pin the pure library/root and
proposed readable policy. The checked-in `package.json` is deliberately unbound;
`quest_package()` binds a fresh run to the current existing kernel. This method
has no opening or closing financial state and does not assert idempotent payment
application across runs. Both the selected policy and source/calendar identities
remain visible in canonical policy review, result detail and trace.

The calendar profile admits the five explicitly pinned Gregorian facts in
`calendar-facts.json`. Additional dates require deliberate calendar/profile
revision; data changes cannot silently alter the day count. The numerical method
requires principal at least USD 0.01, nonnegative target, integral elapsed days
0 through 365, and `ceil(principal * target / USD 0.01) < 2^24`. Nine power
slots and 24 search slots are engineering budgets, not agreement terms or proof
of useful capacity for arbitrary rational magnitudes. Existing resource limits
still apply.

All 34 supplemental tests pass in one 402.120-second run: 20 oracle, nine
canonical and five direct execution groups, including native IR/generated Lean
comparisons, 26 invalid-input mutations and two incorrect-rounding source
mutations. All nine author-facing demo scenarios also pass full comparison and
independent exact certificates. The 86-target build and both smokes pass;
compiler/schema pins, implementation identities, the old baseline record and
original half-away probe remain unchanged. The earlier 352-test baseline was
not rerun or republished. A separate compatibility rerun passes six original/
readable SV, RQ-07 and LG cases plus three advance/reserve/correction mechanisms,
retaining the USD 18,000/35 and 5,000/20/10 controls. Existing toy/scalar proofs do not establish this
method's correctness. The unchanged-language fit
does not establish general XIRR, Excel operational equivalence, whole-contract
compliance, professional approval or a necessary new core capability.
