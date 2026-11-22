# Disclosed reserve deadline extension case

This is an open, selected synthetic reserve example. Its topic and expected
values are public to the development agents. It is not an unseen evaluation.
All amounts are USD, the reserve has one explicitly identified vintage, and
release is a reserve movement rather than bank payment evidence.

The E0 baseline consumes a separately evidenced supplied deadline. It compares
the close date with that deadline, releasing the full available balance on or
after the deadline under the inclusive policy. The close date must fall in the
declared half-open accounting period; evidence must be observed strictly before
the pinned cutoff. The deadline cannot precede vintage creation, and availability
must be nonnegative. The canonical state key includes agreement, holder, pool,
purpose and vintage. January 31, 2025 creation with supplied February 28 deadline
and available 20 releases 0 on February 27 and 20 on February 28.

The proposed E1 method derives the deadline from original vintage creation by
adding an explicitly supplied natural number of calendar months. `clamp_day`
preserves the day where valid and otherwise uses the last target-month day.
`reject_invalid_day` rejects a nonexistent target day. It does not use a fixed
number of days, preserve end-of-month status implicitly, or repeatedly roll a
previously clamped deadline. Nonnegative months and Gregorian years 0001-9999
are the initial supported domain. The inclusive release policy is otherwise
unchanged. A new source/policy/module identity distinguishes this method from
the supplied-date baseline.

The neutral fixture's civil-date observations are represented at UTC start of
that date, with cutoff at UTC start of the next date after observed_through.
This is the declared synthetic transport convention, not a claim about actual
source observation times. No professional or historical interpretation approval
is inferred. The engineering freeze and attempted encoding must precede API
implementation; legitimate supplied-date or calendar-table workarounds remain
part of the experiment record.
