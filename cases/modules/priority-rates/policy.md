# Cedar priority-rate synthetic method, revision 1

This original synthetic agreement, Cedar Distribution / Willow Screen Trust,
uses one declared cash base in USD. Cedar gives Oak Participant and Pine
Participant separate statements; their supplied participation shares sum to one.
These names and numbers have no relation to an issued historical settlement.

Within the supplied half-open effective interval, US receipts use the ordinary
rate (20% in the example), Canada uses the higher-priority Canada rate (40%),
and France selects a valid zero rate. No ordinary rule for another territory
means NO_APPLICABLE_RULE. A deliberately enabled competing Canada rule ties
the greatest priority and blocks the entire connected settlement, even though
its numerical rate is equal. No fallback or implicit file-order choice applies.

Cash, rates, shares and effective dates are run terms. Enabling the competing
rule is a methodology variant recorded in method identity. No rounding occurs
in this witness: exact participant amounts sum to the exact entitlement. There
is no state, reserve, recoupment, payment, FX or implied bank disbursement.

Decision CEDAR-PRIORITY is a proposed synthetic interpretation, not contract
approval. Discriminators are US 20, CA 40, FR 0, absent rule, highest tie,
half-open effective end, participant isolation and a permitted rate-term edit.
