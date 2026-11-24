# SPL measured performance work

The initial stage harness measures receipt-only development probes separately
from the mixed workload proposed by [RR-03](rr03-response-integration.md). It
does not establish production capacity or the research's proposed service targets.

Run the pinned build and the harness sequentially, with a new external destination:

```powershell
lake build spl spl_sv
python scripts/spl_stage_benchmark.py --rows 0 10 100 --pictures 2 --repeats 3 --output C:/Projects/Film_TV_participation_dynamic_DSL/artifacts/spl/stage-benchmark-new
```

The harness never rebuilds a binary during measurement. Keep compiler/runtime
sources, its two scripts, the input schedule and native executables stable. Its
source snapshots and beginning/end hashes identify the measured inputs; the
build precondition establishes their intended correspondence. It also requires
the current native frontend's emitted source to match `Demos/SV.lean` exactly
before crediting execution of `spl_sv` as the selected emitted program.

| Stage | Measured scope |
| --- | --- |
| Native frontend check | Process startup, source read, parse/check/elaborate/defensive IR validation and small JSON report |
| Native source emission | Frontend plus Lean source generation and file write |
| Python frontend | Python parse and static check, separately from evaluation |
| Python reference | Evaluation and result encoding; Python allocation peak from `tracemalloc` |
| Native emitted target | Prebuilt `spl_sv` process startup, binding I/O and strict decode, settlement and result JSON serialization |
| Native IR audit | Prebuilt `spl interpret` startup, frontend, binding decode, interpreter calculation, audit DAG construction/order and JSON serialization |

Pure-settlement-only and trace-generation-only timing are not instrumented.
Windows child CPU and peak working set are measured through the process APIs;
the report explicitly marks unsupported memory measurements unavailable. Child
working set excludes the parent that subsequently decodes JSON. Python allocation
peaks are a different quantity and must not be compared as process-memory peaks.

All stages retain commands, stdout/stderr bytes, exit status, elapsed time and
budgets. Each cohort retains exact source/binding bytes, an independent expected
result, result comparisons, executable/build hashes and trace node/edge counts.
The initial workload has zero costs, funding and allocation records. Original
receipt parents and projected typed receipts are counted separately, although
they coincide in this adapter-free fixture. It is not a canonical guard test.

The independent control checks every title's cash, fee, allowed cost, basis,
share and earnings, then the pool scope/period, earned/recovered/payable values
and zero closing advance. It operates from neutral receipt facts and rejects
facts outside the stated unit-dollar, unfunded, in-period domain.

Default native output is bounded to 64 MiB per stdout stream, stderr to 1 MiB,
each child to 60 seconds, and Windows child peak working set to a sampled
256 MiB budget. Working set is checked at 20 ms intervals; this permits transient
overshoot and is not a hard operating-system memory limit. Unsupported platforms
explicitly record memory-budget enforcement unavailable. Overflow, memory-budget
failure and timeout preserve bounded evidence
and fail the stage. Audits are required for every cohort/sample; an unexecuted
or resource-limited audit cannot be credited as a successful audited measurement.
The initial cohort limit is 100 receipts and eight pictures. Increasing it is a
new resource experiment, not an automatic capacity upgrade. First and repeated
process samples are recorded individually; three samples do not establish a
tail-latency percentile or a controlled cold-cache experiment.

The explicit Windows-only `--stress` switch admits up to 1,000 receipts while
retaining the same default byte/time/memory budgets. For example, a 1,000-receipt
target success and an audit memory-budget failure are two separate observations;
the cohort remains failed and cannot establish 1,000-row audited support.

## First bounded stage evidence

The immutable external `stage-benchmark-20261123-a/summary.json` records the
first 0/10/100 cohort, three emitted-target and three complete native-audit
samples each. All passed their independent controls and beginning/end pins.
Its archived harness predates the additional sampled working-set enforcement.

| Receipt rows | Binding bytes | Target median seconds | Audit median seconds | Audit stdout bytes | Audit nodes/edges | Audit child peak working set, observed range |
| --- | --- | --- | --- | --- | --- | --- |
| 0 | 661 | 0.036314 | 0.038351 | 164,189 | 180/216 | 34,254,848–34,287,616 bytes |
| 10 | 2,955 | 0.035725 | 0.042893 | 523,412 | 410/526 | 35,774,464–35,803,136 bytes |
| 100 | 23,565 | 0.036038 | 0.097579 | 7,606,086 | 2,480/3,316 | 70,000,640–70,078,464 bytes |

