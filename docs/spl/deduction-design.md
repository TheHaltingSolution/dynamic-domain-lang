# Staged deductions and cumulative cost identity

23 November 2026. This independent neutral design precedes executable SPL for
the selected C03 slice. It uses existing core arithmetic, collections and ordered
folds; it does not identify or manufacture a necessary compiler capability.
The [policy](../../cases/deductions/policy.md) and
[neutral fixture](../../cases/deductions/neutral.json) are synthetic
`research_assumption`, not legal/accounting approval or vendor output.

Six explicit variant names distinguish the cost stage and fee base. Define G as
gross receipts, B as selected net receipts, D as admitted eligible cost, f as
fee rate and s as participation share. Gross and net are nonadditive views of
the original receipt, supplied separately with `0 <= net <= gross`.

| Variant | Stage before fee | Fee base | Participation basis | Earned |
| --- | --- | --- | --- | --- |
| pre_basis_gross_fee | B-D | G | B-D-G*f | (B-D-G*f)*s |
| pre_basis_net_fee | B-D | B-D | (B-D)*(1-f) | (B-D)*(1-f)*s |
| pre_share_gross_fee | B | G | B-G*f-D | (B-G*f-D)*s |
| pre_share_net_fee | B | B | B*(1-f)-D | (B*(1-f)-D)*s |
| post_share_gross_fee | B | G | B-G*f | (B-G*f)*s-D |
| post_share_net_fee | B | B | B*(1-f) | B*(1-f)*s-D |

No variant is selected implicitly. G=B1000, D500, f0 and s.8 gives400 before
share versus300 after share. f.1 gives360 for pre-basis/net-fee versus320 for
pre-share/net-fee. G110, B100, D0, f.1 and s.5 gives44.50 gross-fee versus45
net-fee. All arithmetic is exact with no rounding; negative stage balances,
participation basis or earned results block rather than applying a loss floor.

Eligible categories are an explicit unique list of opaque source category IDs.
Unknown/unselected categories are deliberately excluded by this policy, with
their original records retained. Wrong scope or malformed data never becomes a
mere excluded row. Every declared cost, including unused/excluded ones, is
validated. Current cost sequence is a unique nonnegative integer; ascending
sequence supplies contractual ordering for scarce-cap attribution. Physical row
permutation preserves economics.

The cap is cumulative and specific to this policy, variant, scope and purpose.
Opening consumed amount must equal the exact sum of deducted amounts in the
retained historical original-cost records. For each current cost in sequence,
admit zero if excluded; otherwise admit min(original amount, remaining cap).
Retain original amount, category, dates, scope and evidence plus admitted amount,
`eligible_full`, `eligible_capped` or `excluded_category`, and recognition period.
All current cost IDs become recognized, including zero/excluded/capped records.
The selected no-residual policy blocks any later reuse of a recognized original
cost ID, regardless of an unused balance or category change. It does not silently
authorize a residual claim, reversal, new purpose or reclassification.

Cap100/opening consumed80/current eligible30 admits20, closes consumed100 and
retains original cost30/deducted20. A new cost5 in the next period admits0. The
old cost30 cannot return as a newly named residual10 under the same original ID.
Changing IDs to evade source identity is outside this supplied-fact calculation;
source systems must preserve original IDs. Equal totals alone are not authority
to consume a cost twice.

The exact neutral top-level shape is:

```text
schema_version = deduction-neutral/1
case_id, scope, period {start,end}, cutoff, terms
receipts[], costs[], evidence[], opening_state, prior_result?
```

`scope` is `{contract_id,participant_id,pool_id,asset_id,currency}` and currency
is USD. `terms` is `{policy_id,policy_revision,variant,share,fee_rate,cap,
eligible_categories,rounding,allocation,evidence_class}` with policy
`SYNTHETIC-STAGED-DEDUCTIONS-01@1`, `exact_no_rounding`,
`sequence_priority_no_residual` and `research_assumption`. Exact numeric values
are neutral strings, including rational `n/d`; adapters must transport exact
values into existing typed codecs without binary floats.

Receipt records are `{id,scope,gross_amount,net_amount,effective_date,
observed_at,source_ref,evidence_ref}`. Cost records are
`{id,scope,amount,category,sequence,effective_date,observed_at,source_ref,
evidence_ref}`. Evidence is `{id,scope,observed_at,kind}`. IDs are unique within
their categories. All selected-period source observations and retained original
cost evidence precede the exact cutoff. Date recognition is half-open, and an
event date cannot follow its observation. This is a supplied complete input
view, not a raw multi-period intake adapter or inference of cash actually paid.

Opening and closing state have exactly:

```text
scope, purpose = distribution_deduction, policy_id, policy_revision, variant
cap_limit, cap_consumed, cost_history[]
boundary, origin, source_case_id
```

Historical entries preserve every original cost field and add
`deducted,disposition,recognized_period {start,end}`. Genesis is explicit zero
consumed/empty history with source_case_id/origin `genesis`. Successor input is
the exactly serialized prior closing state, adjacent boundary, origin
`prior_result`, and matching source_case_id. The separately supplied predecessor
summary is `{source_case_id,period,closing_state,result_ref?}`. The optional
external result reference is retained provenance; the oracle does not compute
or authenticate a canonical semantic digest. Generic canonical state metadata
must retain its actual predecessor digest separately.

The standard-library-only oracle returns exact intermediates for every stage,
eligible/excluded/unadmitted costs, fee measurement, cost-level cap attribution,
earned entitlement and closing state. It consumes neutral original facts, not
SPL or compiler-projected bindings. `exact_json` serializes Fraction controls and
state for neutral replay. Receipt and cost evidence IDs, original IDs and cost
sequence survive this boundary.

Required controls cover all six variants, eligible subset exclusion, scarce-cap
sequence, split/permutation where policy permits, cap equality/exhaustion,
serialized adjacent periods, duplicate cost history, attempted prior consumption,
wrong scope/purpose/policy/variant, malformed/late facts/evidence and negative
stage rejection. Signed returns/losses, fee caps, general deduction percentages,
residual carry, reclassification, cross-purpose reuse, arbitrary chronology,
payment execution and professional interpretation remain outside this slice.

Independent oracle authoring check: `python -m unittest
Tests.test_deduction_oracle -v` passed all 17 test methods in 0.029 seconds on
23 November 2026, including the six hand-selected stage/base variants and 16
small finite split/permutation pairs. This is oracle evidence only; no native,
emitted or canonical execution was run by this authoring check.
