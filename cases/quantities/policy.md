# Synthetic download participation policy

QUANTITY-PARTICIPATION selects a supplied half-open period view. Each usage row
must have its effective date within [period.start, period.end), a unique record
identity, one referenced supplied evidence event, and an observation strictly
before cutoff. Evidence events also require observation strictly before cutoff.
The adapter transports supplied facts and terms without calculating economics.

The exact sum of nonnegative Download quantities times a nonnegative USD per
Download rate is gross USD. Gross times the declared participation in [0,1] is
earned USD. The selected terms require exact arithmetic without rounding. Zero
and fractional usage are valid. Signed core values remain available to other
policies. The tagged meter carries opening quantity plus this period's quantity
into a separately invoked successor. Actual payments are outside this witness.

This is a proposed synthetic calculation policy, not an approved contract
interpretation, settlement, ledger ingestion claim or compiler correctness proof.
