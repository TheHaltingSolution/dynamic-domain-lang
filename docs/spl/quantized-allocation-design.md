# Independent cent-allocation controls

23 November 2026. This C06 design precedes executable SPL and supplies independent
controls for `B-C06-RESIDUAL`. It addresses the named finite allocation methods,
not general relationship cardinality, Unicode ordering or whole-contract approval.
The [policy](../../cases/quantized-allocation/policy.md) is explicitly synthetic.
The [neutral fixture](../../cases/quantized-allocation/neutral.json) supplies only
original parent, recipient, weight, authority and evidence records.

The main economic rounding point is round-parent-half-even-then-allocate-target.
For each original parent P and complete authorized recipient weights w:

```text
N = half_even_integer(100*P)
T = N/100
W = sum(w_i) > 0
q_i = N*w_i/W                       exact quota in cents
b_i = floor(q_i)
f_i = q_i-b_i
R = N-sum(b_i)                      residual cents, 0 <= R < recipient count
rank_i = descending f_i, then ascending authorized ASCII recipient ID
child_i = (b_i + (rank_i <= R))/100
sum(child_i) = T
rounding_delta = T-P
```

Keep original-parent exact quota P*w_i/W distinct from target-based exact share
T*w_i/W. The original parent .015 with weights 1/2 gives target .02 and children
.01/.01. Original quotas .005/.01 would individually half-even round to 0/.01.
That amount-changing control distinguishes this policy from allocation first.
Two distinct original parents of .005 each separately round to zero; aggregating
them first would be a different policy. No rounding is applied to weights,
denominators, quotas or remainder comparisons.

The canonical discriminator .01 equally to X/Y gives bases 0/0, equal fractional
cent remainders 1/2, residual 1 and X=.01/Y=0. The named identity profile is the
case-sensitive ASCII subset `[A-Za-z0-9][A-Za-z0-9_.:-]{0,63}`, using its ordinal
lexical order. This is explicit supplied authority, not a global Unicode rule.

The separate `authorized_supplied_cents` method selects expressly authorized
original cent amounts for every approved recipient, conserving the same T.
It retains the exact-weight calculation as a comparison. Thus equal-weight .01
can instead select X=0/Y=.01 under an explicit amount authority. Output fields
`weighted_amount`, `weighted_residual_cent` and rank always describe the computed
weight method; `selected_amount` describes the chosen method. The two amount
spaces never silently merge.

The neutral schema is `quantized-allocation-neutral/1`:

```text
case_id, scope, period {start,end}, as_of Date, cutoff Instant, policy
recipient_registry[], parents[], authorities[], supplied_allocations[]
evidence[], opening_state, prior_result?
```

Scope is exactly `{contract_id,participant_id,pool_id,asset_id,currency}`, with
USD selected. Policy pins ID/revision, method, parent_rounding,
quota_basis=`rounded_parent_target`, residual_order, research_assumption and
finite limits: 8 recipients, 4 parents per period, 8 historical periods before
the current period. Exact nonnegative neutral decimal/rational strings carry
amounts and weights; binary floats and negative raw values are rejected.

Each recipient registry row is `{id,scope,observed_at,source_ref,evidence_ref}`.
This original declared universe must remain pinned across ordinary carry.
An authority's complete recipient set must equal it; required recipients cannot
vanish merely because their current weight or child amount is zero.

Each parent is `{id,scope,amount,effective_date,observed_at,source_ref,upstream_ref,
evidence_ref,authority_id}`. The specific upstream reference must be an original
`artifact#line`, never merely a whole multi-line result. Parent dates lie in the
current half-open period. Parent IDs, source references and upstream lines are
consumed once, including zero-valued parents. Distinct parent facts may share
terms; the parent itself must remain independently original.

Each authority retains ID, parent_id, parent_upstream_ref, scope, method,
effective period, approved flag, approved_date, recorded_date, observed_at,
recipient_ids, terms, supplied_allocation_ids, residual_order, source_ref and
evidence_ref. It approves exactly one complete parent allocation. Each original
term is `{id,recipient_id,scope,weight,observed_at,source_ref,evidence_ref}`.
Term IDs and recipient assignments are unique within the authority. Weights
are nonnegative and W>0; all terms and unused authorities are checked. Authority
and parent references must match, including the original upstream line. Approval
must satisfy approved_date <= recorded_date <= as_of. The civil as-of controls
approval selection; the separate exact Instant cutoff controls observations.

Supplied amount rows retain `{id,parent_id,recipient_id,scope,amount,observed_at,
source_ref,evidence_ref}` and must be expressly named by the amount authority.
There must be exactly one per recipient, all integral cents, summing to T. The
weight method forbids supplied allocation references, and unmatched supplied
rows fail under either method. Ordinary evidence retains id/scope/kind/observed_at.
Every referenced original fact and its evidence must be observed before cutoff.
These checks validate supplied provenance consistency; they do not authenticate
an external signature or establish ownership of source cash.

Opening/closing state contains scope, purpose=`quantized_parent_allocation`, full
policy, original recipient_registry, boundary, origin/source_case_id,
consumed_parent_ids, consumed_upstream_refs and original history. Genesis has
empty consumed sets/history. Each history entry retains source_case_id, period,
as_of, cutoff, parents, authorities and supplied_allocations. The oracle replays
those original sources, validates their original cutoffs and recomputes consumed
identities before accepting the opening. Source arrays, authority terms and ID
sets are normalized by stable identity; normalization does not supply financial
answers. Actual adjacent prior_result carries source_case_id/period/closing_state;
optional external result_ref is provenance, not an invented canonical digest.
Policy, registry, scope and predecessor inconsistencies block.

`oracles.quantized_allocation.quantized_allocation(data)` is standard-library only
and returns Fractions; `exact_json` serializes them as canonical rational strings.
Each parent result retains original amount, target cents/T/delta, denominator,
base-cent total, residual, ranking and all child intermediates. Aggregate original,
target and selected-child totals remain distinct. Financial recognition is
explicitly `selected_children_only`, so a parent plus its children cannot be
treated as two contributions. There is no cash-paid output.

The source adapter may validate original schemas, identities, observations and
relationships. It must leave target rounding, denominators, quotas, floors,
remainders, ranking, residual awards and conservation to SPL. It must not send
event-specific ranks or solved money. The independent oracle must not import
the adapter, SPL evaluator or compiler calculations.

Verification: 24 standard-library unittest methods cover the one-cent tie, exact half-even boundaries, fractional
original discriminator, zero weights/parent, whole-cent equality, empty parents,
exact rational weights, amount-authority disagreement, physical permutations,
ASCII case ties, enforced recipient/parent/history bounds, missing/duplicate/unknown/unmatched recipients, invalid scope,
authority/cutoff failures, aliases and actual serialized adjacent periods.
External isolated source-snapshot verification is reported with this slice's
handoff. Compiler equivalence remains work for a separately authored source.
