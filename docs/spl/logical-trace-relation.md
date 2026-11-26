# Logical trace preservation: finite acceptance

This records the observation relation accepted by LD03, lines 441–455 of
`C:/Projects/Film_TV_participation_dynamic_DSL/ResearchAgent/documents/SPL_LD03_Completion_Review.md`,
and its finite application to the measured fact-ID collector optimization.
It is an execution comparison contract, not a general compiler or trace proof.

Two completed native observations satisfy the relation when they preserve:

- Financial status, exact outputs and closing state, diagnostic/error outcomes,
  and whether outputs were discarded on failure.
- The complete ordered logical node sequence: exact identities, types, rule and
  source locations, scope, original fact lineage, operands and optional results.
- Dependency order and exact dependency/detail references, decision outcomes,
  evaluated/skipped/failed/discarded status and lazy unevaluated alternatives.

JSON object-key order, shared-payload IDs and transport wrappers are
representation. A versioned compact dependency index must reconstruct the exact
original node-ID string; it cannot shorten or replace logical identity. Sharing
cannot remove repeated logical nodes or change their values, multiplicity,
decision history or source lineage. Exact textual identities remain exact Text
where their declared source types are Text; the relation introduces no ASCII
restriction or normalization.

The compact reader must validate closed records, earlier references, unique
identities, framing, declared counts and all configured byte/resource bounds.
Completion is mandatory. A valid header or prefix, including apparently valid
financial fields, grants no publication or successor-state authority after
truncation. Expanded reconstruction has a separate budget. A transport checksum
or source pin is evidence of byte identity, not custody or external-fact approval.

## Tested change and exact pins

The selected change replaces `Trace.nodeJson`'s intermediate fact-ID lists and
`List.eraseDups` with an exact `Std.HashSet String` accumulator, followed by the
same explicit lexical sort. All other logical node fields and calculation
semantics remain unchanged. The standalone compact driver is identical across
this pair; both compact protocol versions retain their existing guards.

| Pin | Before | After |
| --- | --- | --- |
| Compiler/reference | `1370523431c8fa7d13e0c424e1547e4885528f764b88b0c256490fa6d874c029` | `654c5a91f8e16975e77f473943caff362e117949e8f232767c25edf6ced3bbba` |
| `SPL/Trace.lean` SHA256 | `03ebeb8488f5a77632358527bfe4c1fa1596d71f12d159ba063f2fbd08ebf60d` | `e053c0b82b3f0d1d4856c55d4212cd7c229aa36210c5d2ebc9b4cc4c3ceae6d4` |
| `spl_trace_stream.exe` SHA256 | `52cebac7d7202b26ccd20cb4455d8d8bad57ecd0fd450e3e65467121d7a9fe53` | `1fb5888cbfb2f575b46a637335183573f549f3f39466998553d816ea3a0d57cb` |

Shared driver SHA256 is
`437f218a9e72d3b95c9dd4d894f6dfe0643aa02f4788f85fa7641e8226bdbf32`;
runtime identity is
`673bb0fe936c48a60c1cf5a1a265fb1d1f9f3cd432f380ee9b3011b7729dace9`.
The post-change module identity is
`d73920c18ffd5c5d47c0bc45871b300ab67fe92bf1ce9f0c6a01aa482d6013a4`.
Later publication integration changes compiler/module fingerprints; these dated
pins must remain unchanged rather than being repinned to a newer tree.

## Executed witnesses

The rebuilt candidate passed 34 methods in 6.263 seconds with this command:

```text
python -m unittest Tests.test_trace_stream Tests.test_mixed_workloads Tests.test_stage_benchmark
```

The frozen full legacy formatter is compared with the new complete node JSON,
both parsed and compressed, across 560 combinations. These include nested
records/lists/maps/tuples/options, duplicate/empty/Unicode/control-character fact
IDs, every Value constructor, optional results, operand permutations and
evaluated/failed/not-evaluated/discarded/passed statuses. An explicit independent
nested identity expectation supplements the differential formatter. The native
transport checks also exercise failure/discard, lazy branches, selection ties,
binding/frontend errors, links, readable source and opaque Unicode/control Text.
Malformed references, framing, completion and resource metadata are rejected.

Fresh original-record mixed cohorts of 100 and 1,000 preserve independently
checked complete title/pool/closing outcomes and validate every reconstructed
node. Direct chunkwise comparison finds identical source, bindings, source-batch
and original-record bytes before/after, and identical complete v0.2 wire in each
profiled/unprofiled pair and against the preceding implementation.

External evidence under `C:/Projects/Film_TV_participation_dynamic_DSL/artifacts/spl/`:

- `trace-factid-baseline-20261123-a/`: archived old source and executables.
- `rr03-mixed-profile-{100,1000}-20261123-a/`: pre-change runs and pins.
- `rr03-mixed-factids-{100,1000}-20261123-a/`: post-change runs and pins.
- `rr03-mixed-factids-1000-20261123-a/collector-comparison/comparison.json`:
  exact input/wire comparisons, test evidence, archived formatter source and C.

The 1,000-record result preserves 64,480 nodes, 88,010 edges, 17,708 payloads and
776,599,360 expanded bytes in 43,503,437 wire bytes. Logical trace SHA256 is
`2e22fd77147b96d987c36839796cdf3125171cbdf5d9daaa479a1b2a4100070b`;
wire SHA256 is
`493ca744ac73185ba238e7ed65a3e9f9e3e7a8e9987509d19596a22ca71c83e6`.
An earlier large legacy serializer did not finish: this is exact observed
before/after compact-wire equivalence plus the finite formatter comparisons,
not a claim that a complete 1,000-record legacy run was observed.

## Scope and dependency disposition

This closes the finite `B-AUDIT-TRACE-REL` acceptance for this source pair and
selected optimization. It does not establish emitted-target branch coverage,
all-program equivalence, a production latency percentile, a whole-pipeline SLA,
10,000-record completion or default canonical compact integration. The measured
node-JSON interval falls from 6.637718 to 1.392800 seconds; exact scopes and
uncontrolled timing limitations remain in [the mixed workload record](mixed-workload-plan.md).

`B-PERF-PROFILE` should depend on the completed narrow 1,000-record internal
profile, logical-relation acceptance and measured optimization evidence. A
dependency on the entire workload/stage campaign would incorrectly keep this
completed finite slice blocked. Larger workloads, repeated closes, capacity
boundaries, default-runner integration and SLA acceptance retain their own
unfinished dependencies and receive no credit from this disposition.
