# Finite supplied named-zone civil dates

23 November 2026. This independent B-C14-ZONE design precedes executable SPL.
It addresses the finite supplied named-zone evidence variant of F10/C14, not a
general timezone engine or a new necessary compiler primitive. Existing exact
Instant comparisons and a finite daily relation can select the original cell.
The stronger required-extension gate remains unchanged.

The [neutral fixture](../../cases/civil-dates/neutral.json) uses two explicitly
synthetic versioned zones. West-Shift has five original local-day cells with
durations 24, 23, 24, 25 and 24 hours. East-Fixed has five 24-hour cells at a
separately supplied +120-minute offset. No current IANA or jurisdictional rule
is asserted. Scope is the exact contract/asset context, without introducing a
money or currency dimension into this nonfinancial relation.

```text
schema_version = civil-date-neutral/1
case_id, scope {contract_id,asset_id}, cutoff, policy
zones[], days[], events[], evidence[]
```

`policy` is `{id,revision,selection,offset_convention,coverage,evidence_class}`,
pinning `SYNTHETIC-CIVIL-DATE-01@1`,
`unique_containing_half_open_utc_cell`, `local_equals_utc_plus_minutes`,
`complete_declared_local_dates` and `research_assumption`.

Each versioned zone record is
`{id,version,scope,local_coverage:{start,end},source_ref,evidence_ref}`. IDs may
repeat across distinct versions; `(id,version)` is the identity. There is no
latest-version fallback. Each daily record is
`{id,zone_id,zone_version,scope,local_date,utc_start,utc_end,
start_offset_minutes,end_offset_minutes,source_ref,evidence_ref}`.
Daily IDs are globally unique; local dates are unique within the named version.
Offsets are explicit signed integral minutes between -1439 and +1439. Four
versioned zones, 32 days each and 128 original events are the declared finite
engineering bounds, not demonstrated throughput capacity.

Mechanical validation `validate_zone_relation(data)` checks:

1. A complete Gregorian day census for every declared local coverage interval.
2. `UTC start = local midnight - start offset`, and
   `UTC end = next local midnight - end offset`, with exact arithmetic.
3. Positive intervals, adjacent local dates, matching end/start offsets and
   contiguous UTC boundaries, without gaps or overlaps within one version.
4. Scope, source/evidence references, exact observation availability and identity.

It returns indexes of original zone/day/evidence records. It neither selects
event cells nor attaches an event-specific civil Date. A later mechanical
adapter must preserve that boundary; event classification belongs to SPL.
Overlapping UTC coverage in different named zones/versions is intentional.

Each original event is
`{id,zone_id,zone_version,scope,occurred_at,observed_at,source_ref,evidence_ref}`.
Both original Instants are retained. Require occurred_at <= observed_at < cutoff;
all source evidence observations are also strictly before cutoff. The exact
independent `civil_dates(data)` oracle selects the unique day with
`utc_start <= occurred_at < utc_end` in that event's explicit zone/version.
No match blocks; multiple matches block rather than selecting physical order.
No clock, default zone, inferred observation, or event-specific solved date
enters the input. Exact fractional seconds remain rational, including values
finer than Python datetime's microsecond representation.

| Original UTC event | Explicit zone | Derived local Date |
| --- | --- | --- |
| March 7 07:59:59.9999999Z | West-Shift | March 6 |
| March 7 08:00:00Z | West-Shift | March 7 |
| March 8 06:59:59.9999999Z | West-Shift | March 7, the 23-hour cell |
| March 8 07:00:00Z | West-Shift | March 8 |
| March 10 07:59:59.9999999Z | West-Shift | March 9, the 25-hour cell |
| March 10 08:00:00Z | West-Shift | March 10 |
| March 8 06:00:00Z | West-Shift / East-Fixed | March 7 / March 8 |

The original local coverage is March 6 through, excluding, March 11, 2026.
West-Shift UTC coverage is March 6 08:00Z through March 11 08:00Z; East-Fixed
is March 5 22:00Z through March 10 22:00Z. The intervals themselves, rather than
a fixed 24-hour arithmetic assumption, determine the civil date.

Outputs preserve event IDs, both original Instants, original zone/version,
selected day cell, derived local Date, original interval, source and evidence.
They deliberately omit local wall-clock time and an event-specific UTC offset:
the supplied midnight boundaries do not specify the within-day transition
instant. Ambiguous/nonexistent local clock inputs, general DST resolution,
zone database updates, legal calendars, money and payments remain outside scope.

Required controls include UTC/local midnight equality, 23/24/25-hour cells,
submicrosecond boundaries, offset-equivalent Instant notation, multiple zones
and versions, no-match coverage, Gregorian/offset inconsistency, gap/overlap,
duplicate identities/dates, wrong version/scope/evidence, observation ordering,
and the prohibition on adapters supplying solved event dates. This finite method
fit strengthens supplied-zone evidence, not a universal timezone capability or
proof of an unavoidable language extension.

Independent authoring verification on 23 November 2026: `python -m unittest
Tests.test_civil_date_oracle -v` passed all 16 test methods in 0.019 seconds.
This records supplied-relation controls only; native and canonical execution
must independently derive event dates before their evidence variant is closed.
