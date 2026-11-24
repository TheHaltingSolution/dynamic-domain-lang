# First-dollar merchandising recognition

This registered existing-language method implements the selected proposed
[trigger-period policy](policy.md) from independently authored
[original facts](neutral.json) and [design](../../docs/spl/merchandising-reprice-design.md).
The independent controls are in `oracles/merchandising_reprice.py`. The source
does not import their results or use paid cash as prior recognized entitlement.
The selected implementation passes39 combined oracle/module methods and six
retained completed bundles, including actual Q1-Q4 carry and preview. The final
evidence is recorded below. Earlier draft failures remain retained.

Production40m times the authorized multiplier, plus production charge6m and
supplied Funding Charge1m once, gives thresholds77m/87m/107m. Inclusive box
observations select a first-dollar rate. The source calculates each original
license row's cash,30% deduction, NMI, target, previously recognized amount and
delta. Revised old525/1050 less original recognized455/910 gives catch-up210.
Current262.50 plus catch-up recognizes472.50. Old original issued1365 and actual
paid1310 remain distinct: issued arrears55 plus unissued472.50 gives unpaid527.50.
This is neither a new issue nor an instruction to disburse money.

Every original Q1/Q2/Q3 view retains its own as-of Date, exact exclusive Instant
cutoff, source-case identity, receipt coverage and approved recognition finding.
Q1 knows neither its later issue nor payment. Q2 knows the Q1 issue455/payment400;
Q3 knows both original issues/payments. Complete populations independently
enumerate license cash, box metrics, issue IDs, bank disbursements and payment
applications with source totals. Explicit complete-zero CB and adjustment
populations differ from missing evidence. Unknown completeness blocks financial
outputs/state with `payment_evidence_status=no_event_supplied` before atomic
publication; no paid0 is manufactured.

The preview is a strict known prefix through September9, with September10
exclusive cutoff. It excludes the future87m trigger, calculates candidate227.50
at.065, recognizes0 and retains finalized recognized1365. Its canonical status
is `provisional`, source comparison status is `preview`, and closing state is
empty. It cannot finalize or supply a successor's consumable state.

## Physical state and original lineage

The unissued interface pins `merchandising-original-json/1` explicitly in the
structured quantity. Native typed inputs retain every required financial,
scope, evidence, authority and chronology field. The mechanical adapter also
serializes each original complete record to canonical JSON Text, preserving
opaque original IDs, category, evidence references and exact numeric/timestamp
lexemes. It asserts original JSON and typed transport round trips. This does
not supply any threshold, selected box, rate, recognition or balance answer.

SPL validates typed original records, uses thin projections for repeated
financial loops, and reconstructs each material previous/current raw-source
state only after replay. It selects that snapshot's original cutoff/as-of and
processed periods. Original complete records are retained as
`{category,id,record}` Text envelopes in state; `neutral_state` mechanically
restores them. Terms/cost/qualification/CB original record Text is pinned too.
Incoming original source, recognized rows, recognition history, policy/research
and original accounting balances must equal the independent source replay.
Changing old original facts or forging old recognition cannot create a new base.

Transient derived receipt/view/issue row IDs reuse already validated unique
original identities. They preserve all material fields. Mechanical restoration
removes these duplicate helper IDs; financial identity remains the original
receipt/recognition/issue. Actual canonical predecessors carry the wrapper's
real `prior_result_ref` in addition to the supplied neutral prior summary.
Supplied-history openings are explicitly labeled; they do not fabricate a
canonical predecessor or cryptographic authentication.

Original evidence rows receive transient integer positions solely to accelerate
lookup. The adapter associates a fact with a position using its original
`evidence_ref` only; it never selects scope, date, kind or approval. SPL validates
all original evidence IDs, slot uniqueness/range, exact selected original ID,
scope, kind and each applicable current/historical cutoff. Slot0 is valid.
Slots are neither economic identities nor state keys; original evidence order
may renumber them without changing restored financial/original-state results.
Raw physical-binding tests bypass the adapter for unknown/misbound/duplicate/
missing/out-of-range slots and unused bad rows. A direct native binding bypasses
descriptor uniqueness to observe duplicate original-ID rejection in SPL itself.

The earlier draft repeated broad raw typed records through intermediate states
and failed publication despite matching financial results. Source factoring,
raw state envelopes and thin typed projections change the program, physical
state and trace. Old/new reference controls compare all normalized emissions
and complete restored original state for baseline, preview and Q1/Q2/Q4. They
do not establish typed-wire or trace identity. Original record content stays at
the validated input and snapshot state boundaries; duplicate old raw-table
operand observations are not an invariant of the changed program.

## Reproduction and limits

Use the pinned project Python and Lean toolchain. Register deliberately with:

```powershell
python -m cases.merchandising-reprice.build_modules
python -m unittest Tests.test_merchandising_reprice_oracle Tests.test_merchandising_reprice_modules -v
```

The generic `compare` path executes the reference, native IR and native-emitted
Lean paths. Selected native module methods separately run Python-emitted Lean.
Full material row/financial/snapshot/state values are compared to the independent
original-fact oracle. Native-IR observations are not emitted-target branch
coverage. Tests distinguish source-native invalid cases, canonical wrapper
rejections and mechanical transport errors. Actual serialized Q1ÃƒÆ’Ã‚Â¢ÃƒÂ¢Ã¢â€šÂ¬Ã‚Â ÃƒÂ¢Ã¢â€šÂ¬Ã¢â€žÂ¢Q2ÃƒÆ’Ã‚Â¢ÃƒÂ¢Ã¢â€šÂ¬Ã‚Â ÃƒÂ¢Ã¢â€šÂ¬Ã¢â€žÂ¢Q3ÃƒÆ’Ã‚Â¢ÃƒÂ¢Ã¢â€šÂ¬Ã‚Â ÃƒÂ¢Ã¢â€šÂ¬Ã¢â€žÂ¢Q4
carry must show catch-up210 once and Q4 new recognition0, with complete artifacts
validated by `load_completed_result`.

