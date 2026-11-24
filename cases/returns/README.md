# Original-rate returns and named loss variants

This registered synthetic C08 slice implements
`SYNTHETIC-RETURNS-LOSSES-01@1`, a proposed `research_assumption`. The
[policy](policy.md), [original neutral fixture](neutral.json),
[independent design](../../docs/spl/returns-design.md) and
[oracle](../../oracles/returns_losses.py) precede executable SPL.
It uses existing records, finite lists, filters, folds and an Id-keyed rate
index. No compiler primitive, core or canonical schema change is introduced.

Historical B basis 80 at its original rate .5 has a current return effect -40,
even though B's separately supplied current rate is .8. Historical registration
does not reearn B's old 40. A new A sale of basis 100 at rate 1 earns 100.
The explicitly selected methods differ:

| Method | Selected calculation | Baseline |
| --- | --- | ---: |
| `signed_pool` | Sum current title earnings less original-rate return effects | 60 |
| `per_title_floor` | Floor each title's signed amount at zero, then sum | 100 |
| `pooled_loss_carry` | Credit `max(signed_current - opening_loss, 0)`; carry `max(opening_loss - signed_current, 0)` | 60 with zero opening loss |

A separate return-only loss case creates loss 40 and recognizes no credit. An
adjacent successor earning 30 carries loss 10; another earning 20 consumes that
10 and recognizes credit 10. Reconcile
`signed_current + closing_loss = credit + opening_loss`.
Loss is not a second current return or a new expense.

The original measurement registry is distinct from the monetary loss meter.
Originals retain original basis/rate/asset/scope/date/source/evidence and a
cumulative returned-basis meter, including after full return. Partial returns
of 30 and 50 across actual serialized periods exactly consume original basis
80; a further .01 blocks. They reverse 15 and 25 under the original .5 rate,
regardless of current rates. Registering a new historical or current-sale ID
already in the registry blocks.

Current sales also register originals at their supplied current rates. A
same-period return can reference one after its measurement date and observation;
recognition must be in the selected half-open period and no earlier than the
return date. Original, return and recognition dates remain separate. Every
supplied original/evidence observation is strictly before the exact cutoff.
Category-qualified history prevents a consumed return from being replayed with
new dates in a later invocation of the same recognized history.

Signed-pool negative results are calculated deltas, and nonnegative loss-method
results are calculated earning credits. Neither is a bank payable, refund,
issued amount or actual payment. The source emits no such fields. The generic
wrapper remains `issuance_status = unissued`; its unrelated payment assessment
is not converted into an invented numeric zero.

## Register and verify

Use the repository's pinned Python/Lean setup and a prior successful build:

```powershell
& 'C:/Projects/Film_TV_participation_dynamic_DSL/environment/python/python.exe' -m cases.returns.build_modules
& 'C:/Projects/Film_TV_participation_dynamic_DSL/environment/python/python.exe' -m unittest Tests.test_returns_oracle Tests.test_returns_modules -v
```

The builder deliberately generates `returns-module.json` and three unbound
`*-canonical-package.json` templates, one per named method. Fresh callers use
`returns_package(..., reference=registered_reference, state_cells=...)` and
`run_module_package(..., backend="compare")`. Registration does not repin issued
historical artifacts during calculation. Current method selection and state
method must agree; ordinary carry cannot change methods, reset a loss or remove
returned-measurement history.

Tests register temporary closures, compare every pool/title/sale/return/original
intermediate and closing state to the independent neutral oracle, and identify
actual native comparison groups separately from reference-only negatives.
On 23 November 2026, one combined run passed all 29 methods: 17 independent
oracle and 12 module methods in 129.211 unittest seconds (129.337819 process
seconds), with exit code zero, unchanged checked source/template bytes and
unchanged start/end post-LG-projection-fix build identities. The raw log, exact
pins and source freeze are retained under
`C:/Projects/Film_TV_participation_dynamic_DSL/artifacts/spl/returns-checks-b25e079f`.
This is supplemental bounded-method evidence, not a full repository regression
or full C08 completion.

Successor tests serialize and reread the actual canonical closing cell, remove
its movement annotation and retain its actual `prior_result_ref`. The neutral
predecessor summary must match its case, adjacent period, exact quantity and
separately supplied canonical reference. Case ID is not a result digest. This
establishes consistency of supplied provenance, not cryptographic authentication
of an external historical account or bank transaction.

## Representation and boundary

The adapter performs exact neutral-field/number transport and money tagging.
It does not price sales, reverse returns, build the current registry, calculate
loss or inject solved financial values. SPL registers current originals, uses
original rates for returns, checks cumulative consumption and executes the
selected financial method. Current rates cover the declared title universe and
period; title outputs include zero-activity members.

Event identities remain arbitrary Text, including colons and Unicode. Neutral
history `returns:some:id` is mechanically split at the first colon into
`Tuple<Text,Text>` and joined on neutral export. Text concatenation and Text-keyed
maps are not admitted operators, so original-ID relationships use finite
filter/fold checks. The current rate index uses the already admitted Id<Asset>
key type. Existing agreement/participant/pool/asset IDs retain the compiler's
ASCII opaque-ID profile.

Repeated scans have quadratic validation/aggregation costs for growing registry,
fact and history populations. The verified scenarios are small; no capacity
claim follows from the generic resource guard. Future indexing must preserve
original Text identity, diagnostic/financial ordering and lineage.

The selected historical imports explicitly represent previously unreturned
original measurement snapshots. They do not reconstruct historical earnings,
issued/paid status or source identity fraud. Renaming a real source event to
evade supplied history is outside this calculation's trust boundary. General
return recognition, clawbacks, FX, reserve linkage, tax, historical restatement,
method-reset authority, bank execution and full C08 coverage remain outside
this finite slice.
