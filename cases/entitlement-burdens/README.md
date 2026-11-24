# Scoped current-period entitlement burdens

This SPL source implements the two selected synthetic methods in the immutable
[policy](policy.md) over [original facts](neutral.json), with controls from the
separately authored [oracle/design](../../docs/spl/entitlement-burden-design.md).
This is a current-period entitlement subtraction, with no claimant credit or
bank movement created. Conserved transfers are a separate method.

Original claimant receipts200 at approved share.5 derive participation100.
Original burdened receipts400 at share.5 derive participation200. The accrued
method measures30% of original claimant participation100, giving30 applied and
burdened170. Claimant participation remains100 and supplied actual payment60
remains60. The linked-paid method measures the distinct actual participation
payment60, giving18 applied and burdened182. It never measures gross200 or
uses the adjusted claimant balance as a new basis.

For each approved authority, SPL derives eligibility at `basis >= minimum`,
requested burden, original cap remaining, permitted amount, cap excess and
current target before/after. The cap applies before the availability check;
insufficient target entitlement then rejects the whole calculation. Cap excess
is retained as a reported amount without later carry. The request's canonical
measurement identity is consumed even if applied0. Explicit original sequence
orders requests. All declared authority edges, including unused edges, must
form a DAG. In A→B→C, B's original200 measures its next20 burden even after B
was adjusted to170; adjusted170 does not produce17 feedback.

The three-period45 cap control applies30,15,0 against fresh current entitlement,
giving target170,185,200. Raw history is replayed from zero, with each original
period/cutoff. Static accounts, terms, authorities and their referenced evidence
are pinned; cap resets and amendments require a different selected policy.
Original receipts, participation lines, payments, applications, requests and
semantic authority/scope/period/method keys are checked across the whole replay.
The output reconciliation is original total minus applied burdens, not transfer
conservation. No withholding or bank-payment order is inferred.

## Scope and transport boundaries

The generic wrapper has one outer execution scope. Its fixed legacy agreement
slot`entitlement-burden-execution`, reader and pool are explicitly coordinator
metadata, not a real financial agreement, participant or cross-contract grant.
Canonical descriptor constraints validate those fixed outer labels. Native SPL
separately checks each original agreement/participant/pool/asset/USD inner scope,
term and approved cross-agreement authority edge. No endpoint is silently moved
under the coordinator's financial agreement. Generic cross-contract type safety,
source custody and professional approval are not claimed.

Physical profile`entitlement-burdens-original-json/5` uses the uniform identity
codec`unicode-utf8-hex/1`. Every arbitrary original identity/reference and real
scope Text is strict UTF-8 encoded as lowercase even-length hex. This is a
reversible physical representation, preserving Unicode scalar lexical order,
embedded delimiters, control characters, and composed/decomposed distinctions.
It does not trim, normalize, casefold or invent economic identities. Strict
restoration rejects malformed/overlong UTF-8, surrogates and noncanonical hex.
USD currency, policy enums, dates and exact numeric semantics remain unencoded.
The earlier six-hex-scalar, raw-hot-row, combined-container and unindexed-port drafts use
different profiles and are rejected; there is no silent state migration.

Full original records are also retained as ASCII-escaped JSON Text, including
exact numeric/timestamp lexemes and original row order. The adapter validates
physical shape, exact values, UTC date transport and reversible typed/raw
correspondence, including restored predecessor records. SPL receives typed
financial fields and derives every financial answer. It validates original
references, scope, evidence kind/approval, effective dates and strict observation
cutoffs, and pins full original history at the input/state boundaries. Parallel
original-ID/raw-record tables and the complete original-frame JSON retain every
original in the dedicated`original_frames` port. The`frames` port contains
typed execution fields only; the adapter projects fields without selecting or
omitting original rows. Hot typed rows/containers carry no raw JSON. Native
checks bind original case-ID order and raw-table ID
populations (and original evidence slots) to the typed rows. SPL does
not parse JSON or authenticate an external original. Arbitrary native bindings
that bypass the mechanical adapter do not obtain an original↔physical codec
proof; native tampering tests separately check reference/slot/scope/financial
predicates. No adapter rejection is counted as native execution.

