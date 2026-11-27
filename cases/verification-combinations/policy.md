# Synthetic quarterly advance recovery policy

The agreement measures a participant's net receipts for each Gregorian
calendar quarter. The receipt and posted-cost appendices check each supplied
period-scoped feed for unique fact identity and membership in that quarter.
The period scope must match the recovery ledger's agreement, participant and
pool. Each new quarter starts at the previous closing boundary. The opening
advance and the period's net receipt basis are nonnegative.

The approved launch rule pays a 50% share and has priority over the 25% volume
rule. The volume rule applies to net receipts at least USD 0.10. The fallback
share is 10%. Calculate the exact participation on total receipts less total
admitted posted costs, then round the resulting participation once to USD 0.01
with half-even ties. Apply the lesser of the rounded participation and opening
advance to recoupment, pay the remainder, and carry the remaining advance and
the quarter's ending boundary to the next quarter.

The sample scopes and approvals are synthetic supplied inputs. The validation
checks pertain to the rows in the supplied feed. Completeness and eligibility
of a real feed depend on the agreement and its evidence.
