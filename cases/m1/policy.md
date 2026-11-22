# Selected synthetic M1a ordinary royalty policies

These are proposed synthetic methods, not an interpretation of a commercial
agreement. Every amount is exact USD. No quantization or payment issuance occurs.
Every supplied basis fact must be nonnegative; this is a selected restriction,
not a universal loss floor. Facts form an explicitly selected period input view,
not a raw ledger awaiting selection: a supplied fact outside the half-open run
period blocks the run. Facts must be observed strictly before the cutoff, with
matching available evidence.
Duplicate fact, bracket and evidence identities fail rather than deduplicate.

Tier brackets partition the entire nonnegative basis: start at zero, have no
gaps or overlaps, have strictly positive finite widths, and end with one
unbounded bracket. Each bracket has an explicit unique nonnegative sequence;
that sequence orders the brackets independently of their physical input order.
Lower bounds are inclusive; upper bounds are exclusive.
Every supplied nonempty tier table is validated, including declared tables
unused by the cap or guarantee method; those methods may instead supply an empty
table. A method that calculates tiers always requires a nonempty valid table.
The marginal method applies each bracket rate only to its slice. Whole-base
is a period-only method applying the reached bracket's rate to the entire
current period basis: at exactly 100 the second bracket applies. Basis 150,
first 100 at 10%, remainder at 20%, earns 20 marginal versus 30 whole-base.
There is no implicit cumulative retroactive escalation.

Cumulative marginal uses a scoped opening cumulative-basis meter, earning the
increment between opening and closing marginal totals. Opening 80 plus current
70 earns 12 and closes at 150. Splitting and physical ordering of current facts
do not change period totals. Only this method may carry a cumulative basis.

Caps allow the lesser of new entitlement and unused ceiling. Cumulative cap
100 with opening consumption 70 and new 80 allows 30 and closes consumption
at 100. Cumulative consumption never resets. A period cap uses a distinct
method identity: continuing within its recorded period retains consumption;
crossing a period boundary requires explicit reset, with the prior period
ending at or before the new start. Reset is forbidden for every other method.
The structured meter carries its selected method and period; the state cell
also carries agreement, participant, pool, asset, purpose and lineage.

The nonrecoupable period guarantee is max(earned, floor): earned 80 and floor
100 gives entitlement 100. It creates no advance balance or recoupment claim.
It differs from the separate advance-150/earnings-80 example (payable zero,
closing advance 70). No guarantee/cap/advance precedence is inferred here.

The only selected composition is period marginal tiers followed by an explicit
period cap starting with zero consumption. Both uncapped earnings and capped
entitlement are reported. Period methods other than period cap carry zero;
method mismatch or a nonzero unrelated meter fails. Negative/signed losses,
retroactive whole-base history, crossing-event variants and general guarantee,
advance and cap combinations require separately declared future policies.
