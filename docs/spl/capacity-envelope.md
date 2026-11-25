# Measured RR03 capacity envelope

The measured capacity of this SPL checkpoint covers a serial comparison and
audited publication of 100- and 1,000-record synthetic film-participation
closes. Both sizes also support the demonstrated sequence of four quarterly
closes using publicly reloaded saved state. The workload has one pool, one
participant and distributor, two or eight pictures, and exact two-way splits
on a tenth of cash parents. The input population, financial controls and clock
boundaries are specified in the [measurement protocol](capacity-measurement.md).

## Source and operating conditions

The campaign used Git commit `87d140df4aada6c800fcd96932bb2a24c84761fa` in the
short physical checkout `C:/spl-fp`. The pinned Windows Lean 4.35.0 build,
103 default Lake jobs and both smoke executables passed. The coordinator used
embedded Python 3.12.8 on Windows 11 Pro build 26300, with an Intel Core Ultra 7
270K Plus (24 logical processors) and 68,053,336,064 bytes of RAM. There was one
worker. The earlier compiler-candidate regression ran on the same host while
the final integrated regression was held. Background CPU and filesystem cache
were uncontrolled. Pre- and post-campaign CPU snapshots are retained.

## Independent repeated closes

All four samples passed at each size. The 100-record series began with an
empty compiled-target cache. One miss produced the target and took 7.540 s
to API return plus 0.441 s for the consumer reload. Its compiler children
took 0.560 s for Lean code generation, 0.275 s for C compilation and
0.878 s for linking. The maximum compiler-child peak working set was
307,838,976 bytes. The subsequent observations and all 1,000-record
observations reused verified target bytes.

| Original records | Cached samples | API median / p95 / max (s) | Consumer median / p95 / max (s) | Through consumer median / p95 / max (s) |
| ---: | ---: | ---: | ---: | ---: |
| 100 | 3 | 4.635 / 4.640 / 4.640 | 0.429 / 0.432 / 0.432 | 5.062 / 5.072 / 5.072 |
| 1,000 | 4 | 34.679 / 34.694 / 34.694 | 5.504 / 5.665 / 5.665 | 40.183 / 40.358 / 40.358 |

Nearest-rank p95 equals the maximum at these sample counts. Every sample
used the same exact input for its size and wrote to a fresh output directory.
A 1,000-record cached close spent median 9.432 s in the native audit child,
0.045 s in the compiled settlement child and 0.160 s in the reference child.
The five graph-validation child medians were 5.236 s (execution),
5.210 s (attachment), 5.858 s (publication), 5.515 s (validated return) and
5.462 s (consumer reload). Publication and load child clocks include
integrity checks and file handling. These phase clocks describe inclusive
work within the public timing boundary. No audit optimization was needed
for the measured workload.

| Original records | Neutral input (bytes) | Bound input, canonical encoding (bytes) | Canonical result (bytes) | Compact wire (bytes) | Expanded logical audit (bytes) | Nodes / edges |
| ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| 100 | 105,542 | 64,961 | 32,654 | 1,527,895 | 5,144,850 | 2,251 / 3,008 |
| 1,000 | 949,426 | 572,236 | 271,743 | 43,503,437 | 776,599,360 | 64,480 / 88,010 |

Repeated workflow samples produced identical compact wire bytes within each
size. At 1,000 records this used 64.8% of the wire guard, 72.3% of expanded
logical bytes and 64.5% of the node guard.

## Four-quarter state carry

Both 2026 chains completed under the same guards with verified cached
targets. The first published state closes the USD 250 opening advance
at zero. Each subsequent input contains the preceding public reload's exact
state key, quantity, boundary and prior result reference. Recoupment was
USD 250, 0, 0 and 0 at both sizes. The successful publications represent
calculations with unissued status and no payment event.

| Original records per close | Distinct originals over four quarters | Through-consumer times Q1 / Q2 / Q3 / Q4 (s) | Sum of four measured intervals (s) |
| ---: | ---: | ---: | ---: |
| 100 | 385 | 5.045 / 5.117 / 5.036 / 5.014 | 20.212 |
| 1,000 | 3,850 | 39.536 / 39.518 / 39.681 / 39.645 | 158.380 |

The sum excludes work between timed intervals. Each chain is a single
sequence of dependent observations. The 1,000-record chain reuses 50
funding records unchanged, with 950 fresh financial facts each quarter.

