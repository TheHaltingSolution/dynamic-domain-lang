# RQ-07 posting-date policy, version 1

Policy identity: `rq07-posted@1`. Economic profile: `sv-rq07-posted-v1`.
Incorporated by [the readable RQ-07 schedule](../../../cases/sv/rq07-readable.spl).
This is the supplied synthetic reconstruction approved only within the scenario;
independent reader/accountant review remains pending.

The Gregorian half-open quarter is `parameters.policy.period`: baseline
2026-01-01 through, excluding, 2026-04-01. The agreement, participant and recovery
pool are `parameters.policy.agreement_id`, `participant_id` and `pool_id`:
baseline `DEAL-SYN-SV`, `PART` and `POOL-SV-AB`. Registered distributor `DIST`
distributes member Pictures `PIC-A` and `PIC-B`. Agreement, roles and authorized
pool membership must cover the period; headings and titles establish none of
these relationships.

Select applied cash by **bank value date** during the quarter. Approved
applications posted strictly before the UTC date of `manifest.cutoff` supply
the receipt allocation; baseline cutoff is 2026-04-04T00:00:00Z. The adapter's
explicit `--observed-at` policy supplies invented observation instants rather
than inferring them from funding dates. Baseline runs use
2026-04-03T00:00:00Z. Supplied raw application dates have day precision. Include
partial applied receipts and allocate bundle cash by the approved 2/5 to PIC-A,
3/5 to PIC-B weights in scenario allocation `ALLOC-77-v1`. Count each allocated
receipt once: invoices, deposits, applications and parent bundle amounts are
separate amount spaces and do not become additional title cash. Invoice,
license, settlement and reporting dates are retained separately.

Costs use **GL posting dates**, not incurred dates. `parameters.cost_date_basis`
is `posting_date`; the typed posting-cost view exposes it as `c.recognition_date`
with `recognition_policy_ref`. Incurred dates are unavailable and remain absent;
no date is fabricated. Deduct only same-Picture costs whose posting date lies
within the quarter and whose branch-specific `parameters.cost_decisions`
explicitly approve them. The Net Profits and Adjusted Gross Receipts schedules
remain distinct. Baseline A's USD 10,000 outside marketing cost is approved in
Net Profits; B's USD 5,500 actual distribution cost is approved in Adjusted Gross
Receipts. B's unsupported overhead is explicitly excluded. These are supplied
scenario decisions, not a general deduction authority inferred from GL labels.

`parameters.funding_snapshot` affirms a complete opening snapshot for both
Pictures and exactly PART/DIST, as of 2026-01-01. Approved funding evidence is
effective by this date, observed within the cutoff, nonnegative and in USD.
Value funding at supplied USD face amounts with no FX, discounting or inferred
noncash value. Funding controls branch choice/share only; it is not separately
deducted. PIC-A has PART 0 and DIST 50,000; completeness authorizes that zero.
PIC-B has PART 40,000 and DIST 60,000, giving 40% = 40,000 / 100,000. The
denominator includes only those two qualifying contributors for the same
Picture. Missing or incomplete evidence, wrong population or a nonpositive
funded denominator blocks the run.

Use the visible 25% fee / 20% share in the unfunded Net Profits branch and
7.5% fee / funding share in the funded Adjusted Gross Receipts branch. Negative
earnings are outside this profile and block. Arithmetic is exact with no
rounding stage; baseline amounts have integral cents.

The opening participation prepayment in `state_cells`, selected by
`opening_aliases`, is a supplied remaining USD 15,000 at 2026-01-01, supported
by the scenario's approved prior-close control (prior advances 30,000 less
prior recovery 15,000), not a reconstructed historical ledger. It carries
agreement, participant, pool, currency, scenario, boundary, provenance and
policy-lineage dimensions. Recover the lesser of the pool's nonnegative
33,000 earnings and this 15,000 opening. Payable is unissued 18,000; closing
prepayment is zero. No new advances or actual-payment mechanism is included.
Required evidence, state and scope failures block statement and closing ports.

Actual parameters, eligibility approvals, source controls, authority and opening
state appear in the run review package. [The registry](manifest.json) supplies
machine-checkable implementation requirements; the canonical wrapper pins this
text and checks those requirements. Native incorporation alone records
provenance and does not prove the supplied scenario's accounting authority.
