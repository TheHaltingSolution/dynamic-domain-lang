# Metered usage across settlement periods

This [schedule](metered-period.spl) combines a half-open date filter, an
owner-scoped minute-to-hour conversion inside a quantity sum, an hourly USD
rate, half-even rounding, and a carried hour meter. It exercises typed zero
when a period contains no eligible activity.

- The first period includes 30 and 90 minutes, excluding a 45-minute row on
  the next boundary. Two hours at USD 1.0025 per hour earns exactly USD 2.005.
  Half-even rounding yields USD 2.00. From an opening third of an hour, the
  meter closes at seven thirds of an hour.
- The second period has no eligible minutes. It earns zero and keeps the
  same seven-thirds-hour balance.
- A third control supplies a per-minute rate for the second period. The
  artifact must reject it at binding admission and expose no partial result.

The [worked checks](../../Tests/test_verification_usage.py) run the actual
certified series and check these amounts and units independently of the
compiler and reference translator.