The current publication encoder writes complete `result.json` compactly while
keeping readable field/trace mirrors. Parsed values and all trace nodes remain;
the64MiB completed-result guard is unchanged. The fresh targeted h baseline
under0660/182/673 publishes41,187,283 bytes and its completed loader equals
the returned object.
This is a single baseline witness, not the combined cohort or a general capacity
guarantee. Historical pretty artifacts retain their original bytes.

The input profile is finite: at most8 periods/views,32 receipts,16 box records,
8 issues,32 bank disbursements and64 applications. Those input bounds do not
establish publication capacity for every admitted combination. The unchanged
completed-result cap is64MiB. Failed, running or partial output is not consumable.
Financial/reference runs and target comparisons alone do not establish a
successful completed audit publication.

Draft failures are retained under the external SPL artifacts root:
`merchandising-reprice-draft-native-a` (182,515,519-byte trace), `...-b`
(179,740,609), `...-c` (224,992,038), `...-d` (131,191,875),
`...-f` (86,989,285) and `...-g` (65,841,102). The result envelope
contains additional content/indentation, so g also exceeds the final-result cap.
`...-e` retains a blocked exact-integer transport-codec draft, corrected before
financial/native acceptance. The a/b/c/d/f/g attempts fail the unchanged publication cap and receive no
completed-state credit; e blocks on transport admission. They retain original source/descriptor,
bindings, native target, financial mirrors and running markers. Comparison
records under `...-a` distinguish exact original typed-state factoring from
later normalized raw-profile comparisons.

The selected source economics and synthetic recognition/booking assumptions
remain separately described in policy. Nonzero CB credits, decreasing/corrected
threshold histories, late historical receipt corrections, amended-old-period
recognition, extra funding interest conventions, reserves/withholding and bank
execution are not inferred. No professional approval or vendor parity is claimed.

The first frozen acceptance attempt, `merchandising-reprice-checks-84046c1c`,
retains a valid completed native baseline but fails before running the39-method
cohort: its separate Python-emitted Unit-closure driver exceeds the unchanged
180-second timeout. Sources/core stay stable; elapsed206.583152s. The driver and
failure are preserved. A separately verified shared Python-emitter memoization
repair regenerates a fresh driver from the retained original baseline facts:
`merchandising-reprice-python-followup-331b80a7` passes in11.592059s with exact
values/errors/closing agreement. The old driver is untouched. This followup uses
compiler20ea52ba/modulea5165f5d/runtime673bb0fe and is not the full acceptance.

## Final frozen acceptance

`merchandising-reprice-checks-cf96f81d/verification.json` passes all39 methods
(26 independent oracle plus13 module), with zero failures, errors or skips.
The test process takes811.007496 seconds; the actual six-bundle phase takes
213.527360 seconds; total1024.575564 seconds. All55 watched source pins and
compiler/module/runtime identities remain unchanged throughout. The records
retain exact source snapshots, original neutral inputs, canonical bindings,
full native IR/audit and emitted sources, validated completion manifests and
separate Python-emitter drivers/outcomes.

The final source uses compiler
`20ea52ba37b7d84b4d5d7ed62c9c38b44a928cf1ffc2287f2bec358bda31c260`,
module`a5165f5db8a42a7365afc553e6e518913ded0065389c1e0a717dd197cd6d412a`
and runtime
`673bb0fe936c48a60c1cf5a1a265fb1d1f9f3cd432f380ee9b3011b7729dace9`.
The source/adapter/test/descriptor/template bytes still match that snapshot;
this final evidence paragraph is a later documentation-only addition.

| Completed bundle | Result bytes | Material outcome |
| --- | ---: | --- |
| Baseline Q3, supplied-history opening | 41,187,283 | Catch-up210, new472.50, paid1310, old arrears55, unpaid527.50 |
| Actual Q1 | 10,147,582 | Recognized455; explicitly complete-empty known issues/payments |
| Actual Q2 | 24,742,448 | New910; known old issue455/payment400 |
| Actual Q3 | 41,925,067 | Actual serialized Q2 predecessor; catch-up210 once |
| Actual Q4 | 55,194,678 | Actual serialized Q3 predecessor; catch-up0/new recognition0 |
| Partial preview | 32,985,527 | Candidate227.50, recognized0, provisional, no closing state |

Q4's complete result leaves11,914,186 bytes below the unchanged67,108,864-byte
limit. This is an observed four-period publication witness; the8-period input
bound is not a general publication-capacity guarantee. The preview is a
completed review artifact with no consumable financial closing state.

`merchandising-reprice-carry-purity-5970c3c9/verification.json` separately passes
three pure mechanical handoff checks in6.439359 seconds. Each calls the exact
frozen helper using actual completed predecessor files, verifies the full
previous result remains unchanged, and reloads/compares its stored completed
artifact **after** constructing the successor. Input cells equal the actual
serialized cells minus only output-only`movement`; quantity, key, boundary and
real`prior_result_ref` remain intact. This additional check does not mutate the
frozen case files or claim another native execution.

The intermediate`merchandising-reprice-checks-9e70aa8b` retains its honest
68.245167-second mechanical-helper failure: baseline/Q1 complete, Q2 rejected
an output-only`movement` field passed back as input, and the39-method test group
never started. The corrected final run uses the actual JSON-round-tripped cells
and removes that field from a separate copy. All prior failures remain retained;
none receive retrospective full-cohort or successor-state credit.