The 100-row emitted result is 1,034 bytes and its process peak is approximately
32.4 MB. Direct field analysis of the first 100-row audit finds 3,677,600 compact
JSON bytes in `instance` operands. All operand/result values total 4,268,565
compact bytes, versus 145,353 bytes across unique values in those fields. These
are payload observations, not an attribution of wall time to a specific function.

The narrow optimization candidate is preserving collection observations once
internally and streaming their expanded public JSON where required. Keep the
existing logical trace byte/value semantics and lineage, then compare exact
expanded traces and independent business outputs. Do not select graph sorting
as the measured bottleneck from these size observations. Current archival
interning remains useful storage evidence but operates after the native
materialization and therefore cannot reduce its peak working set.

The subsequent immutable `stage-benchmark-20261123-stress-a` run used one sample
each at 100/300/600/1,000 rows with the sampled 256 MiB child budget and 64 MiB
stdout limit. The 100-row audit passed. All emitted targets passed, including
1,000 rows in 0.044881 seconds with 33,873,920 bytes peak working set. Audits at
300, 600 and 1,000 rows failed the working-set budget before any stdout, at
observed peaks 279,924,736 / 274,386,944 / 269,094,912 bytes. The first observed
audit failure therefore lies between the tested 100 and 300 cohorts; this is
not an exact capacity boundary. Source/build/binary pins remained unchanged.

`Demos/TraceStream.lean` is the separate transport experiment, executable
`spl_trace_stream`. It uses the existing native frontend components, strict
binding decoder and interpreter, then retains the validated whole logical graph
while serializing each existing `Trace.nodeJson` in dependency order. Outcome
head fields come from the existing `Interpret.outcomeJson` applied to the same
result with an empty graph. This avoids materializing the entire JSON node array
and compressed outcome string, while retaining every expanded node and value.
It changes no kernel source or default canonical runner. Use
`--audit-driver stream` for the identical benchmark cohorts and budgets after
`lake build spl_trace_stream`. Node-by-node output is not atomic publication;
consumers must reject interrupted/truncated JSON and retain completion checks.

The immutable `stage-benchmark-20261123-stream-a` run uses that separate driver,
one sample per cohort and the same 64 MiB stdout/256 MiB sampled working-set
budgets. Complete audits pass at 0, 10, 100 and 300 rows. The 100-row audit writes
the same 7,606,086 output bytes, with 36,048,896 bytes child peak working set;
its complete parsed outcome equals the first legacy 100-row outcome, including
all 2,480 ordered nodes and 3,316 dependency edges. Raw object key order differs.
The independently retained comparison is
`trace-stream-equivalence-20261123/comparison.json` under the external SPL artifacts
root, with canonical whole-outcome SHA-256
`14d529ad615832c1c158cbd14920937f816294d1bde2528e408fca10d046362e`.

At 300 rows the stream audit completes in 0.541265 seconds, writes 48,140,010
bytes and retains 7,080 nodes/9,516 edges at 41,844,736 bytes child peak working
set. Legacy 300 failed the lower 256 MiB sampled memory budget; no completed
legacy 300 comparison was performed in this experiment. At 600 and 1,000 rows,
stream audits fail the 64 MiB stdout budget, with child peaks 51,441,664 and
59,293,696 bytes respectively. Each retained stdout is exactly 67,108,864 bytes;
both are incomplete, deliberately unparsed and uncredited as complete audits.
All target calculations pass and all source/build/binary pins remain unchanged.

This provides bounded evidence that node-by-node JSON output removes much of
the measured native materialization peak. It does not solve repeated expanded
collection payloads, establish complete 1,000-row audited support or measure
production latency. The next failure among the tested stream cohorts is output
volume between 300 and 600 rows. A compact transport plus a bounded streaming
consumer is now the appropriate next experiment; preserve exact reconstruction
and the default financial/audit authority boundaries.

## Native compact streaming experiment

