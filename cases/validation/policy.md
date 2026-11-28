# Period-scoped Skouras/Ventura feed validation

These appendix rules apply to inputs prepared for a single settlement period.
The caller supplies eligible facts already assigned to that period. A crossing
row fails validation and the settlement returns the validator's diagnostic.

| Input format | Duplicate check | Date checked |
| --- | --- | --- |
| `List<SVReceipt>` | Each `fact_id` occurs once in this receipt feed. | `cash_received_date` lies on or after the start and before the end of the supplied `Period`. |
| `List<SVPostingCost>` | Each `fact_id` occurs once in this posted-cost feed. | `recognition_date` lies on or after the start and before the end of the supplied `Period`. |

Both feeds admit empty lists. They use their existing exact USD, date, ID and
record field types. The typed binding decoder checks those representations.
The linked SPL checks the relationship among the supplied rows and period.
Uniqueness concerns each supplied feed. The parties and their records establish
eligibility, completeness, and whether different IDs refer to the same event.

The synthetic example applies a 20% participation share to admitted cash less
admitted posted costs. It has empty opening and closing state. The exact
expected amount is `(90 + 60 − 25) × 0.20 = 25` USD.
