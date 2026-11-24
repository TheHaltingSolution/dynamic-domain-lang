# Explicit indexed SV source experiment

`cases/sv/sv01-indexed.spl` is a new, opt-in implementation named
`SkourasVenturaIndexedExperiment`. It retains the selected exact SV financial
policy while testing grouping before per-picture filtering. It is not the
default source, a new financial primitive or evidence of a necessary extension.
`cases/sv/sv01.spl` and `Demos/SV.lean` remain byte-for-byte unchanged.
The experimental implementation ID is `sv-indexed-experiment/1`, qualified by
the exact source/emission hashes below; it is separate from the unchanged
economic policy identity `sv-incurred@1`.

## Source contract and assumptions

Receipt and selected cost views are grouped once by their declared `Id<Asset>`
keys. The source still iterates the complete **supplied picture list** in its
original order. Each lookup returns that picture's rows or an explicitly typed
empty list; each group's relative source order and multiplicity are preserved.
An absent group gives a zero sum, not an absent title. The implementation does
not build a unique picture map, discover the picture universe from receipts or
deduplicate original rows. Raw duplicate-picture behavior stays observable.

The existing half-open receipt/incurred-date predicates remain inside the
selected groups. Eligible/excluded cost selection, original allocation
authority, full funding snapshots, cutoff admission and source-to-view lineage
remain at the unchanged canonical boundary. Grouping does not add invoice face
amounts to cash, infer eligibility or solve any financial answer in the adapter.
The independent original-fact oracle must run **before** projection and control
every title's cash/fee/cost/basis/share/earned and pooled recovery/payable/closing.

The formulas are unchanged: fee is already `cash * fee_rate` in the original,
not a newly assumed aggregation of rounded per-receipt fees. No rounding or
floating-point computation is introduced. Funding branch, share, basis,
nonnegative-earned assertion and pooled advance recovery remain identical.

All input envelopes and values are decoded before execution, including unused
rows. Under those typed bindings, asset-key projection and comparison are total.
Grouping accepts repeated keys and preserves their rows; it adds no
`DUPLICATE_MAP_KEY` business error. Top-level definitions are evaluated eagerly
in declaration order: there is no claimed lazy global index. A separate picture
count guards grouping inputs so an empty universe never traverses unrelated
receipt/cost collections after decoding.

The negative-opening assertion remains first. Per-picture funding checks and
negative-earned checks retain supplied picture order, including first-negative
earnings before a later invalid share. Group construction occurs before that
iteration and can introduce different resource-failure timing. Equivalence of
all resource-versus-business error precedence is expressly **not** established.
Any observed counterexample must remain visible, rather than being relabeled a
financial-policy success.

## Version and generation pins

| Artifact | SHA256 |
| --- | --- |
| Preserved `cases/sv/sv01.spl` | `0ecd2b31d1be9e8e3764cacc8e1135422fb32786bae8f8a3a1833db9615d6cec` |
| Preserved `Demos/SV.lean` | `ef23268f4f7e1144776a4418778e4a3eb7d815996bffed3b8bd6b233e62578c9` |
| Indexed source | `d1048ec51867332ff5e136aa90bdac011fd132df982cb4baba5efc9c6899d9b5` |
| Native-generated `Demos/SVIndexed.lean` | `4f0ae3430028f78f1de95513da9337b0ea9fb9719e94ec1443888efc2d0e46be` |

The new Demo was generated exclusively by the existing authoritative native
compiler, without editing its output:

```powershell
& .lake/build/bin/spl.exe compile cases/sv/sv01-indexed.spl Demos/SVIndexed.lean
```

The pre-experiment old source/emission/executable are also archived externally
under `artifacts/spl/sv-indexed-baseline-20261123-a/`. Its old executable SHA256
is `60e02bf6ef0a84866341941b651c5df94f4db6bafe4a83dbadcbab4ed749cd22`,
identical to the completed capacity-1,000 observation. Build-specific binary
pins belong to that evidence, not portable source tests.

Root coordinates the separate `spl_sv_indexed` Lake target/build. Native tests
compare a fresh native emission with this file and require the prebuilt target;
they never rebuild or silently skip missing binaries. The optional target is
not a default Lake target. Harness selection defaults to the original source.

## Finite controls and current evidence

