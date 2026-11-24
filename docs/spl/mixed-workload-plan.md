# Original-record mixed workload measurements

This experiment implements the first bounded mixture proposed by
[RR-03](rr03-response-integration.md). It generates neutral original records,
runs the independent [SV oracle](../../oracles/skouras.py) before projection,
then measures the existing canonical input boundary, emitted native calculation
and complete compact native audit separately. The existing SV source, schema,
oracle and original neutral fixture remain unchanged.

## Finite representation and counts

| Object kind | 100-record cohort / two titles | 1,000-record cohort / eight titles | Count treatment |
| --- | --- | --- | --- |
| Original cash receipt parents | 60 | 600 | Financial facts; each original cash amount counted once |
| Original incurred-cost facts | 30 | 300 | Financial facts, including explicit exclusions |
| Funding evidence events | 5 | 50 | Evidence events, with complete opening title/party snapshot |
| Invoice lineage parents | 5 | 50 | Actual financial facts linked by `parent_fact_id`; separate invoice amount space |
| Actual schema guard objects | 100 | 1,000 | Financial facts plus evidence events, before allocations |
| Canonical financial facts/source batch rows | 95 | 950 | Receipts + costs + invoice lineage |
| Allocated cash parent groups | 6 | 60 | Exactly 10% of receipt parents, two authorized targets each |
| Allocation rows | 12 | 120 | Separate from guard count; replace parent views rather than adding cash |
| Projected typed receipts | 66 | 660 | Unallocated parents + two views per allocated parent |
| Selected eligible cost views | 24 | 240 | Remaining 6/60 costs retain explicit excluded dispositions |

The lineage bracket is deliberately concrete: original invoice records with
actual child-cash links validated by both schema and independent oracle. Invoice
face values are neither receipts nor incurred deductions. This does not claim
that a generic lineage metadata row counts against the current financial-fact
guard. Assets, mappings, references, interpretation decisions and separate
allocation-authority records are reported independently from the 60/30/5/5 mix.

Every parent allocation has a distinct supplied synthetic decision with pinned
target/weight terms and a separate neutral authority record. Physical allocation
rows are checked against these authorities. All costs have explicit supplied
eligibility/branch choices and pinned terms. Opening funding totals are composed
from original source events: each title has distributor funding, odd-indexed
titles also have participant funding. The complete snapshot covers both parties
and every picture; known-zero participant funding is explicit under that snapshot.
Pool membership mappings, role scope, policy dates and original source identities
remain inspectable.

The generated source batch preserves row count and separate cash-receipt,
incurred-cost and invoice signed/absolute USD control totals. Its exact canonical
source bytes and digest are retained. Funding events and allocation records also
belong to the separately archived source-record snapshot; their record counts
are not smuggled into the financial batch count. Financial facts use the existing
supplied-full-snapshot availability assumption, without invented `observed_at`.

## Measured path and gates

`validation/mixed_workloads.py` uses only standard-library construction from
`cases/sv/neutral-oracle.json`. Reproducible seeds change physical ordering while
retaining original facts and declared policies. The harness records the exact
seed, bytes and source/build/executable dependency closure.

1. Construct original records and compute the independent oracle from those
   original records, before any compiler projection.
2. Bind canonical source dependencies, validate schema/authority/scope and
   recheck manifest hashes. Measure these stages separately.
3. Project receipts, selected costs and funding views; resolve state aliases and
   verify every projected identity/amount/selected-cost record, title funding
   view, original-fact disposition and source-to-target lineage join against the
   original records and independent controls. Invoice ancestry remains in the
   original graph and is joined through each projected cash ID.
4. Measure semantic hashing and Python reference evaluation. Persist independent
   full title/fee/cost/share/pool/opening/closing controls.
5. Require current native source emission to equal `Demos/SV.lean`; execute the
   prebuilt native emitted target and opt-in compact native audit in separate
   processes. Their timings include startup, I/O and decode. Pure-settlement-only
   timing is still future work.
6. Validate complete compact output with the separately timed bounded reader,
   including all nodes/references and completion, then compare its full financial
   head to the independent oracle. It never builds the expanded trace array.

Initial child budgets match the receipt probes: 60 seconds, 64 MiB stdout,
256 MiB sampled Windows peak working set. The reader has its own process budget.
Failed/partial audits and unexecuted readers remain explicit failures; emitted
target success alone does not pass the cohort. No default canonical finalization
envelope is issued by this stage experiment.

