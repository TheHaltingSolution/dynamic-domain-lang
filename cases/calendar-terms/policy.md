# Finite fiscal calendar and amended-term policy

`SYNTHETIC-CALENDAR-TERMS-01`, revision `1`. Proposed synthetic
`research_assumption`; no universal fiscal, holiday, legal-calendar or proration
default is asserted. Existing generic data, selection and folds can express this
method. It does not require a new builtin and does not extend the existing month
clamp into a claim of complete calendar support.

Use the supplied versioned calendar and complete original daily population over
its explicit half-open coverage. Validate Gregorian dates, ordinal epoch
`0001-01-01 -> 1`, ISO weekday numbers 1 through 7, unique rows and dates, and
complete fiscal-period partition without overlap or gaps. The method's declared
engineering bound is 400 covered days. Fiscal periods and source/evidence are
supplied data; display labels do not determine boundaries.

Closed weekdays are an explicit calendar list; supplied holiday-closed flags
also close a day. A row's closed flag must agree with that declared relation.
There is no ambient weekend or holiday lookup. Proration-eligible flags are
separate source facts and may include closed business days under this method.

For the selected fiscal period, count all eligible original daily rows to obtain
the denominator. For each day, among terms effective in its half-open interval
and signed/recorded on or before the explicit civil as-of Date, select the unique
greatest revision. Same winning revision ties block, even when amounts match.
Retain original and amended terms, explicit predecessor IDs, source and evidence.
Predecessors must exist with lower revision, matching economic scope and no
later recorded date. No available term is the explicitly selected `inactive_zero`
case, rather than an inferred missing monthly amount.

Each eligible active day contributes the selected exact nonnegative monthly
amount divided by the derived denominator. Sum exact daily contributions with
no rounding. An empty eligible denominator blocks. A zero monthly amount is an
active selected term, distinct from inactive days.

Signing and recording are civil Dates, with signing no later than recording;
as-of equality is included. Separate supplied observation Instants and evidence
must precede the exact cutoff. No timezone conversion or observation instant is
inferred from a civil date. This is version selection from the supplied snapshot,
not a full bitemporal reconstruction of historical observed knowledge.

For a separately supplied deadline, `following` chooses the first supplied open
day on or after it; `preceding` chooses the last open day on or before it. An
already open deadline stays unchanged. Missing due rows or insufficient calendar
margin block; do not invent an outside day or modified-following convention.

Baseline fiscal period April 6 through, excluding, May 6, 2026 contains 30
eligible daily rows. Both original and amended terms apply only April 26 through
May 6, so the first 20 days are inactive. Revision 1 monthly amount 240 was
recorded April 10; revision 2 monthly amount 300, referencing revision 1, was
recorded April 20. As-of April 19 gives 80; equality at April 20 selects revision
2 and gives 100 from 10 active days. May 1 is a supplied synthetic closed
holiday. Following selects May 4; preceding selects April 30. These are fixture
flags, not claims about an external holiday.