The opt-in `--compact` flag on `spl_trace_stream` now implements that transport
experiment. Existing legacy/native and expanded streaming commands retain their
behavior. The versioned `spl-native-trace-stream/0.1` format is JSON Lines with
one header, payload definitions before use, ordered node wrappers and one final
completion record. The header retains every original outcome field except the
trace array, including the unchanged `spl-trace-dag/0.1` logical trace format.

Payload and node wrappers reuse the archival transport's opaque `inline`/`shared`
field convention and eligible field names. Payload IDs are consecutive first-use
IDs, interned by equality of the exact native JSON string. The native driver
therefore does not depend on cryptographic hash equality to decide sharing.
It serializes shareable fields of at least 256 bytes once. The new JSONL format
is deliberately distinct from the existing archival envelope and decoder.

Native limits are 100,000 nodes, 100,000 payloads, 32 MiB of unique serialized
payload strings, 8 MiB per record and 1 GiB of logical expanded trace bytes.
The surrounding harness retains its smaller 64 MiB wire-output/256 MiB sampled
child-memory/60 second process budgets. Interrupted output has no valid completion
and is rejected. Final counts and expanded native byte size are validated by
`scripts/spl_native_trace_transport.py`, which also checks closed records,
payload identity/use/order, every node/dependency/detail reference, strict JSON,
depth and all declared reader budgets.

The independent reader retains unique immutable payload objects/canonical bytes
and observed node IDs. It hashes each reconstructed canonical node from cached
field bytes, without an expanded trace array. Explicit mutable reconstruction
deep-copies payloads and has a separate default 64 MiB expansion limit. The
benchmark uses a separately measured, resource-bounded reader process; its peak
working set includes Python startup, wire parsing and complete validation.
Native execution and reader time/memory are reported separately. The format has
no embedded cryptographic checksum: whole-file SHA-256 and canonical logical
trace SHA-256 are recorded evidence, and an externally supplied file hash can be
required by the reader. They do not establish custody or authenticity.

Lean 4.35's JSON printer and Python's canonical JSON use different escape lengths
for tab/backspace/formfeed. The reader verifies native expanded-byte metadata
while computing a separate stable canonical logical digest; the control-character
roundtrip test exercises this distinction. Literal user values containing
reference-like words/keys remain opaque.

```powershell
lake build spl_trace_stream
python scripts/spl_stage_benchmark.py --rows 0 10 100 300 600 1000 --repeats 1 --stress --audit-driver compact --output C:/Projects/Film_TV_participation_dynamic_DSL/artifacts/spl/stage-benchmark-compact-new
```

All six cohorts in immutable `stage-benchmark-20261123-compact-a` passed their
independent title/intermediate/pool/scope/state controls, complete reader
validation and unchanged source/build/executable pins. There was one sample per
cohort; none of these numbers is a percentile or production-capacity commitment.

| Receipts | Compact wire bytes | Logical expanded trace bytes | Native audit seconds / peak working set | Independent reader seconds / peak working set | Nodes |
| --- | --- | --- | --- | --- | --- |
| 0 | 152,543 | 163,082 | 0.039881 / 33,390,592 B | 0.083559 / 19,521,536 B | 180 |
| 10 | 452,051 | 522,303 | 0.045906 / 33,759,232 B | 0.113296 / 19,812,352 B | 410 |
| 100 | 3,068,740 | 7,604,969 | 0.127942 / 36,519,936 B | 0.359493 / 21,098,496 B | 2,480 |
| 300 | 8,899,417 | 48,138,889 | 0.665022 / 43,765,760 B | 0.929978 / 24,711,168 B | 7,080 |
| 600 | 17,645,319 | 173,064,589 | 2.997283 / 51,798,016 B | 1.798176 / 29,233,152 B | 13,980 |
| 1,000 | 29,308,694 | 459,332,275 | 10.392801 / 59,678,720 B | 2.958972 / 37,199,872 B | 23,180 |

