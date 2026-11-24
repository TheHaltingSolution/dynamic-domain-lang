# Linked returns and named loss policies

`SYNTHETIC-RETURNS-LOSSES-01`, revision `1`. These are explicitly selected
synthetic `research_assumption` variants. None supplies a default contract loss
rule, bank refund, actual payment, issuance, historical restatement or clawback.

Register each original measurement with its original basis, rate, asset, scope,
date, source and evidence. Historical original snapshots are reference data;
registering them does not earn their positive entitlement again. The selected
genesis supplies previously unreturned original measurements, with zero loss
carry and empty recognized history. Their historical paid/issued status is not
asserted. Each current sale also registers an original measurement at its
separately supplied current rate for possible future returns.

Return records contain nonnegative measurement magnitudes. Calculate the signed
effect by multiplying that magnitude by the linked **original** rate and
negating it. Never reprice an old return at a current rate. Across all periods,
returned measurement cannot exceed the original basis. Preserve original IDs,
rates, dates, source/evidence and cumulative returned basis in structured state,
including fully returned originals. No physical row order controls economics.

Both current sales and supplied return recognition dates belong to the selected
half-open period. An original measurement precedes or equals its return date,
and return date precedes or equals recognition. A same-period return may target
a new current sale after its original observation; that sale is earned once,
then its linked return reverses only the returned portion. Explicit observations
and evidence precede the exact cutoff. Missing scope, evidence, original IDs,
duplicate or previously recognized events, and excessive cumulative returns block.

For each title t, let E_t be current sale basis times current rate, less returned
measurement times its linked original rate. Choose one named variant:

| Method | Calculated result | Closing loss carry |
| --- | --- | --- |
| signed_pool | Sum(E_t), which may be negative | Zero; opening loss must be zero |
| per_title_floor | Sum(max(E_t,0)) | Zero; opening loss must be zero |
| pooled_loss_carry | max(Sum(E_t)-opening_loss,0) | max(opening_loss-Sum(E_t),0) |

Floors apply at the stated stage only. Prior loss is neither a new return nor
another current expense. The loss-carry variant preserves
`signed_current + closing_loss = calculated_result + opening_loss`. A negative
signed-pool result is a calculation delta, not a bank payable or instruction.
The nonnegative result in the loss-carry method is a calculated earning credit,
not an issued or actually paid amount.

Baseline A current basis 100 at rate 1 earns 100. B's historical basis 80 at
original rate .5 earned 40 in its original measurement; the current full return
reverses 40 even though B's separately supplied current rate is .8. Signed
pooling gives 60; flooring each title before pooling gives 100. In the separate
pooled-loss-carry scenario, return-only negative 40 creates loss 40. The next
period's positive 30 yields result zero and remaining loss 10.

Opening state pins the economic pool, title universe, policy, selected method,
purpose and adjacent boundary. Successor carry uses the actual serialized prior
closing snapshot plus matching predecessor summary. Original measurement IDs
occupy one registry namespace; event recognition uses category-qualified
`originals:id`, `sales:id`, `returns:id` history. Switching loss methods, resetting
loss or deleting returned-basis history requires a separate authorized policy.
Case IDs identify calculations, not canonical result digests; canonical predecessor
references remain separately supplied metadata.
