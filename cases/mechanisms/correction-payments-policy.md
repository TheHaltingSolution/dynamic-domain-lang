# Synthetic supplied-revision obligation reconciliation, revision 1

This proposed registration makes the existing CORR-01 reconciliation executable
through the generic canonical interface. It does not implement full historical
restatement. `SYNTHETIC-CORR-RESTATEMENT` is the unchanged source citation and
`synthetic-restatement` the unchanged fixture authority; both are proposed
synthetic policy decisions. Neither name nor successful execution establishes
professional approval or supplies historical financial evidence.

Scope is one agreement, participant and pool, with exclusive purpose
`obligation_reconciliation` and USD amounts. The original issued amount, revised
entitlement and correction approval are supplied inputs. The source checks the
correction approval and authority, preserves the original issued amount, sums
approved actual payment applications under the required authority and reports
the residual. Duplicate payment event identifiers are rejected. Payment scope
and obligation must match, and all supplied amounts must be nonnegative.

The selected payment cutoff remains a Date: paid_date must be strictly earlier
than payment_cutoff. The default run manifest uses midnight UTC at that selected
date as its run cutoff. PaymentApplication contains no observed_at field, and
this registration does not invent one or claim an as-of observation check.
Changing the manifest cannot change the independently supplied payment Date
selector. Replacing this policy with an observation-aware reconstruction needs
new source, input evidence and a deliberately revised policy/interface identity.

Exact arithmetic without rounding yields revised entitlement minus actual paid.
An overpayment blocks because recovery/negative-obligation treatment is not
selected. The independent baseline has original issued 100, supplied revision
90, payment 80, delta -10 and outstanding obligation 10. The output is a named
reconciliation result, has no closing state, and creates neither a new payable,
an issued correction nor a payment. Full CORR historical dependency replay,
revised entitlement computation, prior-run version lineage, reversals and an
orchestrated historical correction state remain unimplemented.