The 1,000-row emitted target separately passes in 0.049859 seconds. Its audit
retains every logical node through 1,037 unique payloads. The reader validates
all of them without expanding the 459 MB logical trace. The 100-row canonical
trace digest independently matches the complete recorded legacy outcome:
`7230315c96555d2ff81b38edf0de0e8fd5dd64c515642fe4f562e56c5485246b`.
All raw financial head fields also match. The separate comparison is retained
as `trace-native-compact-equivalence-20261123/comparison.json`. Focused tests
compare full legacy/expanded-stream/compact outcomes on bounded success, failure,
skip, discarded-output, readable and imported-library cases.

This is bounded receipt-only transport evidence. The new mode remains an
explicit experimental CLI path and is not the default canonical runner or a
proof of trace equivalence. Native interning still repeatedly serializes expanded
values to obtain equality keys and byte counts, so quadratic CPU work remains;
the smaller output alone does not establish a corresponding latency improvement.
The next optimization should cache or derive serialization identity/size from
immutable observed values while retaining exact equality and full logical audit
reconstruction. Mixed RR-03 workload and isolated pure-settlement timers remain
separate work.

## Indexed compact v0.2

The new explicit `--compact-v2` mode writes `spl-native-trace-stream/0.2`.
Existing `--compact` retains v0.1's wrapper shape and 256-byte eligible-field
threshold; expanded streaming remains unchanged. In v0.2 each node wrapper has
an additional `dependencies` array of integer indices into earlier node records.
The original full `node_id` remains present. The reader reconstructs its exact
earlier node-ID strings in the original dependency order, including repeated
dependencies. It rejects bool/negative/string/self/forward indices, overlapping
encodings, cross-version wrappers and missing completion. No logical identity
is shortened, renamed or omitted.

V0.2 interns the same eligible opaque metadata/value fields at 32 bytes rather
than 256. This selection follows the measured mixed-workload prefix, where
instance scopes, checked types and source spans repeated below the old threshold.
Every node, result and source/audit field still reconstructs exactly. The existing
100,000 node/payload, 32 MiB unique-payload, 8 MiB record, 1 GiB expanded-trace,
64 MiB wire and 256 MiB sampled child-memory guards remain unchanged.

The stage harness selects the new mode with `--audit-driver compact-v2`; the
mixed harness uses `--transport compact-v2` and includes that version in its
matching 100-record prerequisite. After root rebuilt the standalone target,
31 combined transport, stage and mixed-workload regression methods passed in
3.164 seconds. Small-case complete outcomes agree across legacy, expanded
streaming, compact v0.1 and compact v0.2, including failures/skips/discard,
readable/imported sources and Unicode/control characters.

Fresh post-LG-fix mixed experiments are retained as
`rr03-mixed-v2-100-20261123-a` and `rr03-mixed-v2-1000-20261123-a` under the
external SPL artifacts root. Both pass all stages and unchanged source/input/
executable pins under the original budgets. Compiler/reference identity is
`1370523431c8fa7d13e0c424e1547e4885528f764b88b0c256490fa6d874c029`;
runtime remains `673bb0fe936c48a60c1cf5a1a265fb1d1f9f3cd432f380ee9b3011b7729dace9`.
Their source archives include the actual dated dependency closure. The earlier
pre-fix experiments remain unchanged historical observations.

| Original records/titles | V0.2 wire / logical trace bytes | Nodes/edges | Native audit seconds / peak | Reader seconds / peak |
| --- | --- | --- | --- | --- |
| 100 / 2 | 1,527,895 / 5,144,850 | 2,251/3,008 | 0.095617 / 36,106,240 B | 0.254107 / 21,585,920 B |
| 1,000 / 8 | 43,503,437 / 776,599,360 | 64,480/88,010 | 16.291806 / 100,597,760 B | 5.370774 / 73,129,984 B |

The 1,000-record run retains 17,708 payloads containing 7,530,998 unique native
serialized bytes. Its independent reader validates every reconstructed node
without building the 776 MB expanded array, with canonical trace SHA-256
`2e22fd77147b96d987c36839796cdf3125171cbdf5d9daaa479a1b2a4100070b`.
The emitted target separately passes in 0.052341 seconds at 33,710,080 bytes peak.
Whole-experiment time is 24.370983 seconds. V0.2 removes the observed wire-limit
failure for this disclosed mix; no budget profile was enlarged.