Four Python reference/boundary methods pass. Original-fact cases cover the baseline,
authorized allocation plus invoice ancestry, exact fractional cash and 2/3
funding, exact subsecond cutoff admission, all four half-open date boundaries, and the mixed 100-record workload
with explicit exclusions. Each runs its independent oracle before projection
and compares both source implementations' complete financial outcomes.
The equal-cutoff failure is separately rejected by the independent oracle and
canonical admission before projection, without native financial execution credit.

Separate raw typed-view compatibility witnesses cover empty and zero-activity
titles, duplicate pictures, supplied list permutations, unrelated assets,
negative-opening/invalid-share precedence, first negative earnings before a
later invalid share, and invalid unused dates rejected during typed decoding.
These raw witnesses do not claim canonical admission of duplicate/out-of-scope
original financial facts.

After the optional target build passed, all seven focused methods passed in
4.579642 seconds with zero skips and unchanged source/executable pins. Eighteen
cases produce 72 old/new emitted and old/new native IR observations. Every
compared financial status/output/closing/error code agrees. Four reference and
boundary methods additionally control original facts and pre-projection failure
admission. Invalid input decoding is not credited as financial execution.

External `artifacts/spl/sv-indexed-checks-20261123-a/` retains frozen sources,
binary pins, test log/verification, original neutral facts, canonical package,
source-to-target lineage/dispositions, bindings, independent expected outcomes
and every complete raw native result/trace. Compiler/reference identity is
`323f0d844fe11344713523f40d83d3b67d32d1376ce89da823875d72c2a297bc`;
runtime remains `673bb0fe936c48a60c1cf5a1a265fb1d1f9f3cd432f380ee9b3011b7729dace9`.
The old source, generated target and executable remain byte-identical.

The mixed 100-record IR has 1,312 observations versus the original's 2,251.
Small cases can instead grow: the original four-fact fixture goes from 273 to
280, and empty-picture reports from 48 to 67. A first invalid share still blocks
with `INVALID_FUNDING_SHARE`, but the new graph has 59 nodes versus 22 because
index work precedes the assertion. These are current-program observations, not
a universal efficiency or all-resource-error equivalence claim.

The financial/error/state comparison intentionally excludes old/new graph
identity. Every observed new-program dependency order and unique node identity
is checked. Changing source expressions changes structural node IDs and
decision structure. The [representation-only logical relation](logical-trace-relation.md)
cannot be claimed between these different programs.

## Resource scope and next gate

The source removes repeated explicit whole-receipt/cost scans per picture, but
the current Map implementation uses sorted association lists; grouping is not
a promise of constant-time hashing or optimal runtime complexity. In addition,
`Interpret.iteration` records the full source collection as an instance operand.
One global grouping pass can therefore still create quadratic logical trace
expansion, even with fewer observations. Native compiled calculation, reference
observations, native audit generation, wire bytes and expanded bytes remain
separate measurements.

No kernel/compiler/schema mutation or guard increase belongs to this experiment.
Small native controls must pass before any large workload. Future measurements
must explicitly select the indexed source/target and also check the preserved
old compiled target against the original-fact oracle. The old 10,000-record IR
failure remains evidence; it is not rerun or represented as a complete baseline.
Keep the same 100,000-observation, 1 GiB expanded, 64 MiB wire and 256 MiB sampled
child limits. A remaining audit/resource failure is a valid experiment outcome,
not permission to omit lineage, publish a prefix or silently enlarge budgets.
The small verification duration is not a settlement timing benchmark. No indexed
10,000-record completion, production percentile or default-runner replacement
is claimed here.

## Opt-in harness selector

The mixed harness now accepts `--implementation indexed`; omission means
`legacy`, preserving `sv01.spl`/`spl_sv`. The indexed choice selects only the
fixed indexed source/emission/executable, records `sv-indexed-experiment/1`, and
adds those files and the executable to its dependency closure. Each scale gate
requires matching implementation, exact selected spec, source/binary pins,
transport, profile flag, seed and budgets. A legacy report cannot admit an
indexed 1,000/10,000 run. Existing 100/1,000 generator bytes remain unchanged.

Every indexed cohort freshly native-compiles both selected and original sources
and requires exact equality with their separately pinned generated Demos. It
then runs the current original-source compiled target on the **same bindings** and checks
every original-fact oracle title/pool/closing output, in addition to checking
the indexed target and complete new-program audit. Missing/failed/unchecked
old-target controls block cohort success and the next scale gate. It does not
run the old IR at 10,000 or claim old/new graph identity.

