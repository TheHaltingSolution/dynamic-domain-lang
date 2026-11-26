# Cross-contract entitlement burden: selected synthetic policy

The claimant's participation accrual is derived from original receipt basis200
and approved share.5: accrued100. Another agreement's original basis400 and
share.5 give accrued200. A separately scoped authority measures30% of the
claimant's original current accrual, subject to a cumulative original-authority
cap45. Requested30 is applied only against the other agreement: claimant100
remains100 and burdened200 becomes170. No30 is credited to the claimant and no
bank movement is created by the calculation. The resulting combined entitlement
is270 rather than300; transfer conservation is a different policy.

`SYNTHETIC-CONTRACT-BURDENS-01@1` has two explicitly named methods:

- `accrued_basis_current_period`: basis is original pre-burden participation
  accrual derived from original receipt amounts and approved share terms.
- `paid_basis_current_period`: basis is actual original participation payments
  fully applied to those same derived current participation entitlement lines.
  Complete payment evidence is mandatory. The fixture's original payment60 is
  applied to derived participation100, not to receipt basis200. This gives
  requested18 and burdened182 while claimant accrued100 and actual paid60 remain
  distinct. Applications above participation100 reject even if below gross200.

For each authority, `eligible = basis >= minimum_basis`, including equality;
`requested = basis × burden_rate` when eligible, else zero. Let original cap be
`L` and prior applied consumption reconstructed from originals be `K`.
`permitted = min(requested, L-K)` is an explicit selected cap rule. Retain the
cap excess and consume the original request identity even when permitted0.
There is no residual, reclassification or later cap-excess carry. After this cap,
insufficient current target entitlement rejects the entire calculation; no
clipping to availability, floor, negative balance or debt carry is inferred.

The cap45 adjacent-period control uses fresh original receipt/payment/request
facts each period. Requested30 applies30, then15, then0; cumulative applied
consumption is30,45,45. The burdened agreements' fresh current accrual200 becomes
170,185,200. Prior adjusted entitlement is not new current entitlement, and old
claims are not charged again when raw history is replayed.

Graph measurements always use original pre-burden accruals or linked original
payments, never adjusted endpoint feedback. In A→B→C, A original100 burdens B30;
B's original200 remains the measurement for its10% burden of C, giving20 even
though B's adjusted entitlement is170. All declared authority edges must form a
DAG, including unused edges. Explicit unique authorization sequences order
scarce-target checks. A cycle has no fixed-point interpretation.

Original authority+source economic scope+selected period+measurement kind is a
canonical consumption key. One request per such key is permitted, so changing
request IDs, measurement labels or original request-line aliases cannot charge
the same period's measure again. Original receipt, derived participation-line,
payment and request references are unique and retained across serialized
history. Repeated static authority records preserve the original cap, purpose,
rate, minimum, endpoints and evidence. Amendments, cap resets and registry changes
require a separately selected future policy.

The measure is current-period only. Payments/applications must belong to that
period and reference its original participation lines. A later payment against
an old receipt is outside this profile and cannot reopen a consumed basis.
Missing payment population evidence is unknown, not numeric paid0. An accrual
method may carry explicit unknown-paid metadata because it does not use it;
paid-basis calculation blocks. Only a complete original empty payment population
supports numeric paid0. Every account needs a complete original receipt
population, including an explicit empty one for original accrual0.

Periods are half open, with final `as_of = period.end − one day`. Source/evidence
observations are exact Instants strictly before cutoff. Approved/recorded Dates
include equality at as-of; effective start is inclusive and end exclusive. The
selected mechanical date relation for payment periods is UTC, not a guessed
local timezone. Original timestamp offsets/subseconds and raw text identities
remain unchanged in audit/state. Arithmetic is exact with no implicit rounding.

This is a bounded `research_assumption`, not professional acceptance or actual
cross-contract permission. Genuine agreement/participant/pool/asset/USD scopes
remain separate from coordinator execution metadata. Four accounts, eight
authorities/requests,64 rows per array and four total replayed periods are the
engineering limits. Genesis is explicitly zero before authority inception;
later state requires an actual serialized adjacent oracle predecessor. This
does not establish distributed/concurrent commit safety or source authenticity.

The policy follows the missing variation identified in LD03§7, lines390–399 and
`B-C10-BURDEN`. RR04 provides no additional C10 economic selection. Conserved
transfers, bank settlement/refunds, issued/unpaid obligation accounting, source
custody, signed losses, FX and native currency extensions remain outside scope.
