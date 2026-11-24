# Independent mixed-claim waterfall controls

The adopted atomic variant `C07.MIXED_CLAIM_KINDS` and backlog `B-C07-MIXED`
require a composition beyond separate capital-only and advance cases. This
[neutral fixture](../../cases/mixed-waterfall/neutral.json) and
[policy](../../cases/mixed-waterfall/policy.md) supply independent original-fact
controls before another author implements SPL. Existing generic arithmetic,
records, finite folds and maps suffice. Existing waterfall/AO controls and all
compiler/source implementations remain unchanged.

The fixture pins the adopted [atomic catalog](c1-atomic-variants.json),
[capital policy](../../cases/waterfall/policy.md) and
[authorized-offset policy](../../cases/authorized-offsets/policy.md). The new
operating selections are synthetic, not professional approval or filed-contract
interpretation. The API is `oracles.mixed_claims.mixed_claims(data)`, raising
`MixedClaimOracleError` before returning any partial financial state. It imports
only `copy`, `datetime`, `fractions` and `re`. `exact_json` serializes exact
fractions as integer/rational strings; original raw facts/lexemes remain intact.

The schema `mixed-claims-neutral/1` consists of `scope`, `policy`, `research`,
`registry`, `opening_state`, optional `prior_result`, and current frame fields
`case_id,period,as_of,cutoff,earnings,earning_population,
cash_settlement_population,evidence`. Scope includes agreement, pool, asset,
participant group, purpose and USD. Group identity is not a creditor/member.

The immutable original registry contains:

| Original records | Financial derivation and authority |
| --- | --- |
| Participant IDs/payer, earning terms | The payer owes new group participation; original current basis×approved share creates event capacity |
| Roster authority/residual weights | Complete approved residual membership, every member retained, nonnegative weights with positive total |
| Capital/advance funding rows and complete populations | Actual funding amounts, funder/recipient roles, exact funding Instants and unique original bank lines; original rights alone do not establish cash funding |
| Fee bases | Separately identified original base/rate and creditor/debtor authority;250×.1=25 is a claim source, not a second fund deduction |
| Correction sources | Original basis/rate and linked return measurement derive100−40=60 at the original rate |
| Historical payments/applications/complete populations | Original paid80 is separately evidenced, fully linked to original entitlement100 and never inferred from accrual; potential overpayment is80−60=20 |
| Claim authorities | Original claim identity/kind/beneficiary/source IDs, authorized principal bounded by its independent source capacity, priority/sequence, prospective eligible/approval/recording Dates and evidence |

All original sources and their evidence are validated, including unused ones.
There is at most one claim use of a selected kind/source record. Duplicate or
aliased original bank/fee/correction/authority lines reject. Capital/advance
beneficiaries must match actual funders; fee/correction recipients must be the
earning payer for the selected reciprocal setoff. No generic interchangeable
claim-amount bucket erases these source and purpose distinctions.

Current earnings retain original receipt ID/reference, basis amount, economic
Date, sequence, scope, exact observation and evidence. Their complete population
pins IDs and original gross-basis total. No available-capacity answer is supplied.
An event's eligible opening claim balances determine its fixed pro-rata pool;
priority instead consumes available capacity in authorized order. Future
eligibility cannot retrospectively consume an earlier earning event.

Outputs retain source-capacity controls, every earning event's derived capacity
and eligible balances, per-claim before/application/after, preserved economic
kind, residual member lines and per-kind cumulative ledger. Capital/advance
applications are `recoupment_credit`; fee/correction applications are
`earning_offset`. The former generate unissued allocation records, the latter
retained offset records. Residual records are also unissued. Their tuple keys
retain source case, original earning reference and original claim authority or
beneficiary; delimiter tricks or repeated current source rows cannot manufacture
another entitlement. No allocation is reported as actual bank repayment.

The scalar controls are not interchangeable amount spaces: actual capital100,
actual advance100, historical participation paid80, current earning capacity120,
separate fee basis250/fee25, correction potential20, and unissued allocation75 in
the full fee-first example are all retained. Complete-empty current claim cash
settlement evidence supports observed current settlement0; absent evidence
cannot do so. Nonempty settlement is explicitly unsupported rather than ignored.

Four-kind capacity120 applies fee25/correction20/capital75/advance0; its actual
serialized successor capacity90 applies0/0/25/65, leaving advance35. Fee/correction
are not re-created when the original registry is re-read, and original paid80
stays80. Separate capital/advance-only120→90 controls preserve100/20 then0/80 with
residual10. Unissued allocations survive in a different ledger; they are neither
new current capacity nor bank-paid evidence. These witness serial state
calculation, not external concurrent transaction safety.

The state `mixed-claim-state/1` pins scope/policy/review/registry and retains
original current frames with their own cutoffs, independently recomputed results,
the full recoupment/offset ledger, unissued allocation ledger, offset records and
consumed earning IDs/lines. History is replayed from original principals, not
from a supplied remaining-balance answer. Each next opening must equal that
replay and the actual adjacent predecessor summary
`{source_case_id,period,closing_state,result_ref?}`. A case ID is not a canonical
result digest. No new claims or registry changes can quietly reauthorize already
consumed fee/correction capacity.

The roster is mandatory even for empty/zero/exhausted claims. Per-event
recoupment and offsets cannot exceed a claim's remaining amount; total allocated
capacity equals all credits, offsets and residuals. Every claim reconciles
authorized principal to recoupment credits+earning offsets+remaining. Scope,
original source, population, chronological eligibility and unresolved event/order
ties fail atomically. Physical input ordering does not set monetary priority.

The oracle accepts valid Unicode Text identities without imposing declared-ID
ASCII rules; it preserves raw admissible time/number spellings and performs exact
UTC comparisons. This does not assert native acceptance of decomposed canonical
JSON or authorize normalization. A future source adapter must honor the real
canonical boundary and retain raw provenance plus any explicitly approved mapping.

Frozen external verification records the five owned LF files, unchanged package
initializer, exact planning/policy snapshots and pins, source-independent imports,
hand cases and both actual serialized two-period chains. This work supplies no
native, emitted, canonical publication, whole-compiler proof or bank-execution
credit. A different source author must establish those paths independently.