```powershell
python scripts/spl_mixed_benchmark.py --records 100 --output C:/Projects/Film_TV_participation_dynamic_DSL/artifacts/spl/mixed-100-new
python scripts/spl_mixed_benchmark.py --records 1000 --prerequisite C:/Projects/Film_TV_participation_dynamic_DSL/artifacts/spl/mixed-100-new/summary.json --output C:/Projects/Film_TV_participation_dynamic_DSL/artifacts/spl/mixed-1000-new
```

The second command requires a completed successful 100-record run with identical
seed, budgets and actual harness/oracle/fixture/kernel/executable pins. It rejects
stale, failed or partially audited prerequisites before running native work. Keep
these dependencies stable during both measurements; unrelated new method files
are outside the selected dependency inventory. The harness never rebuilds native
executables during a measurement and requires a fresh destination.

These mixes are synthetic development distributions, one shared pool and one
calendar quarter. They do not establish industry representativeness, warm/cold
tail latency, million-row capacity, parallelism or distributed transaction safety.

## First executed mixed cohorts

On 23 November 2026, `rr03-mixed-100-20261123-a` passed all selected stages with
unchanged source/build/executable pins and unchanged original neutral records.
The source batch controls are USD6,174 cash, USD60 incurred cost and USD760
invoice face, in separate amount spaces. Independent earned entitlement is
USD1,590.664; pooled advance recovery is USD250, payable USD1,340.664 and closing
prepayment zero. No actually-paid amount is inferred.

The completed 100-record compact audit has 2,251 nodes/3,008 edges, representing
5,144,850 logical expanded trace bytes. Native wire output is 2,777,601 bytes.
The independent reader verifies every node/reference/completion with logical
trace SHA-256
`a9eff03a67af4a340167b440f1ad269a05ff94a03cde3b40605a4d207b3fff32`.
All 95 original fact dispositions, 90 projected receipt/cost lineage joins and
five actual cash-to-invoice parent links pass their independent controls.

That completed report admitted the 1,000-record cohort under matching pins,
seed and budgets. Its original-fact oracle, canonical binding/validation,
projection, manifest/semantic hashing, Python reference and native emitted target
all passed. The required compact audit exceeded the 64 MiB wire limit; its reader
was explicitly not executed and the cohort correctly failed. The raw input has
950 financial facts/50 funding events, including 50 invoice parents. Its selected
views are 660 receipts and 240 costs, with 60 excluded costs still accounted for.

| Measured stage | 100 originals / 2 titles | 1,000 originals / 8 titles |
| --- | --- | --- |
| Original-fact oracle, traced Python allocations | 0.007760 s | 0.069909 s |
| Canonical binding/dependency hashes | 0.020915 s | 0.059114 s |
| Schema/authority/scope validation | 0.023381 s | 0.212681 s |
| Manifest hash recheck | 0.014899 s | 0.051594 s |
| Canonical projection | 0.001524 s | 0.015719 s |
| Independent projection controls | 0.005018 s | 0.049062 s |
| Semantic hashing | 0.022404 s | 0.208862 s |
| Python reference evaluation | 0.055474 s | 1.387586 s |
| Emitted native process | 0.046449 s / 32,358,400 B peak | 0.051583 s / 33,722,368 B peak |
| Compact native audit process | 0.115031 s / 35,938,304 B peak | Failed wire budget after 16.173148 s / 99,524,608 B peak |
| Independent compact reader | 0.336886 s / 21,065,728 B peak | Not executed: incomplete native audit |

These are single samples with the stated measurement scopes, not pure-kernel or
production tail-latency measurements. The failed 1,000 audit retained exactly
67,108,864 bytes, without a valid completion; it was not expanded or credited as
audited support. Native memory and timeout budgets were not exceeded. This is a
workload-dependent output limit even though the earlier receipt-only 1,000-row
compact probe completed successfully.

Both artifact directories are under the external SPL artifacts root. Their
source archives preserve the dated pre-LG-allocation-fix compiler/reference
identity `1ec2ca5ec6df9ae844348d9fe5961c58ecb3dab614b0e01cfdea741ace93a20a`.
Later compiler/reference fixes must not silently rewrite these observations or
reuse them as matching-pin prerequisites for a changed harness/dependency set.
The eight focused mixed-workload tests passed in 0.090 seconds for that interval.

