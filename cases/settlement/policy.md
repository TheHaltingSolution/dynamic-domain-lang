# Supplied withholding and minimum-payout policy

`SYNTHETIC-SETTLEMENT-01`, revision `1`. Proposed synthetic
`research_assumption`; this is a calculation policy for the fixture only.

Aggregate current gross earned USD entitlement. Apply the explicitly supplied
rate in `[0,1]`, rounding withholding once to a USD cent with half-even rounding.
Current net entitlement is gross earned less that withholding. Input money,
state, threshold, issuance, payments and applications are integral USD cents;
non-cent inputs block. No tax-law applicability, remittance or filing is inferred.

Add current net entitlement only to opening **unissued** net entitlement. If
that candidate is at least the supplied minimum payout, it is eligible for a
new issue notice. Equality qualifies. A new issue is separately supplied evidence,
at most one positive notice for the full eligible candidate. Eligibility alone
creates no issuance. Amounts without an issue notice remain unissued, including
eligible amounts. Opening net entitlement is neither earned nor withheld again.

Previously issued unpaid obligations retain their original identities, source,
evidence, issue amounts and paid-to-date. They remain due regardless of this
period's new-issuance threshold and are never included in a replacement new issue.
Actual payments are separate evidenced cash events. Applications must allocate
each payment completely to identified old or new issued obligations without
exceeding any remaining balance. Duplicate or previously recognized category/ID
pairs block. No bank transfer is requested or executed.

Closing unpaid is closing unissued entitlement plus each remaining issued
obligation. It reconciles to opening total unpaid plus current net entitlement
less current actual payments. Preserve original issuance lineage and cumulative
paid-to-date. Remove fully paid obligations from active state while retaining
their recognized issuance IDs.

Require the explicitly supplied complete-settlement-population attestation for
the exact scope/period, plus all referenced source evidence. Without it, missing
payment evidence is `no_event_supplied` and cannot establish numeric zero paid
or consumable carry. With complete attestation, empty event populations are
`complete_no_events`. All observations must be strictly before the exact cutoff.
This fixture supplies a complete selected-period view; out-of-period records block.

Keep agreement, participant, pool, asset, USD currency, policy, purpose and period
boundary fixed across carry. Reuse the exactly serialized prior closing state
only for an adjacent successor period and with its supplied predecessor summary.
Case identity is not a canonical result digest; canonical predecessor references
remain separate metadata. Genesis explicitly supplies zero balances and no
recognized history. No historical correction, transfer, tax approval or universal
settlement policy is authorized by this fixture.

The baseline earns 100, withholds 10, nets 90, supplies an issued notice of 90 and
an actual payment/application of 80, and carries the original notice's remaining
10. A subsequent gross 10 nets 9, remains unissued below threshold 25, and carries
that 9 alongside the original issued 10. A further gross 20 nets 18; the new
candidate is 27, not 37. A separately supplied notice of 27 and payment 20 applied
10 to each notice leave only 17 outstanding on the new notice.
