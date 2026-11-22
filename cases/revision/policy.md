# CORR-01 bounded authorized restatement

Selected synthetic policy, proposed for this fixture only. RR-02 authorizes the
mechanism's distinction between entitlement and actual payment; it does not
approve a universal contractual correction right. This case explicitly supplies
synthetic authorization to replace one Q4 application against one unchanged bank
receipt. It selects restatement only, with exact arithmetic and a 20% rate.

Reconstruct from the original Q4 opening snapshot, with zero prior entitlement,
zero participation prepayment and no recognized corrections. Independently
recompute the immutable original issued result. Replace original application 500
with eligible 450 and reconciled 50 outside the selected eligible scope, preserving
bank cash 500. Original entitlement 100 becomes 90; delta is -10. Separately
evidenced cash actually disbursed 80 against the original obligation leaves 10
outstanding as of the February cutoff. No new disbursement or future offset is
authorized or generated. Overpayment requires another policy and blocks here.

The affected-period state stores revised entitlement and correction recognition,
not February cash as a Q4 closing balance. The output separately labels actual
paid and outstanding as of cutoff. Every supplied observation string is retained
verbatim in canonical input artifacts; typed output observations use the exact
Instant codec's UTC rendering. Q4 effective dates, February authorization and
observation instants, and actual disbursement instant have separate meanings.
Availability uses strictly-before Instant comparisons, including exact fractional
seconds. Approval must precede observation; disbursement must precede observation.

Correction, replacement, original application/run/opening, obligation and evidence
identities are explicit typed references, pinned in the complete canonical inputs.
The current manifest schema has no original-run field; no new global schema or
pretend manifest field is introduced. Source checks reference relationships;
canonical constraints bind opening provenance, period, asset and participant.
Each state key has one writer. Reusing candidate closing state as original opening
fails; a previously recognized correction also fails. Repeating the same complete
immutable reconstruction produces the same candidate history rather than adding
another movement. This is a single authorized restatement route, not an engine
for replaying arbitrary historical periods and dependencies or concurrent commits.

Discriminating cases include unauthorized or prospective-route attempts, wrong
opening, stale references, duplicate/already-recognized correction, nonconserved
reallocation, exact cutoff, changed bank cash and actual-paid-over-revised.