These are single bounded samples. They do not establish a production percentile,
full C1 coverage, a compiler/trace proof or distributed capacity. Native execution
still serializes repeated expanded values to derive equality keys/byte counts;
the successful transport change does not establish an equivalent CPU-latency
improvement. Pure-settlement and internal audit-phase timing remain separate
instrumentation work.

## Exact byte accounting without whole-node recompression

The next narrow driver change removes the redundant `json.compress` of every
complete logical node before its fields are compressed for interning. Each
field's native compressed string is now cached once for counting/interning.
Legacy object size is the sum of its two braces, separators, quoted key bytes,
colons and cached value bytes. The expanded-byte guard still runs before any
payload or node is emitted. The existing wire formatter, modes, versions and
all resource limits remain unchanged.

Completion metadata is checked against the exact raw `trace` array byte span in
legacy native stdout, rather than merely a reserialized approximation. After
the target rebuild, all 31 transport/accounting/stage/mixed methods pass in
3.101 seconds, including empty graphs, zero values, failures/discarded output,
readable/imported sources and Unicode/control-character escaping.

Fresh `rr03-mixed-once-100-20261123-a` and
`rr03-mixed-once-1000-20261123-a` runs both pass the same 64 MiB wire/256 MiB
sampled child-memory/1 GiB logical-expansion budgets under the stable post-LG
compiler/reference identity. Every source, original record, projected value and
financial control remains unchanged. The only changed measured dependency pins
relative to the preceding v0.2 runs are the standalone driver and its executable.

| Originals | Prior / current native audit seconds | Current reader seconds | Current whole-experiment seconds | Native / reader peak working set |
| --- | --- | --- | --- | --- |
| 100 | 0.095617 / 0.085857 | 0.251014 | 0.782922 | 35,901,440 / 21,692,416 B |
| 1,000 | 16.291806 / 14.558170 | 5.373187 | 22.671430 | 99,577,856 / 73,510,912 B |

Chunkwise comparison establishes byte-for-byte equality of the full source,
bindings and completed v0.2 wire for both cohorts. The 1,000-record wire remains
43,503,437 bytes with SHA-256
`493ca744ac73185ba238e7ed65a3e9f9e3e7a8e9987509d19596a22ca71c83e6`;
all 64,480 nodes/88,010 edges and 776,599,360 logical bytes reconstruct with the
same canonical trace digest. The exact comparison record is
`rr03-mixed-once-equivalence-20261123-a/comparison.json` under the external SPL
artifacts root. The emitted target separately takes 0.049770 seconds at 1,000
records; its pure-settlement component is still not isolated.

These are individual before/after observations, not a production percentile or
acceptance of RR-03's proposed 15-second close target. Complete measured work is
still over 22 seconds at this cohort. Internal interpretation, node conversion,
ordering and serialization timers plus repeated observations are needed before
attributing the remaining audit CPU or making stronger latency claims.

Large expanded output is still costly. The harness parses a child result only
after a successful exit and bounded complete stdout. Its native output budget
therefore also bounds parent parse input bytes, although parent parsed-object
memory can exceed that byte count and is not included in child working-set
metrics. Keep this distinct from a solution for arbitrary-size downstream trace
consumption; a streaming reader or validated compact transport is future work.

After these probes, select a narrow optimization from actual timing, memory and
byte evidence. Preserve the independent controls and full audit lineage. Likely
profiling boundaries are picture-by-receipt scans and trace operand duplication;
the existing archival transport operates after trace generation and therefore
does not repair its native memory cost. Instrument internal phases before
attributing elapsed time to a particular implementation function.

Then add RR-03's explicit mixed neutral-fact generator: receipts/costs/events/
lineage, allocation fan-out, hot-pool skew and sequential periods. Keep independent
scopes separate from shared pools, gates and state chains. Establish meaningful
single-process limits before planning worker parallelism or distributed execution.

A pure timer should decode bindings before its clock starts, execute the emitted
`settle` function repeatedly with results consumed, then time result serialization
separately. Compile that driver as a native executable from the exact emitted
library and retain its source/executable hashes. Establish whether the compiler
can share immutable results across repeated identical calls before interpreting
per-iteration timings. An instrumented audit driver needs independent construction,
topological-order and serialization timers. The present whole-process stage
differences cannot establish those internal costs.
