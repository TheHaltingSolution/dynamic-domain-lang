# Authorized current-period cross-contract transfers

`SYNTHETIC-CONTRACT-TRANSFERS-01`, revision `1`. This is a synthetic
`research_assumption`, not general contractual authority, vendor equivalence,
bank execution or permission to move unpaid/issued balances.

Accounts retain their real source/target agreement, participant, pool and USD
currency scopes. The coordinator is a distinct coordination identity, not a
substitute shared agreement. Duplicate economic accounts, self-edges, same-
agreement edges, unknown accounts and currency mismatch block this selected
cross-contract profile. Limits are 16 accounts, 64 declared authorizations and
transfer transactions, and 256 entitlement facts per invocation.

Only original current-period calculated entitlement is transferable. Each
account begins with its supplied nonnegative current entitlement facts. Retain
the original source and upstream entitlement-line references as supplied provenance,
without claiming custody or verifying the upstream financial calculation.
There is no opening unpaid, previously issued, bank cash or prior-period
closing balance available to transfer under this measure.

Each upstream reference identifies a specific original entitlement line using
`artifact-reference#line-id`, not a whole multi-line result artifact. References
are unique across current facts and retained in consumed history. Re-aliasing the
same original line under a new fact ID cannot add entitlement in a later period.
This checks consistency of supplied provenance, not signature or custody.

Every declared authorization must explicitly approve its source/target scopes,
the exact selected period, a nonnegative amount limit and unique nonnegative
sequence. Approval and recorded Dates must be on or before the explicit civil
as-of Date, including equality; approval cannot follow recording. Separate
observation Instants and evidence must precede cutoff. There is at most one
positive transfer transaction per authorization. A transaction preserves its
own identity and cannot exceed that authorization's amount limit.

All declared authorization edges form a finite directed acyclic graph. Process
accounts topologically, taking the smallest account ID only to order independent
available nodes. For each account, process its outgoing transactions by the
explicit authorized sequence. The sequence does not override graph dependency
order. Incoming current-run credits may fund subsequent outgoing transactions.
Missing available entitlement blocks rather than clipping a transfer or emitting
a partial result. Cycles have no fixed-point interpretation in this policy.

For transfer m from S to T, subtract m from S's available current entitlement and
add exactly m to T. Each account reconciles final entitlement = original current
entitlement + incoming - outgoing. Global final entitlement equals original
current entitlement. Report external_cash_added=0 as a conservation invariant,
not as independent evidence about actual bank activity. Credits and transfers
are not new external receipts or new source earnings.

The baseline source earns 100; an explicitly authorized transfer of 30 leaves
source entitlement 70 and target entitlement 30. A downstream target may transfer
part of that credit onward under its own separately scoped authorization.

Opening state carries consumed entitlement, authorization and transfer IDs and
the preceding period's audit summary, not monetary funds. Successor execution
uses fresh current-period entitlements and actual serialized predecessor state.
Reusing a consumed transaction, authorization or entitlement identity blocks.
Replaying the same immutable period from its original opening deterministically
reproduces the candidate transfer once; it does not establish an atomic external
commit or concurrent retry guarantee. A separate coordinated publication service
would be required for that operational claim.

No actual payment, bank transfer, refund, FX, signed loss, implicit crossing,
historical unpaid-balance transfer, authorization amendment or cyclic contract
dependency is implemented by this fixture.