| Records per close | Neutral input (bytes) | Bound input (bytes) | Canonical result (bytes) | Compact wire (bytes) | Expanded logical audit (bytes) |
| ---: | ---: | ---: | ---: | ---: | ---: |
| 100 | 105,817–107,428 | 65,194–66,723 | 32,687–33,840 | 1,527,895–1,539,522 | 5,144,850–5,252,034 |
| 1,000 | 951,213–966,324 | 573,603–587,984 | 271,776–283,432 | 43,503,437–43,832,805 | 776,599,360–801,622,990 |

Nodes and edges stayed at 2,251 / 3,008 for 100 records and
64,480 / 88,010 for 1,000. The heaviest observed close used 65.3%
of the wire limit and 74.7% of the expanded logical limit.

| Records per close | Maximum coordinator peak working set (bytes) | Maximum runtime child peak working set (bytes) |
| ---: | ---: | ---: |
| 100 | 381,984,768 | 88,375,296 |
| 1,000 | 391,385,088 | 100,999,168 |

Working-set maxima cover repeated and chained observations. The coordinator
and each child have distinct process lifetimes. The maximum runtime child
observation used 37.6% of its 256 MiB guard. The observed compiler maximum
used 28.7% of its 1 GiB guard. All 16 observations completed, with zero
child timeouts, stdout overflows, or working-set guard failures.

## Evidence

Full evidence is external under `artifacts/spl/release-capacity-20261125-a/`.
`campaign.json` has SHA-256
`124f74355dac5f85a5631f6f1cffbe1afe0e751cc8f533fd50a1b0da9781e0d0`.
The source and build pins were unchanged after the run. The individual
publications, original inputs, oracle outputs and process reports are
retained there. Timing and hardware logs and the separate inspector are in
`artifacts/spl/release-capacity-build-20261125-a/`. The inspector confirmed
the committed markers and wire hashes, both public reloads for each result,
and exact successor state from each prior publication. Five one-second
host CPU samples ranged from 12.1% to 21.4% before the campaign and from
0.7% to 16.4% afterward. These are endpoint snapshots.

## Guards and workload limits

| Guard | Scope |
| --- | --- |
| 1 GiB and 180 seconds | Each compiler-only child process. |
| 256 MiB and 60 seconds | Each runtime, reference, audit reader or publication child. Windows working-set enforcement is sampled, with a final peak check. |
| 64 MiB | Bounded result or child stdout and compact trace wire limits in the measured workflow. |
| 1 GiB expanded graph | Compact native production and full reader limits. Compact encoding preserves the complete graph. |
| 100,000 graph nodes and 100,000 payloads | Separate native/reader observation and sharing limits. Compact records have an 8 MiB per-record limit and retained shared payloads have a 32 MiB aggregate limit. |
| 100,000 input originals and 100,000 typed collection items | Distinct admission limits for raw financial facts plus evidence and for individual decoded or projected collections. |
| 64 jobs, 64 MiB package aggregate, 8 MiB plan/resource metadata, 16 KiB resource keys | Separate conservative component planner. It accepts registered module profiles only, supports one worker, and has no approved legacy SV profile. |

Historical measurements preserve two different oversized outcomes:

- A 1,000-record v1 reconstruction exceeded its 64 MiB reconstruction guard
  (`RECONSTRUCTION_BYTE_LIMIT`). That dated attempt provided no canonical
  completion or successor state. See external evidence
  `performance-protocol-full-20261123-a/protocol/summary.json`.
- A 10,000-record legacy RR03 study reached `COMPACT_EXPANDED_BYTE_LIMIT` in
  native audit and `RESOURCE_LIMIT` in the reference evaluation, with no
  complete audit or successor. See external evidence
  `rr03-mixed-capacity-10000-20261123-a/capacity-verification.json`. This
  checkpoint includes no 10,000-record rerun.

An admission forecast with 60,000 receipt parents and 20% eight-way splits
gives 96,000 allocation rows and 144,000 projected receipt rows (48,000 direct
plus 96,000 split). That would exceed the stated receipt collection guard,
even before allowing for a byte, memory or earlier admission guard. This was
a count calculation. Capacity with larger or more uneven bundles, multiple
participants or independent pools, different source complexity, deep state
histories and distributed execution remains unmeasured. Graph size depends
on those workload dimensions. The reported timings are research measurements
on this host and profile.
