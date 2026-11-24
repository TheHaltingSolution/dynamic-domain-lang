# Explicit cross-contract entitlement coordinator

23 November 2026. This independent C10 design and neutral oracle precede SPL
implementation. Existing exact arithmetic, structural records and finite folds
can calculate the method, but canonical integration needs a deliberate
coordinator interface. The generic wrapper's one outer agreement does not itself
authorize relationships among several real contracts. Never recast recipients
as ordinary participants in one source pool to evade that interface requirement.

The [policy](../../cases/transfers/policy.md) is a named synthetic
`research_assumption`. The [neutral fixture](../../cases/transfers/neutral.json)
keeps two actual scopes: agreement-source/participant-source/pool-source and
agreement-target/participant-target/pool-target, each USD. A separate coordinator
identity connects explicitly authorized transfers. Source entitlement 100 and
transfer 30 yield source 70 / target 30 without creating external cash.

The selected measure is **current-period entitlement only**. Let E_a be original
current entitlement for account a, I_a incoming credits and O_a outgoing
transfers. At each step, available balance starts at E_a and changes only by
current-run credits/debits. Require sufficient source availability before each
positive transaction. Final F_a=E_a+I_a-O_a, all F_a nonnegative, and sum(F)=sum(E).
`external_cash_added=0` is this accounting invariant, not payment evidence.

Prior-period unpaid, issued or cash balances are not transfer inputs. Opening
state carries identity history and a prior audit summary only; its old closing
entitlements are never added to current E. This avoids repeatedly subtracting
opening-plus-current unpaid amounts. Upstream original entitlement and result
references are supplied provenance, not a verified original calculation or a
custodied third-party result. Incoming transfers are intermediate credits, not
new original entitlement; downstream accounts may transfer them onward.

The exact top-level shape is:

```text
schema_version = transfers-neutral/1
case_id, coordinator, period {start,end}, as_of, cutoff, policy
accounts[], entitlements[], authorizations[], transfers[], evidence[]
opening_state, prior_result?
```

`coordinator` is `{id,currency,purpose}`, USD and
`current_entitlement_transfers`. Each account is
`{id,scope,source_ref,evidence_ref}` with its real
`{agreement_id,participant_id,pool_id,currency}`. These economic tuples are
unique. Edges must cross agreement IDs in this selected profile, not merely
rename one existing account. Maximum declared sizes are 16 accounts, 64
authorizations, 64 transfer transactions and 256 current entitlement facts.
These are engineering limits, not universal contract terms or capacity results.

Entitlement facts contain
`{id,account_id,scope,amount,effective_date,observed_at,source_ref,
upstream_result_ref,evidence_ref}`. They are original nonnegative exact current
entitlements, not cash. Source and upstream references are retained unchanged.
Economic dates must lie in the selected half-open period. Duplicate facts or
the same current source view under different IDs block. Each upstream reference
is a specific original entitlement line in `artifact-reference#line-id` form.
It is unique across current facts and retained in consumed upstream history.
Different lines of one artifact may share its artifact prefix but need distinct
line suffixes. Re-aliasing an already consumed line under another row ID blocks;
the oracle checks supplied-reference consistency, not custody or authentication.

Authorization rows contain
`{id,source_account,target_account,source_scope,target_scope,effective,
approved,approved_date,recorded_date,observed_at,sequence,maximum_amount,
source_ref,evidence_ref}`. Effective period is exactly the selected period.
Every declared authorization is approved and known by the civil as-of Date;
`approved_date <= recorded_date <= as_of`, with equality included. This is
separate from exact `observed_at < cutoff`; no recording Instant is inferred
from a Date. Even unused declared authorizations are validated. Maximum amount
is a nonnegative exact USD entitlement limit, not an inferred available balance.

Transfer rows contain
`{id,authorization_id,source_account,target_account,source_scope,target_scope,
amount,recognition_date,observed_at,source_ref,evidence_ref}`. Each amount is
strictly positive. There is at most one transaction per authorization. Endpoints
and original scopes must match that authorization exactly, and recognition is
inside the selected period. Transfer observation follows the linked approval
observation. Authorizations and transactions remain distinct original records.

Evidence rows are
`{id,coordinator_id,account_ids,observed_at,kind}`. Every referenced account is a
real coordinator member. Each fact/evidence relationship must explicitly cover
the relevant account or both endpoints. This structural validation does not
confer actual cross-contract permission; the supplied synthetic approvals are
the selected research assumptions.

Build the graph from all declared authorization edges, including unused edges.
Reject unknown endpoints, self-edges, currency mismatch and cycles. Process
nodes with Kahn topological order; among currently independent zero-indegree
nodes, choose the smallest account ID. Outgoing transactions for a node use
their globally unique explicit authorization sequence. Sequence is subordinate
to graph dependencies; it does not permit spending a future incoming credit.
No amount is silently clipped, no fixed point is inferred for a cycle, and any
error blocks the entire coordinated result and successor state.

Opening/closing state has exactly:

```text
coordinator_id, account_scopes[], purpose, policy_id, policy_revision
boundary, origin, source_case_id
consumed_transfer_ids[], consumed_entitlement_ids[], consumed_authorization_ids[]
consumed_upstream_refs[]
last_period[]
```

Account scopes are `{id,scope}` records pinning the complete real account set.
Genesis has zero-length consumed lists and last_period, origin/source_case_id
`genesis`, and boundary at period start. A successful run writes exactly one
last_period audit summary containing source_case_id, period, account results,
original entitlement facts and applied transfers. These historical numbers are
context, never new available funds. Consumed IDs persist beyond that summary.

An adjacent successor must present the exactly serialized previous closing state
and matching `{source_case_id,period,closing_state,result_ref?}` summary. The
optional external result reference is supplied provenance; financial controls do
not compute or authenticate its canonical digest. The canonical coordinator must
also retain actual predecessor cell references and ensure all endpoint outputs
belong to one coordinated result. Calculation determinism is not an implemented
multi-contract transaction/commit service.

The standard-library oracle `contract_transfers(data)` returns original current
entitlements, topology, per-transfer source/target balances before/after, per-
account incoming/outgoing/final values, global conservation and successor history.
`exact_json` preserves exact neutral strings for carry. Required controls include
70/30, downstream funding, authorized sequence, cycle/self/unknown scope, amount
limits/overdraw, no opening-fund reuse, as-of/effective/cutoff equality, duplicate
and consumed IDs, permutation/deterministic replay, predecessor boundaries, and
global/per-account conservation. FX, banks, signed balances, undisclosed authority,
cyclic fixed points and operational atomic publication remain outside this slice.

Independent authoring verification on 23 November 2026: `python -m unittest
Tests.test_transfer_oracle -v` passed all 16 test methods in 0.018 seconds.
This records neutral financial controls only. Native, emitted and cross-contract
canonical coordinator execution require separate implementation and evidence.