## Next measured transport candidate

Read-only sizing of the failed audit's complete-record prefix found 54,213 node
records and 4,674 payload definitions in 67,107,734 bytes before the truncated
last record. Dependency arrays contain 15,194,995 bytes of prior node-ID strings;
substituting already-topological integer indices estimates 443,307 bytes for
those array values alone. Every original node ID would still be retained and
reconstructed exactly. This estimate excludes wrapper/version overhead and is
neither a full-trace size result nor completed-audit validation.

The same prefix leaves repeated eligible metadata below the current 256-byte
interning threshold inline: instance scope 6,662,306 bytes, value type 2,778,162
and source span 2,468,372. A separate explicit transport version could combine
dependency-index wrappers with measured lower-threshold metadata interning.
Keep the existing compact format/decoder unchanged, validate exact reconstruction
and bounds independently, and benchmark only within a new stable source interval.

## Executed indexed v0.2 continuation

That candidate is now implemented as a separate `--compact-v2` driver mode and
`--transport compact-v2` mixed-harness selection. Compact v0.1 remains available.
V0.2 transmits dependencies as validated indices into earlier exact original
node IDs and lowers eligible-field interning to 32 bytes. Logical source IDs,
dependency order, complete node contents and outcome head remain unchanged.
The reader rejects cross-version dependency representations and retains the same
strict completion/resource rules. Native build and 31 combined focused methods
passed before these measurements.

```powershell
python scripts/spl_mixed_benchmark.py --records 100 --transport compact-v2 --output C:/Projects/Film_TV_participation_dynamic_DSL/artifacts/spl/mixed-v2-100-new
python scripts/spl_mixed_benchmark.py --records 1000 --transport compact-v2 --prerequisite C:/Projects/Film_TV_participation_dynamic_DSL/artifacts/spl/mixed-v2-100-new/summary.json --output C:/Projects/Film_TV_participation_dynamic_DSL/artifacts/spl/mixed-v2-1000-new
```

The fresh post-LG-fix `rr03-mixed-v2-100-20261123-a` report passed and admitted
the matching `rr03-mixed-v2-1000-20261123-a` run. Both pass all independent original
fact/projection/target/audit/reader controls with unchanged source and executable
pins. All original counts in the table above remain the same. The budgets also
remain 64 MiB wire, 256 MiB sampled native/reader working set and 1 GiB logical
expanded trace; no separately enlarged profile was used.

At 100 records, v0.2 transmits 1,527,895 bytes for the same 2,251 nodes/3,008
edges and 5,144,850 expanded bytes. Its logical trace digest exactly matches
the earlier complete v0.1 100-record result. The current source interval has
compiler/reference identity
`1370523431c8fa7d13e0c424e1547e4885528f764b88b0c256490fa6d874c029`,
so the earlier pre-fix build pins remain dated evidence rather than new
matching-prerequisite records.

At 1,000 records/eight titles, complete v0.2 wire output is 43,503,437 bytes,
representing 64,480 nodes/88,010 edges and 776,599,360 logical expanded bytes.
Native audit takes 16.291806 seconds at 100,597,760 bytes peak working set; the
separately bounded reader takes 5.370774 seconds at 73,129,984 bytes peak. It
validates every reconstructed node without retaining an expanded node array.
The canonical logical trace digest is
`2e22fd77147b96d987c36839796cdf3125171cbdf5d9daaa479a1b2a4100070b`.
The emitted target takes 0.052341 seconds at 33,710,080 bytes peak; the whole
experiment takes 24.370983 seconds. Financial agreement includes every title's
cash/fee/cost/basis/share/earned values and pooled opening/recovery/payable/closing,
with all source allocations, decisions and dispositions independently controlled.

This closes the observed wire failure for one disclosed 1,000-record mixed
cohort while preserving the earlier failure history. It is not a p95 service
claim, production workload distribution or general capacity boundary. Audit CPU
and complete-pipeline latency remain material next work; repeated expanded-value
serialization and internal phase attribution still need measurement.

## Same-wire byte-accounting continuation

The subsequent driver caches each logical field's compressed string and derives
exact expanded object size from braces, separators, quoted keys and value bytes,
eliminating a redundant compression of the entire node. The expanded guard still
executes before payload/node output. No transport shape, logical node, dependency,
money value or budget changes. Thirty-one focused methods pass, with expanded
byte metadata compared directly against raw legacy native trace-array bytes.

