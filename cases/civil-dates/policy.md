# Supplied versioned named-zone day relation

`SYNTHETIC-CIVIL-DATE-01`, revision `1`. This finite synthetic
`research_assumption` relation is not a general timezone engine, a current IANA
database, or a jurisdiction's legal clock/calendar. No ambient timezone or clock
is consulted. Events must name their exact original zone and version.

Supply one original Gregorian local-date cell for every day of each zone's
declared half-open local coverage. Each cell retains local Date, original UTC
interval start/end, start/end offset minutes, scope, source and evidence. Offset
convention is explicitly local = UTC + offset. The cell's UTC start must equal
its local midnight minus its start offset; end must equal next local midnight
minus its end offset. Adjacent local dates must have contiguous offsets and UTC
boundaries. Intervals must be positive and cannot overlap within one versioned
zone. Different explicit zones/versions may overlap in UTC.

For each original event occurrence Instant, select the unique containing
half-open UTC interval in that event's zone/version and return the cell's local
Date. Exact start equality is included; exact end equality belongs to the next
cell. Preserve arbitrary fractional-second precision. Missing coverage is an
error, not a default UTC date. Occurrence cannot follow observation; observation
and all source evidence must be strictly before the explicit cutoff.

The disclosed synthetic West-Shift zone has 24/23/24/25/24-hour cells for
March 6 through March 10, 2026, using supplied offsets -480 and -420 minutes.
East-Fixed uses supplied +120-minute offsets over the same local dates. These
specific transitions make the method testable; they assert nothing about real
DST dates or locations. Offset changes are given only at cell boundaries; this
relation classifies civil dates and does not infer an event's local clock time
or exact within-day offset.

Mechanical validation checks Gregorian date/offset/midnight consistency, complete
local populations, version/scope/evidence and nonoverlapping contiguous intervals.
It returns original records, without event-specific solved civil dates. The
independent oracle and later SPL implementation separately select event answers
from the original daily relation. The profile bounds are four versioned zones,
32 days per zone and 128 events; these are finite engineering limits, not a
capacity result or universal calendar restriction.

Missing/duplicate dates or IDs, wrong zone/version, inconsistent interval/offset,
gaps/overlap, wrong scope/evidence, unavailable observations and outside coverage
block. No money, rate, payable, bank payment or implicit jurisdictional rule is
calculated by this method.
