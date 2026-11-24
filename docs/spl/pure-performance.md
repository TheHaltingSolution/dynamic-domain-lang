# Isolated emitted-settlement timing

`spl_pure_benchmark` times the actual pure function emitted from the unchanged
original SV source. `Demos/SVBenchmarkLibrary.lean` is generated exclusively by
the authoritative native `compile-library` command and contains no global main.
The driver imports that library, never the executable `Demos.SV`, and duplicates
no fee, cost, participation or advance-recovery formula.

```powershell
lake exe spl compile-library cases/sv/sv01.spl Demos/SVBenchmarkLibrary.lean
lake build spl_pure_benchmark
python scripts/spl_pure_benchmark.py --output C:/Projects/Film_TV_participation_dynamic_DSL/artifacts/spl/pure-settlement-new
```

The harness performs no build. It requires fresh native library emission to match
the checked-in importable library byte-for-byte before crediting any observation.
Native source/library/driver/executable and Python/oracle/input/build pins are
retained with a source archive and exact binding/plan bytes. Source/binary
correspondence also depends on the preceding pinned Lake build.

The two selected data cohorts are the same disclosed original-record 100/two-title
and 1,000/eight-title mixes from [the mixed-workload plan](mixed-workload-plan.md).
The independent original-fact oracle checks the base data and 64 separately
supplied exogenous opening advances: USD0, USD1000, through USD63000. These
values come from the benchmark nonce, not solved earnings. The oracle runs before
projection and produces complete expected title/pool/closing outcomes for each.
The driver decodes inputs, all opening variants and expected outcomes before its
settlement clocks start.

| Native clock interval | Scope |
| --- | --- |
| Binding/plan preparation | File reads, strict typed decode and expected-outcome encoding |
| First decoded call | First actual emitted settlement call in the process; OS/CPU cache state uncontrolled |
| Warmup | Actual settlement, serialization and checks; recorded separately |
| Settlement batch | Runtime nonce selection, noinline IO boundary, actual emitted settle, strict result retention and loop overhead |
| Serialization batch | Existing target `outcomeJson` and compact JSON encoding, with retained output strings |
| Verification | Whole-outcome equality against independent controls plus portable FNV1a64 byte consumption checksum |

The driver uses Lean4.35's opaque `IO.monoNanosNow`, whose pinned reference is
`reference-manual/Manual/IO.lean` under the external Lean library; its declaration
is in toolchain `src/lean/Init/System/IO.lean`. The pinned compiler's
`Lean/Compiler/InlineAttrs.lean` defines `@[noinline]` as never inlining the marked
definition. The driver applies that boundary to an IO call of the actual emitted
library function. Runtime-varying openings yield real result changes; retained
strict results and later full-output checks/checksums make them observable. This
is explicit benchmark discipline, not a theorem about all compiler optimization.

Default batches begin with 128 iterations, double until at least 100 ms of
settlement time, and stop at a fixed 8,192-iteration bound. Failure to reach the
span is reported explicitly. Three final warm batches are retained per process,
and the parent launches three separate processes. Calibration batches and all
first/warmup observations remain visible. These are disclosed observations,
not controlled cold-cache measurements, production p95 or RR-03 target acceptance.

Child timeout, output and sampled working-set budgets remain explicit. Checks or
resource failures fail the cohort; they cannot become successful zero-timing
samples. Process CPU and peak working set describe the whole child, including
decode, retained arrays and checks, while native clock intervals have their own
scopes. No whole-process subtraction is presented as a pure timer. Audit and
canonical finalization are deliberately outside this separately named calculation
experiment; no audited capacity or actual-payment claim is made.


## Initial measured evidence (2026-11-23)

External evidence: `artifacts/spl/pure-settlement-20261123-a/summary.json`
under the external project folder. All six focused test methods passed. Fresh
native library emission matched exactly; all source/executable dependency pins
remained unchanged. Compiler/reference identity was `1370523431c8fa7d13e0c424e1547e4885528f764b88b0c256490fa6d874c029`.

| Original records / titles | Median settlement per call | Median serialization per call | Selected iterations per batch | Whole child peak working set |
| --- | --- | --- | --- | --- |
| 100 / 2 | 0.339851 ms | 6.416 microseconds | 512 | 34,840,576 to 34,881,536 bytes |
| 1,000 / 8 | 4.715209 ms | 18.712 microseconds | 128 | 35,745,792 to 35,782,656 bytes |

Each row contains three processes with three final warm batches each. All batches
reached the 100 ms minimum, exercised all 64 opening variants, and passed whole
independent outcome, serialized-byte and checksum controls. First decoded calls
were 0.3635 to 0.3681 ms and 4.5926 to 4.6328 ms respectively. These are first-in-process
observations with uncontrolled cache state. Independent 64-variant original-fact
preparation took 0.753443 s and 7.280372 s outside the native calculation timer.
The entire harness took 16.760235 s.

The 100-record batch serialized 544,584 bytes with FNV1a64
`7459827622397693181`; the 1,000-record batch serialized 383,380 bytes with
`9409888353733679969`. Different batch iteration counts explain the byte counts.
Three-process observations support neither a production p95 claim nor RR-03
acceptance. The roughly 14.56 s complete native audit observation remains a
separate experiment; these measurements do not assign that cost to internal
audit stages by subtraction.