Fresh `rr03-mixed-once-100-20261123-a` and its matching
`rr03-mixed-once-1000-20261123-a` both pass all stages under unchanged budgets and
the same stable post-LG kernel identities. Exact chunkwise comparison to the
preceding v0.2 experiments confirms identical complete source, bindings and wire.
Only the standalone driver source/executable pins differ. Comparison evidence is
retained separately in `rr03-mixed-once-equivalence-20261123-a/comparison.json`.

The 1,000-original native audit observation is 14.558170 seconds, versus the
preceding 16.291806. Independent reader time is 5.373187 seconds; whole-experiment
time is 22.671430 seconds, versus 24.370983. Native/reader peak working sets are
99,577,856 / 73,510,912 bytes. The wire is still exactly 43,503,437 bytes and
reconstructs the same 776,599,360 bytes across 64,480 nodes/88,010 edges. Financial
controls, dispositions and original source counts all remain identical.

These single observations demonstrate the selected change's bounded behavior;
they do not establish a latency percentile or the proposed RR-03 15-second target.
Remaining audit CPU needs internal phase instrumentation and repeat measurements.

## Opt-in internal audit profile

`spl_trace_stream --profile-stages` emits one `spl-native-audit-profile/1`
JSON object on stderr after completion, outside the unchanged stdout transport.
The same flag is accepted by the mixed harness. A profiled mixed run first runs
an unprofiled audit on exactly the same source/bindings, then requires bytewise
equivalence through matching complete-wire SHA256, validates every reconstructed
node with the bounded reader and checks complete independent financial controls.
`--wire-reference PATH` additionally requires equality with an archived prior
wire. A matching successful profiled 100-record prerequisite remains required
before the 1,000-record run. All existing resource limits remain unchanged.

Named monotonic intervals cover source/manifest reads, parse/link/check,
elaboration/IR validation, binding read/decode, interpreter execution, driver
graph validation/order, outcome head and per-node JSON conversion, field encoding
and expanded-byte accounting, dependency lookup, sharing, record compression,
stdout writes/flush and the whole transport. The strict reader of the timing
side channel checks expected stage/call counts against actual node/payload
counts, monotonic nonnegative integral spans and parent bounds. Missing timings
or incomplete audit output cannot receive successful profiling credit.

The public interpreter already includes IR validation and internal graph
validation/order. Its `interpreter_graph` interval is inclusive of those costs;
driver `graph_validate` and `graph_order` are subsequent passes. The profile
does not split the interpreter's internal calculation from its internal checks.
`transport_total` includes all driver transport work. The
`sharing_and_payload_records` interval also includes first-use payload record
compression/writes; these overlap the aggregate record/write intervals. Parent
and child intervals must never be added together. Remaining wrapper/object
construction, reference updates and clock bookkeeping appear within inclusive
parent clocks or unassigned runtime, rather than being silently allocated to
one measured child.

Pure work runs through a noinline IO boundary so argument preparation does not
eagerly precede the clock. Each stage reports total nanoseconds and call count.
The profile also reports the number of clock pairs and a separate 1,000-pair
empty-clock probe. The probe excludes real map updates/closures/cache effects
and is never used for overhead subtraction. Paired whole-process observations
show instrumentation perturbation under uncontrolled cache/scheduling state;
they are neither a correction nor a controlled causal estimate. Stdout timings
measure acceptance by Lean's stream and the OS pipe, including any backpressure,
not durable disk completion. Process CPU/memory retain their whole-child scope.
Default commands emit no timing stderr and preserve exact logical/wire semantics.

### Initial internal observations (2026-11-23)

Fresh `rr03-mixed-profile-100-20261123-a` and its matching
`rr03-mixed-profile-1000-20261123-a` both pass with unchanged dependency pins.
Thirty-three focused trace/mixed/stage test methods pass. Direct chunkwise file
comparison confirms identical complete source, typed bindings, source-batch
records and original source records against the preceding `rr03-mixed-once-*`
experiments. Both profiled and unprofiled wires are exactly identical to those
prior complete wires. Native generated C and boundary inspection evidence are
archived under the 1,000-record result's `native-boundaries/` directory.

