# Selected synthetic MQP prospective fee history

This calculation is the RR-03 selected synthetic reconstruction. Its output is
adjusted receipts **before RPPA allocation**, not a final producer participation
or payment. The neutral fixture README identifies the filed provisions and the
interpretation/evidence limitations.

Use explicit agreement, uncrossed project/pool and USD scope. Supply the original
opening actual-payment tracker, distinct fee-available tracker and complete
relevant payment registry. Validate evidence before the pinned instant cutoff;
the neutral adapter uses explicitly synthetic UTC start-of-observation-date and
next-day-cutoff transport. Other-project events do not update these trackers.

Order selected period events by (civil effective date, supplied sequence), rejecting
ties and duplicate event identities before any economic transition. Sequence is
an explicitly supplied economic policy. Accrual never counts as actual payment.
Actual cash payment increases the actual tracker. Under `agreement_date`, disputed
cash becomes fee-available only when a linked agreement confirms the same amount
and actual date. Under the separately selected `actual_date` sensitivity it is
available when paid. An agreement cannot credit the amount twice. Missing prior
payment, undeclared dispute status or a changed agreed amount/date blocks this
bounded method. The payment registry is typed opening/closing state, not a list
of inferred disbursements.

For each eligible receipt apply the selected prospective rate to the whole
receipt using the fee-available tracker immediately before the event. The named
comparison policy is `at_least` or `greater_than`; it is visible in the result.
The principal U.S. TV license receipt class is excluded. All calculations are
exact without a rounding stage, and opening availability cannot exceed actual
payment. No future receipt is repriced or fee correction automatically inferred.

Opening actual/available trackers are 900. Three eligible receipts of 100 under
the agreement-date selection incur fees 10, 10 and 20: total fee 40, adjusted
receipts 260. The actual-date alternative yields 10, 20 and 20: fee 50, adjusted
receipts 250. Both close trackers at 1,000. Prospective correction applications
are a separate explicitly authorized method, with their own original fee link,
capacity, carry and replay controls; they are not manufactured by this example.
