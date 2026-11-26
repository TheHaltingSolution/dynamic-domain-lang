# Selected exact usage-time conversion

This is a synthetic engineering fixture for B-C02-CONVERSION. It is not a
sourced royalty interpretation or a previously inexpressible financial method.
The declared feature is `spl.usage-time/1`; the explicit relation is
`spl.usage-time/1:minute-hour`. Exactly sixty UsageMinute equal one UsageHour.
Both conversion directions are explicit. Same-endpoint conversion, unrelated
units, a missing feature/relation, and a price in another unit or currency fail.

The original ledger supplies 90 UsageMinute and an independent original price
quote supplies USD12 per UsageHour. The selected calculation gives 1.5 UsageHour
and USD18. No amount is rounded. Fractional and signed core quantities retain
their sign and exactness; a nonnegative contractual measurement policy would
need a separate explicit choice. A missing price permits a quantity-only result
and makes no financial inference.

The comparison uses original quantity150 Minute at an independently supplied
USD.20 per Minute quote: USD30. The new representation converts150 Minute to
2.5 Hour and applies the independently supplied USD12 per Hour quote, also
giving USD30. The old representation remains valid. The new interface adds
checked, explicit unit conversion rather than creating new financial arithmetic.

The oracle retains original measurement/quote IDs, evidence references and
numeric spellings. Neither a solved converted quantity nor a conversion factor
is an input. It independently computes exact base-minute magnitude, converted
quantity and earned money. It imports only the Python standard library and
does not import any compiler, adapter or SPL calculation.

These controls do not establish source/IR admission, owner-context compatibility,
tagged codec behavior, state identity/carry, catalog pin validation or any native
execution. The implementation must test those separately, including forged
59:1 relations against the immutable60-minute Hour definition. No currencies
other than USD, civil-time/calendar conversions or implicit conversion are
selected by this fixture.