| Internal monotonic interval | 100 originals | 1,000 originals |
| --- | --- | --- |
| Interpreter, including its internal validation/order | 0.006976 s | 5.003032 s |
| Whole driver transport (inclusive parent) | 0.041171 s | 9.458454 s |
| Node-to-JSON conversion | 0.008180 s | 6.637718 s |
| Field encoding and expanded-byte accounting | 0.017247 s | 1.993644 s |
| Subsequent driver graph validation | 0.001736 s | 0.102916 s |
| Subsequent driver graph ordering | 0.001265 s | 0.071613 s |
| All compact record compression | 0.005659 s | 0.162647 s |
| All stdout writes | 0.001369 s | 0.043279 s |
| Sharing plus first-use payload records (overlaps compression/writes) | 0.004779 s | 0.377807 s |

The 1,000-record unprofiled child takes 14.483345 s wall / 14.203125 s CPU at
96,051,200 bytes peak working set. Its paired profiled child takes 14.508533 s /
14.359375 s CPU at 97,501,184 bytes peak. The observed wall difference is
25.188 ms; the 100-record instrumented process is instead 5.750 ms faster than
its pair. Scheduling/cache differences prevent attributing these differences
entirely to instrumentation. At 1,000 records, 486,796 stage clock pairs are
recorded; the separate 1,000-pair empty probe takes 41 microseconds, without
map-update/closure costs. No correction is applied.

The separate bounded reader takes 5.373038 s at 72,998,912 bytes peak. The paired
whole experiment takes 37.114415 s because it deliberately runs two full audits.
This is not a new single-audit latency result. All 64,480 nodes / 88,010 edges,
17,708 payloads, 43,503,437 wire bytes and 776,599,360 expanded trace bytes remain
unchanged. Wire SHA256 remains
`493ca744ac73185ba238e7ed65a3e9f9e3e7a8e9987509d19596a22ca71c83e6`;
logical trace SHA256 remains
`2e22fd77147b96d987c36839796cdf3125171cbdf5d9daaa479a1b2a4100070b`.

The next narrow candidate is fact-ID collection/deduplication inside
`Trace.nodeJson`: recursive collection currently constructs repeated lists and
then applies `List.eraseDups` before lexical sorting. A hash-set collector with
the same explicit final lexical ordering could preserve all logical JSON while
reducing repeated work. This is a measured-stage-driven candidate, not yet an
attribution of the entire node-JSON interval to deduplication. It requires old/new
full-node equivalence, nested/duplicate/Unicode identity checks and unchanged
complete-wire controls before performance credit. Stdout changes are a much
smaller candidate in this observation. Financial semantics remain outside the
proposed transport optimization.

### Fact-ID collector candidate

The approved candidate replaces only `Trace.nodeJson`'s fact-ID collector. It
threads one exact `Std.HashSet String` through every record field and nested
sequence/tuple/map/option value, across operands and the optional result, then
uses the same explicit lexical `mergeSort` for the final identities. No fact-ID
spelling is shortened or normalized, and non-text `fact_id` values retain their
previous behavior. All other node fields, graph decisions/dependencies,
financial calculations, compact protocols and resource limits remain unchanged.

The frozen legacy full formatter in the focused Python test creates 560 direct
`Value`/`Node` combinations across nested duplicate and empty identities,
Unicode/control strings, every value constructor, optional results, operand
permutations and evaluated/failed/skipped/discarded/passed statuses. It compares
both full parsed JSON and exact compressed JSON, with an independent explicit
nested identity expectation. Temporary `lean --run` source emits no persistent
`.olean`, avoiding the stale native symbol issue from direct module rebuilding.
The fixture passed against the archived pre-change implementation before the
collector source changed.

Archived old source/driver/executables are under external
`artifacts/spl/trace-factid-baseline-20261123-a/`. The candidate changes the
compiler/reference fingerprint to
`654c5a91f8e16975e77f473943caff362e117949e8f232767c25edf6ced3bbba`;
runtime remains `673bb0fe936c48a60c1cf5a1a265fb1d1f9f3cd432f380ee9b3011b7729dace9`.
Earlier benchmark source pins remain separate dated evidence. Performance credit
requires a rebuilt target, focused checks, a fresh matching 100-record gate and
1,000-record complete-wire/financial controls.

