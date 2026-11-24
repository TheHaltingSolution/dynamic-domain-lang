# Mixed recoupment allocation and earning-offset waterfall

`SYNTHETIC-MIXED-CLAIMS-01@1` is a bounded `research_assumption`. The measure is
current participant-group earning capacity: original receipt basis240 times
approved share.5 gives120. It is neither original financing nor bank cash paid.
The debtor group is a separate participant identity from its creditors and
residual beneficiaries.

The original registry preserves four economic kinds:

| Kind | Original source and limit | Selected application |
| --- | --- | --- |
| capital | Actual capital funding100 to group plus separate recoupment authority100 | Calculated recoupment allocation credit |
| advance | Actual advance funding100 to group plus separate recoupment authority100 | Calculated recoupment allocation credit |
| fee | Separate original fee basis250 at original rate.1 gives25; scoped authority25 | Reciprocal earning offset retained by current earning payer |
| approved_correction | Original entitlement200×.5=100; linked return80×.5=40 revises it60; separately evidenced actual paid80 exposes20; prospective authority20 | Reciprocal earning offset, never automatic from a negative earning |

Fee basis250 is an independently identified original claim-accrual measurement,
not another receipt added to current capacity120 and not a pre-fund fee
deduction. Its claim is consumed once. The historical reversal40 establishes
correction capacity only; it is not deducted again from fresh earnings. Original
paid80 stays80 after calculated offsets. Fee/correction creditors must be the
current earning payer, and authorities explicitly permit setoff against the
group. Capital/advance creditors must match their actual funding sources. A face
promise, original entitlement100 or missing payment view cannot manufacture an
advance or paid80.

Three named recipes exist:

- `priority_fee_first`: fee, correction, capital, advance.
- `priority_correction_first`: correction, fee, capital, advance.
- `pro_rata_eligible_balances`: allocate the smaller of event capacity and total
  eligible remaining claims in proportion to those remaining balances across
  all kinds. No eligible balance means zero application without division.

Each event is processed by economic Date then its unique explicit sequence.
Claims are eligible only from their approved prospective eligible Date, inclusive.
For eligible claims the authority must also be observed by the earning record's
observation. All source/evidence observations precede the period's exact cutoff.
Priority ordering is authorized kind rank, eligible Date, then sequence. A tied
complete key rejects; physical source order or lexical ID never supplies an
economic tie breaker. Pro rata retains the same deterministic reporting order
without turning priority into a monetary preference.

With only capital100/advance100 and capacity120, priority allocates100/20 while
pro rata allocates60/60. With capacity30 and all four kinds retained, fee-first
offsets25fee/5correction; correction-first offsets10fee/20correction. Capital and
advance remain unrecovered. With all four claims and capacity120, fee-first
applies25/20/75/0. All-kind pro rata applies capital2400/49, advance2400/49,
fee600/49 and correction480/49. All arithmetic is exact without cent rounding.

At each event, capacity equals recoupment credits plus earning offsets plus
residual entitlement. For each claim, authorized principal equals cumulative
recoupment credits plus cumulative earning offsets plus remaining recoupable
balance. Recovery credits reduce this selected recoupment ledger, not a bank
repayment balance. They create separately identified unissued allocation
entitlements. Fee/correction offsets are retained setoffs and do not create a
second outgoing payable. No bank movement is created by the calculation.

Residual is allocated only to the entire approved roster at its explicit
nonnegative weights and positive total. The group cannot be an individual
beneficiary. Whole roster and positive denominator remain mandatory even for
zero residual, empty claims or no earning events. Zero-weight members remain
visible; an empty roster or all-zero weights rejects. With capacity270 all245
of principal is applied, residual25 splits12.5/12.5, and new unissued allocations
are225 while retained offsets are45.

Current cash settlement of these claims/allocations is an explicitly approved
complete-empty population for every period. Missing completeness blocks unknown
cash; nonempty cash settlement requires a different policy rather than being
silently dropped. This zero observation concerns claim settlements only, not
original capital/advance bank funding or the historical payment80. Those remain
separate amount spaces and source purposes.

All original principal sources, approvals, source-line references and the claim
registry are immutable after the first period. No fresh claims, amendments,
interest, additional funding, external repayment, claim splitting/reclassification
or automatic reauthorization of a recovered correction is supported. Original
bank lines cannot be reused as capital and advance; original fee/correction
measurements cannot back another claim under a new identity. Current earning
lines are distinct from original funding/fee/correction amount spaces and are
consumed once across adjacent serialized history.

In actual capital/advance carry, capacity120 creates100/20 allocation credits;
next capacity90 creates0/80 and residual10 split5/5. Old unissued allocations
are retained, not added back as new capacity. With all four kinds enabled,
120 applies fee25/correction20/capital75/advance0;90 then applies0/0/25/65,
leaving advance35. Old fee/correction principal and original paid80 do not reset.

This is a supplied final-period known view: half-open period, as-of last Date,
complete populations observed no earlier than period end, and an exclusive
Instant cutoff. Historical periods retain their own original observations and
cutoffs. Event eligibility is an explicitly selected Date/known-record relation,
not a universal legal or full bitemporal default. Original funding births and fee/
correction claim sources occur in the genesis ledger period; historical paid80
predates it. Opaque valid Unicode Text IDs and admitted numeric/time lexemes are
preserved without normalization, trimming or case folding.

The engineering limits are eight claims, eight residual members,12 participants,
32 rows per table and four total replayed periods. They are not a native capacity
benchmark or an all-combinations promise. Native/canonical source acceptance,
bank execution, distributed commit guarantees, professional interpretation and
currency extensions require separate evidence; no FX is introduced.