Evidence Int slots enumerate original rows and associate each fact by its
original evidence reference only. Native SPL validates every evidence row,
including unused rows, and checks slot range/uniqueness plus exact original ID,
kind, endpoint coverage, approval and chronology before using an Int-keyed map.
Slot0 is valid. Slots are transient lookup metadata, not authority or state IDs.
Thin validation/financial projections retain full originals at explicit
input/snapshot boundaries. Source changes alter the program and audit layout;
equal financial/state outcomes do not imply identical traces.

Every account needs an approved complete original receipt population, including
an explicit empty view for known gross/accrual0. Paid-basis calculation requires
a complete payment/application population. Original payments must be fully
applied to original current participation lines; applied amounts cannot exceed
derived participation100 even if gross receipts were200. Missing paid views
remain nullable unknown in the accrued method and block the paid method. Only a
complete empty view supports actual paid0. Failed/unknown calculations expose no
financial result or consumable state. Blocked metadata is applied by the generic
publication API before finalization.

Actual successors JSON-round-trip previous validated closing cells, remove only
the output-only`movement` field from a separate copy, and retain quantity, key,
boundary and real canonical`prior_result_ref`. The previous returned object and
completed stored bundle remain unchanged after constructing a successor. This
is provenance and deterministic replay, not cryptographic source authentication
or an external transaction service. Preview is provisional review of the same
complete current-period calculation, with no consumable closing state.

## Verification and bounded scope

```powershell
python -m cases.entitlement-burdens.build_modules
python -m unittest Tests.test_contract_burden_oracle Tests.test_contract_burden_modules -v
```

`compare` checks reference evaluation, native IR and native-emitted Lean. Module
controls explicitly execute separately Python-emitted Lean and compare full
values/errors/state. Every material account/receipt/application/burden/order/
cap/consumed/original-history/state field is checked against the independent
oracle. Reference-only methods retain their declared narrower execution scope.

Draft-a retains a failed64MiB publication attempt and93,391,388-byte pretty
trace with9,853 nodes. Profiled per-frame aliases and native-validated Int evidence
lookup reduced draft-b to7,981 nodes; its baseline completed at46,867,106 bytes.
Draft-b remains valid historical evidence under its original six-hex program and
physical profile. Further source narrowing and the new lossless UTF-8 codec
change the source/physical layout. Full normalized financial and original-state
comparison is required; final native acceptance is pending.

The next frozen attempt`entitlement-burdens-checks-ba146974` retained complete
Q1/Q2 bundles at31,689,413 and66,177,916 bytes. Q2 had930,948 bytes remaining
under64MiB. Q3 then failed publication; its144,724,055-byte pretty trace has
24,794 nodes. The43-method cohort was not executed and that attempt has no
Q3/preview/full-cohort acceptance credit. Its profile identifies13.97MB in typed
frame construction while each field still observes a redundant raw row payload.
The current source separates those raw records and caches total typed field
reads. Earlier artifacts retain their original source/profile identities.

The subsequent`entitlement-burdens-checks-b3c89de3` also remains failed:
Q1 completed at35,018,516 bytes, then Q2 failed publication. Its104,786,172-byte
pretty Q2 trace has18,166 nodes. The full43-method cohort was not executed.
The measured typed-frame projection alone contributes8.47MB over two periods,
because its parent still contains both raw and typed data. Profile/4 moves
the raw container to its own input port, preserving the exact normalized
financial/original-state comparison obligation and rejecting prior draft shapes.

The finite profile allows four accounts, eight authorities/requests,64 rows per
array and four total replayed periods. These bounds do not guarantee publication
capacity for every admitted combination. The64MiB guard and180s timeout remain
unchanged; no observations may be truncated to manufacture completion.
Amendments/cap resets, old-period payment reopening, conserved transfers,
bank settlement/refunds, issued/unpaid obligations, signed losses and FX remain
outside this selected synthetic profile.

