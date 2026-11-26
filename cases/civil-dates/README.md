# Civil Date from original versioned day cells

This finite C14 supplied-zone profile selects an event's Date from an explicitly
named zone/version and original half-open UTC day interval. The independent
[oracle](../../oracles/civil_dates.py),
[design](../../docs/spl/civil-date-design.md), [policy](policy.md) and
[neutral relation](neutral.json) precede executable SPL. The synthetic West-Shift
relation contains 24, 23, 24, 25 and 24-hour cells; East-Fixed supplies a separate
offset. No IANA database, current jurisdictional rule or ambient timezone is used.

SPL matches `zone_id` and `zone_version` exactly, then requires exactly one cell
with `utc_start <= occurred_at < utc_end`. Midnight equality starts the new day;
an arbitrarily precise instant before it remains in the preceding cell. The
same UTC occurrence can therefore select March 7 in West-Shift and March 8 in
East-Fixed. Different explicit versions can also select different dates. There
is no latest-version or default-zone fallback.

Outputs retain original event/zone/version, both original timestamps, selected
cell/Date, original interval/offset endpoints and source/evidence references.
Original timestamp spellings survive transport alongside exact Instant values.
The relation does not identify an intraday transition Instant, so it supplies
neither a local wall-clock time nor an event-specific offset.

## Mechanical boundary and native selection

The adapter independently validates the original zone/day relation without
importing the oracle or inspecting event values. It checks Gregorian coverage,
complete original day populations, unique zone/version/day identities, explicit
integral offsets, positive intervals, midnight/offset equations and contiguous
UTC bounds with matching adjacent offsets. Exact fractions avoid datetime's
microsecond limit. This establishes the supplied relation's consistency; it
does not establish an external zone database or legal calendar's correctness.

The adapter transports the original rows and exact/lexical tags. It never
classifies an event, converts an event to a civil Date, or supplies solved Date
or cell-ID input fields. Event validation and unique interval selection run in
SPL. Mechanical table errors are adapter failures; event cutoff/version/reference
and interval-match guards execute in source. Tests distinguish those stages.
Additional physical-input negative tests deliberately bypass the neutral table
boundary only to exercise native ambiguous/no-match rejection; they do not make
an inconsistent original calendar valid.

All source evidence observations and event observations must be strictly before
cutoff; occurrence is no later than observation. Overlapping UTC ranges across
different zones or versions are intentional. Missing or ambiguous matches block
the entire event result rather than selecting a physical row or UTC Date.

## Generic execution metadata

The domain scope is exactly the original contract and asset, with no currency,
financial party, financial pool or payment measure. The generic module wrapper
requires an outer execution envelope. It retains the real contract/asset and
uses fixed `civil-date-reader`/`civil-date-evidence` labels solely as reader/pool
metadata, with purpose `civil_date_evidence_envelope_only`.

Manifest period is the envelope of original declared zone local-coverage bounds.
Every version's own coverage remains unchanged; the envelope contains all of
them and is never derived from event answers. It is execution metadata, not an
additional financial period or date-classification rule. Generic wrong-context
checks can reject contract/asset inputs before SPL; tests identify that boundary.
State is empty. Source results contain no money, currency or payment inference.

## Reproduction and limits

With the pinned environment and existing native kernel:

```powershell
python -m cases.civil-dates.build_modules
python -m unittest Tests.test_civil_date_oracle Tests.test_civil_date_modules -v
```

The generated template is intentionally unbound; execution binds current
compiler/runtime/module identities. Native test groups use canonical compare
(native IR, native-emitted Lean and reference), followed by separate execution
of Lean from the Python emitter with identical decoded inputs. Every event and
coverage output is compared to independent original-relation controls. Completed
artifacts are validated through `load_completed_result`.

Bounds are four zone/version pairs, 32 original days per pair and 128 events.
These are engineering bounds, not demonstrated capacity. Finite scans/folds
preserve arbitrary zone/version Text identities. General timezone resolution,
ambiguous/nonexistent local clock inputs, automatic rule updates, legal calendars,
monetary settlement and universal timezone/compiler proofs remain outside this
supplied-evidence variant; the stronger required-extension gate remains separate.
