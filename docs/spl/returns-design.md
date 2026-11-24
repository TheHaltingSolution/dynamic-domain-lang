# Original-rate returns and explicit loss variants

23 November 2026. This independent neutral C08 design precedes executable SPL.
It uses exact arithmetic and generic records, maps and folds; no new primitive
or financially necessary compiler gap is presumed. All variants are synthetic
`research_assumption` under
[SYNTHETIC-RETURNS-LOSSES-01@1](../../cases/returns/policy.md). They are not
professional contract interpretation, original account approval or bank execution.

The [neutral fixture](../../cases/returns/neutral.json) retains a historical
original B measurement of USD 80 at rate .5, with original date December 15,
2025 and source/evidence. A current return of measurement 80 recognizes a signed
effect of -40 in Q1 2026. B's separate current rate .8 cannot change that old
effect to -64. A current A sale of 100 at rate 1 earns 100. Registering B's
historical original does not reearn its old 40 or assert anything about issued,
paid, refundable or recoverable cash.

Let E_t be current title earnings minus original-rate return effects. Named
methods deliberately differ:

| Method | Calculation | Baseline |
| --- | --- | --- |
| signed_pool | Sum(E_t) | 100-40 = 60 |
| per_title_floor | Sum(max(E_t,0)) | 100+0 = 100 |
| pooled_loss_carry | Result=max(Sum(E_t)-L,0); closing L=max(L-Sum(E_t),0) | Depends on supplied prior loss |

The separate carry witness has return-only current -40 from original B, zero
opening loss, result zero and closing loss 40. With that exact serialized state,
new positive 30 in the next adjacent period yields result zero and closing loss
10. A further positive 20 would absorb the remaining 10 and recognize 10. Carry
reconciles `signed_current + closing_loss = result + opening_loss`. The original
returned-basis meter is separate from the pooled monetary loss meter.

Every raw sale/return magnitude and original basis is nonnegative; signs are
calculated effects. Exact rates lie in `[0,1]`; all calculations retain rational
precision with no implicit cent rounding. A return references an original
measurement ID, repeats its asset and pool scope, and uses that original rate.
Multiple partial returns may consume the remaining original basis across
periods, but their cumulative measurement cannot exceed the original. Current
rates apply only to new current sale measurements.

Current sales also become registered originals. Same-period returns against
those new originals are permitted when measurement date is no later than return
date, return date no later than current recognition date, and original observation
no later than return observation. Current sale earnings are counted once and
then reduced by the linked returned portion. Historical imports require a
measurement date before the selected period. Recognition is the explicitly
supplied current-period route, not a reconstruction/rewrite of the old period.
All supplied observations and referenced evidence precede the exact cutoff.

The exact neutral structure is:

```text
schema_version = returns-neutral/1
case_id, scope, asset_ids[], period {start,end}, cutoff, policy
current_rates[], originals[], sales[], returns[], evidence[]
opening_state, prior_result?
```

Pool scope is exactly `{contract_id,participant_id,pool_id,currency}`, with USD
currency. An explicit nonempty unique `asset_ids` universe scopes title results,
including zero activity. Every fact repeats pool scope and its asset ID; an
original and its linked return must refer to the same asset. Current rates are
one row per member asset with
`{asset_id,rate,scope,effective:{start,end},observed_at,source_ref,evidence_ref}`;
their effective intervals cover the selected period.

Historical `originals` rows contain
`{id,asset_id,scope,basis,rate,measurement_date,observed_at,source_ref,evidence_ref}`.
Current `sales` contain
`{id,asset_id,scope,basis,effective_date,observed_at,source_ref,evidence_ref}`.
`returns` contain
`{id,original_id,asset_id,scope,returned_basis,return_date,recognition_date,
observed_at,source_ref,evidence_ref}`. Evidence is
`{id,scope,observed_at,kind}`. Exact financial values are strings, including
rational n/d; binary floats are invalid. Original/source identities must remain
stable; renaming a source event to evade history is outside the supplied-fact
calculation and is not authorized by this policy.

`policy` is `{id,revision,method,recognition,measurement,rounding,evidence_class}`,
pinning `SYNTHETIC-RETURNS-LOSSES-01@1`, one explicit method,
`supplied_current_period`, `original_basis_original_rate`, `exact_no_rounding`
and `research_assumption`. No absent method defaults to signed pooling, a floor
or a loss meter.

Opening and closing state contain exactly:

```text
scope, asset_ids[], purpose = returns_and_loss, policy_id, policy_revision, method
boundary, origin, source_case_id, loss_carry
original_registry[], recognized_ids[]
```

Registry entries preserve original row fields and add `returned_basis`,
`origin_kind` (`historical_import` or `current_sale`) and `registered_case_id`.
Current sales are converted mechanically into original measurement records using
their effective date and supplied current rate, then retained even after full
return. Already registered original IDs cannot be supplied again as new historical
imports or current measurements. History retains category-qualified recognition
tokens so duplicate returns cannot be reapplied after date changes or across
periods. Original imports and current sales share the original-registry namespace;
return event IDs are a different category.

Genesis has zero loss, empty registry/history and origin/source_case_id `genesis`.
Historical originals supplied in that run are explicit previously unreturned
measurement snapshots, not reconstructed original earnings/payment histories.
Successor opening is the exactly serialized previous closing snapshot, with
adjacent boundary and matching `{source_case_id,period,closing_state,result_ref?}`
predecessor summary. Optional external result_ref is provenance, not a digest
computed/authenticated by the oracle. Canonical state metadata must separately
retain its actual prior-result digest. Ordinary carry pins method and scope;
it cannot silently reset a loss or cross to another title universe.

The standard-library oracle `returns_losses(data)` returns title/current/return
intermediates, original-rate effects, per-original consumed/remaining measurement,
pool signed earnings, explicitly named recognized entitlement, loss movements
and closing state. `exact_json` serializes Fraction controls for neutral carry.
No field represents actual bank refunds or paid cash. Exact duplicate replay,
scope, original-rate/source preservation, partial cumulative returns, date/cutoff
edges, signed/floored methods and serialized pooled loss carry are required tests.
General returns recognition, tax, FX, payment execution, historic correction,
amendment/reset authority, reserve linkage and full C08 family coverage remain
outside this finite slice.

Independent authoring check on 23 November 2026: `python -m unittest
Tests.test_returns_oracle -v` passed all 17 test methods in 0.022 seconds.
This verifies neutral controls and synthetic policy boundaries only. Native,
emitted and canonical comparisons require separate integration evidence.
