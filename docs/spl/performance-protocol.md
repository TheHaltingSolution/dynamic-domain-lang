# Bounded repeated performance protocol

This work completes the remaining measurement machinery around the existing
[mixed workload](mixed-workload-plan.md), [pure settlement timer](pure-performance.md)
and [indexed source experiment](indexed-sv-experiment.md). It changes no financial
source, core semantics, schema, canonical publication format or resource guard.
The original generator and default legacy-source target remain unchanged. The
indexed source stays experimental; its retained 10,000-record audit failures and
blocked successors are not retried or relabeled by this protocol.

The new [runner](../../scripts/spl_performance_protocol.py) and
[focused checks](../../Tests/test_performance_protocol.py) use one worker and
explicit dependency/source/input/executable pins. The compilation closure includes
the actual Lake C-command trace and response-file flags, linked runtime objects,
resolved static/import libraries, compiler/toolchain executables and headers,
the selected source, emitted Demo, Python harnesses, schemas and source fixture.
It checks the full closure before each observation and at completion. Shared
Lake output is read only; schedule compilation writes disposable Lean/C/object/
executable artifacts and never writes shared `.olean` files.
Repository inputs and cached objects/executables are copied into a pinned
checkout snapshot; the external toolchain retains complete file hashes.
Those hash reads themselves warm filesystem caches before observations.

## Observation scopes

The full planned repetition bracket is three fresh-process observations followed
by thirty later fresh-process observations per 100/1,000 original-record cohort.
These are fresh versus reused output directories and later host-cache-warm
processes. They are not controlled OS cold-cache runs. Runtime libraries and
compiled schedules are cached and pinned; each measured compilation still
executes its selected tools rather than reporting a cache-hit lookup as compile
time. Host CPU competition, hardware, worker count, process startup and per-child
CPU/working-set scopes remain explicit. Smaller selected sample counts are smoke
controls and cannot complete the repetition protocol.

Compilation intervals are native frontend/source-to-Lean emission, Lean
elaboration/C generation, C object compilation and native link. The freshly built
target must pass complete independent title/pool/closing controls. Full original
facts produce those controls before compiler projection. A failed stage prevents
its downstream compile/link/control steps and subsequent dependent compilation
observations. Prebuilt-target mixed measurements are a separate branch with their
own fresh emission-byte and full independent controls; they cannot replace a
failed disposable compilation.

Mixed observations retain the existing separate validation, projection,
dependency/semantic hashing, reference, native target, compact IR audit and
bounded reader scopes. Native process timings include startup/decode/calculation/
serialization; the separate pure timer supplies actual decoded-input settlement
and serialization intervals. Existing internal audit profiles retain their
overlapping/nested interval warnings and clock-overhead observations. They are
not added together or subtracted to invent a pure timer.

The protocol retains every failed or unexecuted sample and uses exact timing
strings. Successful-only empirical nearest-rank summaries show their denominator
and all censoring. They are not population p95, SLA, production-distribution or
capacity conclusions. A successful selected-stage report is distinct from all
protocol obligations being complete.

## Fixed runtime guards and separate compiler profiles

Calculation/audit/reader/publication observations retain the existing 60-second
native timeout, 64 MiB stdout/result budget, 256 MiB sampled child working-set
budget, 1 GiB logical expanded trace limit and 100,000 native IR observations.
The orchestration Python worker has a separately disclosed 240-second aggregate
wall budget because it executes several individually bounded children; this
does not increase any native stage timeout. Working-set observations exclude
descendants, siblings, parent preparation and filesystem cache. The 20 ms memory
sampling may permit transient overshoot. Compiler/link driver descendants are
not silently included in a driver's measured working set.

The original `runtime256` compiler profile also uses 60 seconds/256 MiB. Its
first actual focused SV attempt passed frontend emission in 0.042250 seconds,
then failed Lean elaboration/C generation after 1.071251 seconds at a sampled
269,250,560 bytes. C object, link and financial control were not executed. A
separately labeled same-budget retention replay is external at
`artifacts/spl/performance-protocol-aot-guard-20261123-a`; it is not a passing
compilation or a completed repetition campaign.

