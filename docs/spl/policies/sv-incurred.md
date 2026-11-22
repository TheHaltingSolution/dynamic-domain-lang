# SV incurred-date policy, version 1

Policy identity: `sv-incurred@1`. Economic profile: `sv-incurred-v1`.
Incorporated by [the readable SV schedule](../../../cases/sv/sv01-readable.spl).
This is a bounded synthetic case policy, with proposed interpretation decisions;
it is not historical contract approval.

The quarter is the Gregorian half-open interval in `parameters.policy.period`
(baseline 2026-01-01 through, excluding, 2026-04-01). This calendar is a synthetic
profile choice. Eligible Pictures are the agreement's explicitly registered
assets, distributed by its registered distributor and authorized members of its
participant prepayment pool for the period. Display titles establish no identity,
membership or priority. `parameters.policy.agreement_id`, `participant_id` and
`pool_id` identify these scopes; canonical agreement/role/membership records must
agree. Baseline assets are `picture-a` and `picture-b`.

Cash Receipts are same-Picture cash amounts selected by `cash_received_date`
within the quarter. They are not invoice face values. The supplied canonical
facts, allocation authority and `manifest.cutoff` determine the available fact
snapshot; both receipt and cost projections retain their source lineage.

For each branch, deduct only same-Picture costs with reviewed eligibility for
that branch whose **incurred date** falls within the quarter. `parameters.cost_date_basis`
must be `incurred_date`; the typed selector is `c.incurred_date`. Missing dates
block; posting or paid dates are not substituted. `parameters.cost_decisions`
supplies each fact's explicit approval, branch and reason. The Net Profits
Schedule and Adjusted Gross Receipts Schedule are distinct eligibility methods;
their common aggregation shape does not authorize the same cost population.
The baseline separately authorizes USD 10,000 for A's Net Profits branch and
USD 5,500 for B's Adjusted Gross Receipts branch. This case consumes those
decisions; it does not implement a general contractual cost-classification method.

`parameters.funding_snapshot` must affirm completeness at the quarter opening
for all member Pictures and exactly the participant and distributor. Approved
`evidence_events` of kind `funding` supply their acquisition funding, effective
on or before that opening and observed within the run cutoff. Valuation uses
nonnegative supplied USD face amounts, with exact rational arithmetic, no FX,
discounting, inferred noncash value or duplicate deduction of funding. A zero
participant contribution is meaningful only under this complete snapshot.
The funding share is participant acquisition funding divided by participant plus
distributor acquisition funding for the same Picture. Baseline A is 0 / 50,000;
B is 40,000 / (40,000 + 60,000) = 40%. Positive participant funding selects the
funded branch. Missing completeness, wrong parties/scope, a nonpositive funded
denominator or negative funding blocks calculation.

The visible schedule supplies 25% fee / 20% participation for the unfunded
branch and 7.5% fee / the funding share for the funded branch. Negative earned
participation is outside this pilot and blocks settlement. All arithmetic is
exact; this case introduces no rounding operation.

Available Advance Balance is a supplied remaining opening participation
prepayment, selected through `opening_aliases` and `state_cells`, with approved
provenance, policy lineage and the full agreement/participant/pool/currency/
scenario/opening-boundary key. Baseline opening is USD 15,000, not a derivation
from a historical ledger. Sum nonnegative Picture earnings, recover the lesser
of pool earnings and available opening prepayment, and carry the remainder.
Baseline earned 33,000 less recovered 15,000 gives unissued payable 18,000 and
closing prepayment zero. No new advances or actual payment application is
assumed by this schedule. Missing or inconsistent authority, scope, evidence or
required state blocks outputs and closing state.

The run review package exposes the actual parameters, decisions, evidence and
opening cells alongside this versioned text. [The registry](manifest.json)
records machine-checkable implementation requirements; the canonical wrapper
pins this text and checks those requirements. Native incorporation alone is a
provenance declaration and does not certify these supplied facts or policies.
