# Named staged deduction policies

`SYNTHETIC-STAGED-DEDUCTIONS-01`, revision `1`. All six variants are explicit
synthetic `research_assumption` selections. None is a default interpretation of
another agreement. This method calculates earned entitlement, not issuance,
actual payment, tax or losses. All money is nonnegative exact USD; share and fee
rate lie in `[0,1]`. There is no implicit rounding or floor.

Each receipt supplies gross and selected net as two views of that same original
activity. Sum them separately; never add gross and net as separate cash. Net
cannot exceed gross. Receipt recognition dates and source/evidence references
are supplied. All current rows must belong to the selected half-open period.

Only costs in the explicitly selected category set are eligible. The cumulative
cap covers those cost deductions only, not the separately calculated fee. Admit
costs in ascending explicitly authorized unique nonnegative sequence, up to the
remaining scoped cap. Physical input order conveys no authority. Retain each
original cost and its deducted amount/disposition, including excluded and
cap-limited costs. No remainder is carried for later reuse: any already recognized
original cost ID blocks if presented again, including an excluded or partially
admitted row. Reclassification or residual claims require a different policy.

Let G be gross receipts, B selected net receipts, D admitted eligible cost, f the
fee rate and s the participant share. Gross-fee variants measure fee on G.
Net-fee variants measure fee on the stage balance: B-D for pre-basis and B for
pre-share/post-share.

| Explicit variant | Fee F | Earned entitlement |
| --- | --- | --- |
| pre_basis_gross_fee | G*f | (B-D-F)*s |
| pre_basis_net_fee | (B-D)*f | (B-D-F)*s |
| pre_share_gross_fee | G*f | (B-F-D)*s |
| pre_share_net_fee | B*f | (B-F-D)*s |
| post_share_gross_fee | G*f | (B-F)*s-D |
| post_share_net_fee | B*f | (B-F)*s-D |

Require every selected stage balance, participation basis and earned amount to
be nonnegative; do not replace a negative value with zero or carry a signed loss.
Even a zero share does not excuse a negative underlying stage. With G=B=1000,
D=500, s=.8 and f=0, pre-share earns400 while post-share earns300. With f=.1,
pre-basis net-fee earns360, while pre-share net-fee earns320. These differences
are the intended economic distinctions, not rounding artifacts.

Opening state retains policy, variant, cap limit, scope, deduction purpose,
period boundary and original cost history. Consumed cap must equal the sum of
historical deducted amounts. An adjacent successor receives the serialized prior
closing state and matching predecessor summary; it cannot silently reset the
cumulative cap or deduct the same original cost again. Case identities are not
canonical result digests. Source observations and referenced evidence must be
strictly before the exact cutoff, including prior cost evidence retained for carry.
