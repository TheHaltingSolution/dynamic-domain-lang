# Finite fiscal and amended-term controls

23 November 2026. This independent C14 design and neutral oracle precede the SPL
implementation. Existing generic typed records, finite relations, comparisons,
unique selection and folds can express the finite method; no necessary compiler
extension is claimed. The existing calendar-month clamp is a different feature.
The [policy](../../cases/calendar-terms/policy.md) is explicitly synthetic
`research_assumption`, not legal-calendar or interpretation approval.

The [neutral fixture](../../cases/calendar-terms/neutral.json) contains 40 original
daily calendar rows over April 1 through May 11, 2026, including margin outside
the selected fiscal period April 6-May 6. The daily rows carry dates, ordinal and ISO
weekday metadata, separate supplied proration eligibility/holiday/closed flags,
calendar ID/version, economic scope, and original source/evidence references.
Fiscal periods partition the complete coverage. No source financial answer,
denominator, numerator, prorated amount or rolled deadline is supplied.

`validate_calendar(data)` in `oracles/calendar_terms.py` mechanically validates
the complete Gregorian population, dates/ordinals/weekdays, flag relation,
version/scope/evidence, and nonoverlapping complete fiscal partition. It returns
indexes of original rows, without pricing, selecting terms or calculating
financial day counts. The explicitly declared engineering bound is 400 days.
Those checks are distinct from the financial `calendar_terms(data)` oracle,
which counts eligible source rows, selects dated terms, computes exact daily
amounts and derives a business-day relation. Neither imports compiler helpers.
The SPL implementation must derive the financial denominator/numerator itself;
a mechanical adapter must not inject the oracle's solved values.

The exact top-level neutral structure is:

```text
schema_version = calendar-terms-neutral/1
case_id, scope, calendar, fiscal_periods[], selected_period_id
days[], terms[], as_of, deadline, policy, cutoff, evidence[]
```

Economic scope is exactly
`{contract_id,participant_id,pool_id,asset_id,currency}` and currency is USD.
`calendar` has `{id,version,coverage:{start,end},closed_weekdays,
ordinal_epoch,evidence_ref,source_ref}`. The ordinal epoch is explicitly
`gregorian_0001_01_01_is_1`. Each fiscal record has
`{id,calendar_id,calendar_version,scope,period:{start,end},evidence_ref,source_ref}`.
It must lie inside coverage, and every covered date belongs to exactly one
supplied fiscal period. `selected_period_id` is a real record ID, not a label
parsed into a calendar interval.

Each daily row is exactly
`{id,date,ordinal,weekday,proration_eligible,holiday_closed,closed,calendar_id,
calendar_version,scope,evidence_ref,source_ref}`. `ordinal` and ISO `weekday`
are original integral metadata, mechanically checked against Gregorian date.
The closed relation is the declared closed-weekday set or the supplied holiday
flag. Baseline closed weekdays are explicitly 6/7, with a synthetic May 1 holiday.
Changing those flags is changing calendar input, not importing a universal rule.
Eligible calendar days are a separate financial population; closed days may
remain eligible, so business-day rolling does not silently change proration.

Each original or amended term is exactly
`{id,revision,predecessor_id,effective:{start,end},monthly_amount,scope,
signed_date,recorded_date,observed_at,evidence_ref,source_ref}`. Revisions are
positive integers. Root terms have revision 1 and empty predecessor_id; other
terms must reference an existing lower revision in the same scope, recorded no
later. Explicit increasing revision eliminates predecessor cycles. Competing
highest known effective revisions are ambiguous, even at equal amounts.

Both signing and recording use civil Dates. Signing must precede or equal
recording. A candidate is known when both Dates are `<= as_of`, including exact
equality. Observation availability is separately `observed_at < cutoff` on exact
Instants. This method neither synthesizes a recording Instant from a Date nor
claims full bitemporal observed-knowledge reconstruction. Every supplied term
and evidence record is validated, including unselected or later-known terms.

For each daily source row in the selected fiscal interval, choose the unique
highest known effective revision, or the named `inactive_zero` outcome. Let D
be the number of proration-eligible source rows. An eligible active day under
monthly amount M contributes exactly `M/D`; ineligible/inactive rows contribute
zero. Empty D blocks. Sum daily contributions without rounding. The numerator
is active eligible rows, derived from actual selected terms. When monthly amounts
vary across amendments, retain per-term days and exact monetary contributions;
do not replace them with one misleading aggregate monthly amount.

| As-of Date | Selected active term | Derived denominator / numerator | Exact result |
| --- | --- | --- | --- |
| April 19 | v1, monthly amount 240 | 30 / 10 | 80 |
| April 20 equality | v2, monthly amount 300 | 30 / 10 | 100 |

Both baseline terms are effective only April 26-May 6, so the first 20 fiscal
days are explicitly inactive. The fixture contains no old term earning 240 on
those first 20 days. A genuinely earlier active term would add its own prorated amount.
Effective starts are included and ends excluded. Zero monthly amount remains a
selected active term; it does not turn into the no-term outcome.

`deadline` is `{date,roll,source_ref}`. `following` selects the minimum supplied
open date greater than or equal to the due date. `preceding` selects the maximum
open date less than or equal to it. Baseline May 1 following gives May 4, and
preceding gives April 30. No result is invented when due rows or required open
neighbors are outside supplied coverage. Modified following, inclusive-language
normalization, legal holidays, timezones and jurisdictional rules need separately
named policies or original evidence.

`policy` pins `{id,revision,proration,term_selection,no_term,rounding,evidence_class}`
to `SYNTHETIC-CALENDAR-TERMS-01@1`, `eligible_days_selected_fiscal_period`,
`greatest_revision_unique`, `inactive_zero`, `exact_no_rounding`, and
`research_assumption`. Evidence records are
`{id,scope,observed_at,kind}`. Exact monthly money is nonnegative neutral decimal
or rational strings, never binary floats. The independent oracle uses standard
library Gregorian date operations and Fraction arithmetic as financial controls;
the adapter/SPL implementation must preserve original calendar and term lineage.

Missing/duplicate dates, IDs, fiscal gaps/overlap, wrong metadata/flags, calendar
version/scope/evidence mismatch, missing predecessors, ambiguous amendments,
as-of/effective boundary behavior, zero/inactive populations, exact amounts and
finite business-day margins are mandatory controls. This slice does not complete
all fiscal/legal calendars, amortization/day-count conventions, historical replay,
distributed execution, actual payments or full C14 contract coverage.

Independent authoring verification: `python -m unittest
Tests.test_calendar_terms_oracle -v` passed 18 test methods in 0.029 seconds on
23 November 2026. This covers the original population, amendments, exact daily
proration and finite business-day relations. It records oracle checks only;
native, emitted and canonical execution require separate integration evidence.