The rebuilt candidate passes all 34 focused methods in 6.263 s, including the
560 complete legacy formatter comparisons. Fresh matching
`rr03-mixed-factids-100-20261123-a` and
`rr03-mixed-factids-1000-20261123-a` both pass every original-fact, projection,
complete financial output, all-node reader, exact prior wire and paired
profile/unprofiled wire control with unchanged source/executable pins. Exact
input/source comparisons, before/after observations, frozen test source and
generated C are retained in the latter result's `collector-comparison/` folder.
Module fingerprint is now
`d73920c18ffd5c5d47c0bc45871b300ab67fe92bf1ce9f0c6a01aa482d6013a4`.

| 1,000-record observation | Before collector change | After collector change |
| --- | --- | --- |
| Unprofiled native audit wall / CPU | 14.483345 / 14.203125 s | 9.269901 / 9.203125 s |
| Profiled native audit wall / CPU | 14.508533 / 14.359375 s | 9.371586 / 9.265625 s |
| Node JSON interval | 6.637718 s | 1.392800 s |
| Whole transport interval (inclusive) | 9.458454 s | 4.267114 s |
| Interpreter interval (inclusive) | 5.003032 s | 5.060296 s |
| Field encoding/accounting interval | 1.993644 s | 2.026554 s |
| Unprofiled / profiled child peak working set | 96,051,200 / 97,501,184 bytes | 96,137,216 / 100,757,504 bytes |
| Separate reader wall / peak working set | 5.373038 s / 72,998,912 bytes | 5.245720 s / 73,121,792 bytes |

The unchanged complete wire and logical trace hashes above still cover all
64,480 nodes, 88,010 edges and 776,599,360 expanded bytes. No trace reduction or
budget enlargement contributes to this observation. The small 100-record
unprofiled audit changes from 0.091959 s to 0.090609 s, while its node JSON
interval changes from 8.180 ms to 6.284 ms; these single small observations show
no measured regression but do not establish a general latency distribution.

The instrumented 1,000-record pair is 101.685 ms slower than its unprofiled pair;
486,796 clock pairs remain, with a separate 41.2-microsecond empty-clock probe.
The paired experiment takes 26.660926 s in total because it runs two audits.
These scopes and uncontrolled scheduling/cache effects remain explicit. The
result isolates a material improvement in the selected node-JSON stage without
claiming a production percentile, a whole-pipeline 15-second result or complete
performance acceptance. Interpreter construction and repeated field encoding
remain measured next candidates; changing them requires another scoped review.

## Bounded 10,000-original probe

The next finite generator branch contains exactly 6,000 cash parents, 3,000 cost
facts, 500 funding events and 500 invoice lineage facts across 40 pictures.
Financial facts number 9,500; canonical facts-plus-events guard objects number
10,000. Six hundred cash parents each have four separately authorized exact
allocation weights 0.1/0.2/0.3/0.4: 2,400 physical allocation rows produce 7,800
projected receipts. Explicit cost choices select 2,400 views and exclude 600.
Invoice face values remain a separate amount space. Metadata, mappings,
interpretation decisions and independent allocation authorities are counted
separately. Existing 100/1,000 generator canonical bytes remain unchanged, with
frozen whole-workload SHA256 regression checks.

Before a 10,000-record native probe, the same source/executable/budget/profile
interval must pass fresh 100 and then 1,000 gates. The 10,000 gate requires that
matching completed 1,000 report. Initial repetitions are fixed to one. Guards
remain 64 MiB wire, 256 MiB sampled child working set, 1 GiB expanded trace and
the kernel's 100,000-observation limit; no enlarged profile is selected silently.

The original-fact independent oracle runs before canonical projection and full
title/pool/closing controls remain mandatory for the compiled financial target.
The potentially large Python reference trace is evaluated in a separately
bounded child at 10,000 records. Its summary serializes financial fields,
diagnostics and observed trace count rather than expanding that trace again.
Resource/process failures stay explicit and cannot prevent the later target
financial checks. They receive no reference-completion credit. Native target
execution precedes the required audit, including a paired unprofiled audit when
profiling is explicitly enabled.

Parent preparation remains finite generation/oracle/binding/schema/projection
work with measured Python traced peaks and a 64 MiB original-input byte guard.
That guard is checked after serialization; neither it nor per-operation traced
peaks enforce an overall 256 MiB parent-memory limit. Child working-set budgets
exclude the parent, retained inputs and filesystem cache. No whole-process
memory claim is inferred from the child's limit.