After that observed boundary, the coordinator authorized the explicit
`compiler1g180` profile: one worker, 1 GiB sampled child working set and a
180-second timeout for compiler tools only. It is separate evidence, not a
passing rerun of `runtime256`. The resulting financial target control still
uses the unchanged 60-second/256 MiB runtime profile. Both profiles preserve the
same exact source, tool flags, sample limits and financial controls. A failure
at 1 GiB remains a failure; this protocol permits no further memory ratcheting.

```powershell
python scripts/spl_performance_protocol.py --compiler-profile compiler1g180 --host-load-note "Describe actual concurrent host work" --output FRESH_EXTERNAL_PATH
```

Do not start a large run until source/build inputs are frozen and the small
native toolchain/control path has passed or retained its explicit resource
failure. Reusing an old successful summary with changed pins, seed, transport,
generation, missing reference control or incomplete reader cannot authorize a
larger cohort or later sample.

## Remaining implementation and measurements

The runner implements repeated compilation and mixed-stage orchestration, three
pure-timer processes with ten verified warm batches each, a four-close audited
stage chain and genuine generic IR artifact publication. Focused and frozen
campaign results are recorded below. They do not establish completed canonical
closes or a service-level target.

The [chain adapter](../../scripts/spl_audited_stage_chain.py) uses the separately
named `rr03-stage-chain/1` synthetic source profile. From its first close, a pinned
synthetic authority observed/approved on 15 December 2025 explicitly continues
agreement, roles, membership and interpretation authority through 1 January 2027.
The original single-quarter authority would fail `SV_AGREEMENT_PERIOD`; it is not
waived or retrospectively extended. Exact profile differences and the authority
document/hash travel with the new records. Economic terms remain unchanged;
absence of intervening amendments/funding is an explicit selected assumption.

Each 1,000-record snapshot has 950 fresh cash/cost/invoice original rows and the
same 50 original historical funding events. Four closes therefore have 3,850
distinct originals, not 4,000 newly issued facts. New/reused/guarded/projected
counts are separate. Independent controls require every original funding event
to enter exactly one title's valuation, the funding IDs/dates/amounts and title
funding totals to remain identical, and subsequent opening advances to come
from actual completed prior wires. Old funding evidence never becomes fresh
cash or a fresh prepayment issue. The default 100/1,000 generators stay byte
identical. A new independent oracle runs before projection for every close.
Actual native IR closing JSON encodes the checked USD prepayment as a canonical
Rat; transport restores that exact value into the pinned USD opening slot, using
the checked source type rather than inventing currency tags in native outputs.

Generic publication reconstructs the exact existing native IR outcome and uses
the genuine general artifact helper, without fabricating canonical fields. Such
an IR artifact is not a canonical financial result: no canonical fields will be
fabricated to make it appear one. Canonical-close credit stays false. If expansion,
serialization, memory or result size fails first, retain that measured failure
and leave dependent publication/chain stages `not_executed`. An incomplete first
audit supplies no successor money or state. The known 10,000-record four/eight
successors remain unexecuted; these measurements do not close the larger
`B-PERF-ENVELOPE` topology/fan-out obligations or canonical carry support.
The existing 64 MiB reconstruction guard also remains unchanged; its failure is
separate from the independently completed non-expanding audit reader and from a
writer or memory failure. It cannot be relabeled as a measured writer rejection.

## Frozen measurement results (23 November 2026)

The corrected focused cohort passed all 48 methods with zero failures, errors,
skips or source/dependency drift. The first small gate is retained as a harness
failure: compilation and its genuine 100-record audit completed, then an
observational summary's optional JSON null was incorrectly sent to a financial
decoder. The corrected metadata path permits null while retaining duplicate-key,
float, nonfinite and size rejection. Financial decoders stayed unchanged.
`performance-protocol-small-20261123-a` is not repinned or credited as a 1,000 gate;
the fresh `-b` gate completed separately under its new harness pins.

The full campaign is external at
`artifacts/spl/performance-protocol-full-20261123-a`, with source/cache snapshots,
all 179 dependency hashes, per-observation commands/CPU/working-set/input/output
measurements, original-fact controls and terminal audits. Its 931.727135 seconds
include concurrent immutable unit-regression host load. The host reported Intel64
Family 6 Model 198 Stepping 2, 24 logical CPUs, 68,053,336,064 physical-memory
bytes and Windows 11; the matching processor brand read after the run was
Intel Core Ultra 7 270K Plus. One protocol worker ran. Compiler/module/runtime
identities stayed `20ea52ba…` / `a5165f5d…` / `673bb0fe…`; complete values and
all source/toolchain/executable/flags pins remain in the retained reports.

