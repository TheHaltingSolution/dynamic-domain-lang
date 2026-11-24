# Original gross/net and per-unit royalty bases

`SYNTHETIC-PARTICIPATION-BASES-01@1` selects four separate C02 policies.
These are development assumptions, without professional contract approval.

Original receipts125 and separately identified deductible costs25 establish
gross125 and net100. The complete original Download measurement is100.
Approved terms supply percentage.20, unit royalty USD1.50/Download and a
separate participation share.50. The selected methods are:

| Method | Calculation | Control |
| --- | --- | --- |
| gross_percent | Gross receipts times the percentage | USD25 |
| net_percent | Gross receipts less original deductions, then percentage | USD20 |
| unit_rate | Original Download quantity times USD/Download | USD150 |
| unit_rate_then_participation | Unit royalty, then one separate participation share | USD75 |

The percentage and per-unit royalty are distinct kinds of rate. The share is
applied once only by the fourth method. Gross/net percentages do not also apply
that separate participation share. The unit methods do not deduct monetary
costs from the quantity or apply the percentage. All material measures, chosen
basis/rate, pre-participation royalty and applied share remain visible.

All three complete populations and their original rows are validated for every
method, including unused monetary/quantity measures. Row IDs and original
references are unique across the tables; duplicate equal contributors are not
silently collapsed. The population declarations identify original row IDs and
reported totals, not financial answers supplied to the compiler. Empty complete
populations are known zero; missing completeness is unknown and blocks.

Agreement, participant, asset, pool and USD scopes must match exactly. Periods
are half-open calendar dates. Original economic dates are inside the period;
each original is observed no later than its complete population, which is
observed after period end and strictly before the report cutoff. Approved
terms cover the whole period and are known by every original row observation.
Timestamp comparisons use exact UTC seconds, including arbitrary decimal
fractions and supplied numeric offsets. No float or microsecond rounding is
used. Original timestamp strings and Unicode spellings remain intact. Calendar
period boundaries denote UTC midnight; leap-second spellings require a separate
time policy and reject here.

Each table admits at most32 original rows. Nonnegative fractional measures and
zero are valid. Costs exceeding gross require a separately selected loss policy
and reject here; the implementation must not insert a floor. There is no
rounding: all intermediate and final values are exact rationals. Currency is
USD and quantity Download. No FX, implicit conversion, payment/issuance,
state carry or contract amendment is part of this stateless method.