An incomplete audit never supplies audited financial outputs or closing state.
A bounded first-header observation may show the interpreter's blocked diagnostic
and empty outputs even when transport later fails, but grants no completed-node
or state credit. Four/eight-close dependency plans mark successor closes
`not_executed` after an incomplete first close. A first-close success also does
not imply later closes ran: each needs separately executed original facts and
actual serialized audited predecessor state. This first probe executes one
close; it is not a four/eight-period capacity claim. Fifteen focused Python
methods currently pass, including 10,000 original-fact/projection controls,
strict scale gates, reference-summary failure handling and prefix/state guards.
Those draft checks alone supply no native timing or capacity evidence. The
following observation is a failed bounded close, not successful capacity.

### Current-pin gate and first failure (2026-11-23)

After publication integration, fresh
`rr03-mixed-capacity-100-20261123-a` and
`rr03-mixed-capacity-1000-20261123-a` pass all stages with exact prior complete
wire bytes and unchanged source/executable pins. Compiler/reference is
`323f0d844fe11344713523f40d83d3b67d32d1376ce89da823875d72c2a297bc`,
module is `7a2f98f64b70cb67e5b95ecdbb0fec85536d1cce3fb9423f1dfd42c9ed1772eb`,
and runtime remains `673bb0fe936c48a60c1cf5a1a265fb1d1f9f3cd432f380ee9b3011b7729dace9`.
The nonprofiled 1,000-record audit takes 9.262570 s at 96,182,272 bytes peak;
its separate reader takes 5.327790 s at 73,412,608 bytes. The 100-record audit
takes 0.084873 s. These are single observations under the unchanged budgets.

The one admitted `rr03-mixed-capacity-10000-20261123-a` probe **fails** with all
original records and dependency pins unchanged. No retry or larger guard was
used. Complete independent original-fact and projection controls pass first.

| 10,000-original stage | Actual status | Wall / CPU | Whole-child peak working set |
| --- | --- | --- | --- |
| Bounded Python reference | Returned blocked `RESOURCE_LIMIT` at exactly 100,000 observed reference nodes; worker exited normally | 0.596315 / 0.578125 s | 81,166,336 bytes |
| Compiled financial target | Passed complete 40-title, pool and closing controls | 0.241125 / 0.265625 s | 47,067,136 bytes |
| Required native audit | Header reports blocked `RESOURCE_LIMIT`; compact serialization then exits 1 with `COMPACT_EXPANDED_BYTE_LIMIT` | 17.813114 / 17.500000 s | 138,276,864 bytes |
| Complete audit reader | `not_executed`: native audit did not complete | No timing credit | No memory claim |
| Successor closes in 4/8-period plans | `not_executed`: audited predecessor incomplete | No timing credit | No state supplied |

The target's component observation agrees on earned 159,239.022, recovered 250,
payable 158,989.022 and closing advance zero, including every title intermediate.
This does not make those amounts issued or audited: the benchmark's
`audited_financial_outputs` is empty and `audited_closing_state` is empty.
The native header also contains empty emissions/closing. Its prefix grants no
trace completion credit. Only 3,808,802 partial wire bytes are retained; there
is no complete node/edge count or full logical-trace digest for this failure.
The native `RESOURCE_LIMIT` header must not be confused with the subsequently
observed 1 GiB expanded-serialization guard. No timeout, 64 MiB wire overflow or
256 MiB child-memory breach occurred. The reference's verified 100,000-node
count is a separate observation from the incomplete native transport.

Original neutral bytes are 10,511,233; canonical package 9,348,018; bindings
2,461,462; source financial batch 3,800,301; original financial/event/allocation
records 5,141,657. Parent preparation observations are 0.876963 s generation,
0.832029 s original-fact oracle, 0.507822 s binding/hash, 2.424870 s schema,
0.488496 s manifest recheck, 0.201855 s projection, 0.711532 s independent
projection controls and 2.427512 s semantic hash. The largest individual traced
Python peak is 40,244,780 bytes during semantic hashing. These are per-stage
allocation measurements, not a bound on retained parent objects or process RSS.
Whole experiment elapsed time is 28.483478 s; it is not a successful close/SLA.

This establishes an observed failed first-close boundary for this disclosed
10,000-record/40-title/four-way allocation mix. It establishes neither a maximum
supported raw count nor a production distribution, p95, successful 4/8-close
chain, raw 100,000-object boundary or high-fanout capacity. A next optimization
or separately named resource profile needs its own review and evidence.
