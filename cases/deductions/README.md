# Staged deductions and original-cost cap history

This registered `spl-module/1` method implements the six selected synthetic
[stage/base policies](policy.md) from the independent
[neutral design](../../docs/spl/deduction-design.md). It uses the existing native
SPL frontend, pure imported functions, exact USD arithmetic and ordered folds.
It adds no compiler capability, currency, rounding default or source-language
interpretation rule.

Six stage/base names do not imply six independently money-changing methods.
Under this exact/no-rounding policy, `pre_basis_gross_fee` and
`pre_share_gross_fee` have equal monetary results. Their stage/lineage observations
remain distinct. Financial mutation adequacy must classify this equivalence
explicitly rather than counting a changed label as a monetary kill.

`stages.spl` is the reusable financial library. `deductions.spl` validates the
original receipt/cost/evidence records and scoped opening history, allocates the
cumulative eligible-cost cap in authorized unique sequence and calls that
library. Gross and net remain separate views of each original receipt. The
original cost amount and identity survive every exclusion and partial admission;
no unadmitted remainder is carried for a later claim under the same original ID.

| Selected control | Expected exact result |
| --- | --- |
| G=B1000, cost500, share.8, fee0 | Pre-share400; post-share300 |
| Same, fee.1 measured on selected stage net | Pre-basis360; pre-share320 |
| Gross110/net100, no cost, share.5, fee.1 | Gross-fee44.5; net-fee45 |
| Cap100, original costs80 then30 then5 in adjacent closes | Admitted80/20/0; consumed80/100/100; full originals retained |
| Two current80 costs and remaining cap100 | Authorized sequence admits80/20; physical row permutation preserves attribution |

Original cost IDs, categories, source references and evidence references remain
opaque source text. The language's admitted finite ordering key is the already
validated unique numeric sequence. The fold uses that same sequence for event
identity while retaining the original text ID in the full event and history.
Finite lists/filter/count validate duplicate and previously recognized IDs;
the adapter does not invent typed IDs, concatenate tokens or rely on a Text map
key that this core does not admit.

The adapter in `build_modules.py` checks exact physical records and event/date
consistency, tags money and transports original facts. It does not choose
eligible categories, compute the fee, allocate cap or project a solved answer.
The independent [oracle](../../oracles/staged_deductions.py) was authored against
neutral facts before these SPL sources and imports no compiler calculation code.

```python
from cases.deductions.build_modules import (
    register_deductions, deduction_package, run_deduction_package,
)

reference = register_deductions()
package = deduction_package(reference=reference)
result = run_deduction_package(package, backend="compare")
```

Run the builder from the checkout to deliberately refresh development descriptors
and the unbound checked-in package template:

```powershell
python -m cases.deductions.build_modules
python -m unittest Tests.test_deduction_oracle Tests.test_deduction_modules -v
```

The pinned Python executable and Lean setup are in the root README. Do not
refresh registrations concurrently with canonical execution. The on-disk
`canonical-package.json` deliberately has unbound build/closure fields; bind a
fresh invocation before execution. Positive tests use an isolated copied registry
and explicit `compare` mode, comparing reference, native IR and native-emitted
Lean along with independently computed material intermediates and complete
original-cost history. Reference-only negative groups identify their own scope.

An adjacent canonical successor consumes the actual serialized closing cell.
`neutral_state` mechanically decodes its typed quantity for neutral replay; its
actual `prior_result_ref` is retained separately from the neutral case ID.
The supplied opening snapshot, structured state cell and predecessor summary
must agree. Policy revision, variant, cap limit, purpose, scope and boundary
cannot be silently amended during ordinary carry. Historical deducted amounts
must reconcile to consumed cap, and all retained original facts/evidence still
validate before the current exact cutoff.

The descriptor explicitly permits an empty evidence array for an entirely empty
close, as the neutral policy requires. Every supplied current or historical fact
still needs a valid evidence reference, so deleting evidence from a nonempty
close blocks. Nonempty evidence retains the generic authority/cutoff checks.
Typed Instant outputs use canonical UTC spellings; independent controls compare
their exact chronology rather than requiring the original offset spelling.
The original neutral fixture bytes remain the source record.

Outputs expose every stage balance/fee base, eligible/excluded/unadmitted totals,
earned entitlement, cost-level original/admitted/disposition detail, reconciliation
and one structured closing ledger. They do not establish issued or actually paid
amounts. The policy remains `research_assumption`; signed returns/losses, residual
claims/reclassification, fee caps, arbitrary deduction percentages, chronology
replay, FX and professional contract interpretation are outside this slice.

Verification on 23 November 2026: one combined run passed all 29 oracle/module
test methods in 178.194 seconds, with no skips. Its source pins and compiler,
runtime and generic-module identities remained unchanged. The external record is
`C:/Projects/Film_TV_participation_dynamic_DSL/artifacts/spl/deduction-module-checks-b/verification.json`
with the full log alongside it. The initial authoring failures remain separately
preserved in `deduction-module-checks-a`; they concerned optional-empty evidence
metadata and comparison of equivalent UTC-offset spellings, both resolved before
the passing combined run. This slice does not claim a fresh full-repository pass.