After the deliberate memoizing-emitter promotion, `legacy` continues to mean
the same original SPL source, with a current memoized executable. Reports now
qualify `target_generation` as `spl-native-definition-thunk/1`, which must
match for scale admission. The compatible `old_target` field names this current
source-algorithm baseline. Historical pre-memoization executable evidence below
remains separately pinned and is never silently substituted into a new run.

`--host-load-note` records the actual known concurrent work. A regression
running in an isolated checkout still competes for this host's CPU. Such runs
can characterize completion, node/byte counts and resource failures, but cannot
support standalone causal before/after latency, p95 or SLA conclusions. Native
measurements remain separately coordinated; the selector's 23 passing
mixed/stage control methods themselves supply no benchmark credit.

```powershell
python scripts/spl_mixed_benchmark.py --implementation indexed --records 100 --transport compact-v2 --host-load-note "State actual known background work here" --output FRESH_EXTERNAL_PATH
```

## Bounded source-only probe: failed, not adopted

The subsequent `rr03-indexed-{100,1000,10000}-20261123-a` archives ran under the
same `323f0d...` compiler and `673bb0...` runtime pins above. The isolated
813-method checkpoint regression was active on this host. These observations
establish completion and resource failures; they support no causal latency,
percentile, or SLA claim. Original source, generated target and executable were
preserved, and dependency pins stayed unchanged through each probe.

| Originals / titles | Compiled indexed target | Native audit observations | Expanded bytes | Compact wire bytes |
| --- | --- | --- | --- | --- |
| 100 / 2 | Complete; full oracle agrees | 1,312 | 3,824,516 | 1,054,599 |
| 1,000 / 8 | Complete; full oracle agrees | 11,527 | 128,745,489 | 10,390,551 |
| 10,000 / 40 | 60-second timeout; zero output | `RESOURCE_LIMIT` head; incomplete | 1 GiB guard exceeded | 14,237,800-byte unconsumable prefix |

At 10,000, the original-fact oracle, projection and Python reference completed;
the reference reported 11,467 observations. The preserved original compiled
target passed every oracle title/pool/closing check in 0.237454 seconds. The
indexed compiled target timed out after 60.013618 seconds (59.359375 CPU seconds,
46,874,624-byte peak working set). Its result was not replaced by the old result.
The separate native audit failed after 23.266251 seconds, with
`COMPACT_EXPANDED_BYTE_LIMIT`, a 150,847,488-byte peak working set, and a blocked
`RESOURCE_LIMIT` head containing empty emissions/state. No completion record,
reader success or audited financial/state result was credited. All dependent
four/eight-close successors were `not_executed`. There was one 10,000 probe,
no retry and no guard increase.

The source-only experiment therefore failed its large-cohort gate and remains
unadopted. The old target's completion and the new target's timeout are concrete
facts despite the shared-host timing caveat. The later emitter investigation
is a separately pinned compiler experiment; it cannot retroactively turn this
failed run into a pass.

## Diagnosis and separate compiler experiment

The old emitter hoisted `Unit → Eval Value` closures. Definitions captured
other closures before the declaration-order force statements replaced names
with `pure` values. Such earlier captures recomputed their dependencies, unlike
the native IR interpreter's definition cache and Python environment cache.
For the archived emitted indexed C, the successful eight-title call graph
predicted 114 group builds. A later isolated generated-C counter actually
observed 114, versus two after the separate `Thunk.mk`/`.get` emitter candidate.
The counter wraps only disposable generated C calls; it changes neither the
financial source nor shared runtime. See [the memoization experiment](emitter-memoization-experiment.md)
for toolchain semantics, exact pins, controls and limitations.

The Runtime grouping helper still uses keyed insertion sorting, association-list
operations and per-key filtering. Memoizing definitions addresses redundant
group construction; it supplies no stronger asymptotic claim for this helper.
The native audit also still records full source collections in instance
operands. Its resource failure is independent of compiled-target recomputation.

Python's 11,467 observations and native IR's 100,000-observation guard are
different alphabets: the native evaluator records references, fields, literals
and per-row instance nodes which Python does not uniformly emit. Python's
smaller count is not evidence that a native trace is missing observations,
and neither count supplies a coverage percentage for emitted calculation.
