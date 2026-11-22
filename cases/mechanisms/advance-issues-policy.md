# Synthetic funded advance pool, revision 1

This proposed synthetic registration preserves the existing RR-01 mechanism.
It is a calculation policy selection, not a record of professional approval or
authority for any historical agreement. Both `RR-01-FUNDED-AS-OF-POOLED` and the
fixture authority `synthetic-prospective` are explicit proposed run decisions.

The scope is one agreement, participant and pool, with purpose
`participation_prepayment` and USD amounts. The supplied opening prepayment is
an original synthetic snapshot; successor runs carry the scoped published
closing cell and its result reference. State has one writer, uses a USD net
change, and cannot be reused for a reserve or outstanding obligation.

Actual funded date selects the half-open calendar quarter. Issue and matching
funding evidence observations must each precede the selected Instant cutoff,
which equals the manifest cutoff. Unavailable rows remain visible in the audit;
they do not become available merely because their funded date is in the quarter.
Every candidate issue has exactly one evidence match. The source checks scope,
amount, funded date, disbursement, title, currency, purpose, eligible/approved
flags and the selected authority. The generic interface additionally prevents
duplicate event, issue, disbursement and evidence identifiers. Existing typed
evidence is an input port because its actual schema differs from a generic
attestation envelope; no observation or approval has been invented.

Add selected issues to the nonnegative opening pool, then recover the smaller
of available prepayment and nonnegative period earnings. Pay the difference and
carry the remaining pool. Arithmetic is exact without rounding. This selects
no FIFO, intra-quarter earnings order, offsets, reversals, historical true-up or
cross-pool authority. The baseline supplied issue is 15000 and earnings 10000,
so the independently expected closing carry is 5000 and payable is zero.
Emissions are a calculated settlement and issue audit; they create neither
issued obligations nor payment evidence.