All 33 compiler observations and all 66 mixed observations passed: three fresh
outputs plus thirty later observations per selected group. The 30 later compiler
medians were 0.039132 seconds for native frontend emission, 1.563206 for Lean
elaboration/C generation, 0.212035 for C compilation and 0.873052 for linking.
The separate `compiler1g180` codegen peak was 883,118,080 bytes. C/link metrics
retain their driver-child scope and exclude descendants. Generated C and object
hashes were identical; all actual executable hashes are recorded. Reused output
paths retain their final executable, while the three fresh executables remain
separately archived. These observations do not constitute a full cold-runtime
build or deterministic byte reproduction of every overwritten warm executable.

| Later fresh-process observation, 30 samples | 100 originals | 1,000 originals |
| --- | --- | --- |
| Whole mixed worker median | 1.166277 s | 18.271980 s |
| Empirical nearest-rank successful-worker p95 | 1.184560 s | 18.545956 s |
| Native emitted-process median | 0.044067 s | 0.050118 s |
| Native compact-audit median | 0.085523 s | 9.729574 s |
| Independent bounded-reader median | 0.248225 s | 5.396730 s |
| Maximum audit child working set | 36,130,816 B | 96,190,464 B |
| Maximum reader child working set | 22,040,576 B | 73,543,680 B |

Every complete wire at a given size had the same SHA-256, with 2,251/64,480
nodes, 5,144,850/776,599,360 expanded trace bytes and 1,527,895/43,503,437 wire
bytes. All title, fee, cost, basis, share, pool, opening and closing controls
passed. These are disclosed stage clocks with startup and host competition;
they do not establish a population p95, the proposed 5/15/60-second targets or
completed canonical-close latency.

The pure driver independently completed three processes with ten verified warm
batches each at both sizes. All 30 spans exceeded 100 ms (minimum 115.419900 ms
and 211.056200 ms). Median actual decoded-input settlement was 0.114158 ms and
1.668138 ms per call, with serialization 0.006724 ms and 0.020029 ms. All varied
opening outcomes, byte counts and checksums passed. These remain separate from
startup, audit, canonical validation and publication.

Both actual four-close audit-stage chains completed. The 1,000-record chain
retained exactly 3,850 distinct originals, unchanged original funding bytes and
title funding valuations, adjacent actual wire-derived opening values and native
recovery `[250, 0, 0, 0]`. The 100-record chain similarly retained 385 originals.
Every successor was independently controlled from original facts before projection.
Neither chain is canonical carry evidence.

Generic IR artifact publication succeeded for all 33 100-record observations.
The first 1,000 reconstruction failed `RECONSTRUCTION_BYTE_LIMIT` under its
unchanged 64 MiB guard, at 191,594,496 bytes child peak. Its financial-control,
writer and reload stages were not executed; the next 32 publications were
`not_executed`. The bounded completed-result loader rejects its running marker.
The full campaign therefore ends **failed at IR publication**, with no canonical
close or larger-capacity credit. No 10,000-record retry or guard increase occurred.

## Concrete next boundary

Usable 1,000-record canonical closes require a separately reviewed, explicitly
versioned canonical compact-audit result/publication path. It must bind the exact
financial head, checked source/input/build identities, complete logical trace
hash and immutable wire file hashes, validate every node/reference/completion
without reconstructing the expanded array, retain current atomic ownership and
failure rules, and make old loaders reject its new version. Current default
array results and all resource guards should remain unchanged. This is a new
canonical integration task, not an inference from generic IR publication.

The retained 10,000-record failures need another measured source/trace-size
experiment as well. Read-only census of the completed indexed 1,000 archive
found 98,273,543 operand-value bytes and 13,800,672 fact-ID-value bytes; receipt
grouping's 660 instance nodes alone occupy 73,825,466 canonical node bytes.
Exact census and source spans are external at
`artifacts/spl/performance-next-analysis-20261123-a`. Repeated whole collection
operands are a concrete target. Bounded chunks or lossless physically indexed
ports would be new program/input contracts requiring original-fact/lineage,
scope/date/error-order and complete old/new financial controls. Chunking can add
observations, and compact publication alone cannot defeat the existing 100,000
observation or 1 GiB logical-trace limits. Neither candidate is implemented or
promised to make the 10,000 case complete.