Profile/4's`entitlement-burdens-checks-100b912d` retains completed Q1/Q2 bundles
at27,895,598 and59,700,269 bytes under the later unit-integrated compiler.
Q3 failed publication at the unchanged limit; its135,844,999-byte pretty trace
has25,564 nodes. No Q3/preview/full43-method credit is claimed for that attempt.
Its profile identifies two repeated whole-frame associations at3.59MB each and
raw-history lookup at3.36MB. Profile/5 indexes those associations by the original
declared period start using existing Date-keyed maps, after native positive/
adjacent-period validation. It retains exact source-case ID and full-period
equality, raw-table populations and original order. The adapter copies original
period metadata only; no period, scope or financial answer is selected for it.
Native evidence membership also uses cached original Text account IDs rather
than repeatedly observing whole account records. Join headers contain only
original ID/slot populations, with complete typed financial rows retained in
the execution frames. Full original financial/history records are assembled
once, then each reconstructed state takes only its original period prefix;
current/future records cannot enter the predecessor state. Material states
are indexed by their original boundaries rather than scanned repeatedly.
These are program/layout
changes, with complete outcome/state equivalence still required.

## Explicit compact transport qualification

The adapter now accepts an optional `audit_profile` keyword. Its default stays
`array-v1`; compact publication is selected explicitly:

```python
result = run_entitlement_burden_package(
    reviewed_package, registry_root, backend="compare",
    artifact_dir=output_directory, audit_profile="compact-v2")
```

The generic CLI provides the same explicit selection after deliberate binding:

```powershell
python -m spl_compiler module-bind cases/entitlement-burdens/canonical-package.json reviewed.json
python -m spl_compiler module-run reviewed.json --registry . --output review-bundle --backend compare --audit-profile compact-v2
```

Use `load_completed_audited_result` for completed v2 bundles and
`carry_audited_state` for actual successor cells. The old v1 loader deliberately
rejects v2. Existing issued v1 cells can be obtained through the separately
versioned `load_completed_v1_carry_receipt`; that partial extraction is not a
canonical result or a new source-calculation proof.

The native test helper explicitly selects v2 and allocates an owned publication
directory for every compare invocation. Reference-only tests retain v1. Its
loader selects only recognized completion versions. Independently Python-emitted
Lean is the exact `emit_module` output, compiled using pinned generic flags under
the separate1 GiB/180-second compiler profile, then executed under256 MiB/60s.
Raw-binding native-only negatives use the bounded native audit/reader path.
No backend is replaced with an oracle answer, and no financial input or trace
is omitted to obtain completion.

This is a new transport-qualified adapter/test revision. The economic SPL,
oracle, policy, original facts and physical`/5` layout remain unchanged. Earlier
failed campaigns and helper/receipt records retain their original hashes.
The import-only candidate's `c10-compact-qualified-20261123-b` retained complete
fresh Q1/Q2/Q3, preview and actual old-v1Q2-to-v2Q3 controls. Its full43-method
cohort **failed** one negative fixture before native admission: the helper-only
`source_observed_at` field was appended directly to a `/5` typed evidence row.
The record remains failed and unchanged. The corrected negative uses the normal
execution-field projection, preserving `approved=False` and requiring native
origin plus `BURDEN_EVIDENCE_APPROVAL_CUTOFF`.

## Prepared execution boundary

Call `run_entitlement_burden_package` for original-record transport checks.
Before execution, the wrapper mechanically projects **all** raw frames and their
ordered tables again, checks them against the typed frames, and checks supplied
opening, actual state cell, history and predecessor transport. It derives no
participation, burden, payment, cap or state financial answer. Original facts
must still satisfy the independent SPL predicates. The generic `module-run` CLI
and `run_module_package` API accept already prepared typed inputs; they do not
perform this case-specific raw/typed correspondence check. Their caller owns
that preparation boundary. Neither API authenticates supplied original JSON.

`c10-wrapper-boundary-20261123-a` preserves the pre-fix counterexample: changing
only typed claimant receipt/population amounts200 to300, with original raw bytes
and actual opening unchanged, produced claimant accrual150 and adjusted target155
instead of100 and170. The revised wrapper returns only empty blocked metadata
with `BURDEN_PREPARED_PACKAGE_MISMATCH`. Both explicitly selected publication
formats invalidate stale completion and publish that blocked outcome atomically;
an interruption/publication failure leaves no consumable completion. Caller
packages and previously owned invocation files remain unchanged.

Tests of intentionally corrupted typed bindings use the generic API explicitly
to retain native source-validation credit; separate wrapper tests require
preflight rejection and claim no native calculation. The forged-cap discriminator
retains both boundary rejection and independent generic native/source replay.
New frozen acceptance of this wrapper/test revision is still pending. The
economic SPL, oracle, policy, original fixtures and physical `/5` layout remain
unchanged; neither failed record is repinned as a success.
