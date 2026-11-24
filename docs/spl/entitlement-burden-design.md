# Independent original-fact entitlement burden controls

The [neutral fixture](../../cases/entitlement-burdens/neutral.json) and
[selected policy](../../cases/entitlement-burdens/policy.md) implement the finite
oracle portion of `B-C10-BURDEN`. This precedes a different author's SPL source
and coordinator integration. Existing exact arithmetic, records/maps and finite
folds suffice; no new financial primitive or currency capability is presumed.

The adopted evidence is [LD03§7](C:/Projects/Film_TV_participation_dynamic_DSL/ResearchAgent/documents/SPL_LD03_Completion_Review.md:390),
the backlog's `B-C10-BURDEN`, and the [existing transfer scope lessons](transfers-design.md).
The fixture pins LD03 and RR04 bytes; RR04 has no C10-specific rule. Approval
flags and operating details are supplied synthetic research assumptions, not
legal/accounting approval or verified upstream truth.

The API is `oracles.contract_burdens.contract_burdens(data)`, returning exact
`Fraction` intermediates and a structured closing state. `exact_json` converts
fractions to integer/rational strings for serialized oracle carry.
`ContractBurdenOracleError` raises a stable `BURDEN_...` diagnostic before any
result/state is returned. The module imports only `copy`, `datetime`, `fractions`
and `re`; it reads neither SPL nor compiler/projection calculation code.

The top-level run schema is:

```text
schema_version = entitlement-burdens-neutral/1
case_id, coordinator{id,currency,purpose}, period{start,end}, as_of, cutoff
policy, research{ld03_sha256,rr04_sha256,review_locator}
accounts[], terms[], receipts[], authorizations[], requests[]
payments[], applications[], receipt_populations[], payment_populations[], evidence[]
opening_state, prior_result?
```

Every endpoint scope is `{agreement_id,participant_id,pool_id,asset_id,currency}`.
Accounts have original ID/scope/source/evidence/observation. Terms preserve
original ID/account/scope/share/effective/approval Date and original contract-line
reference. Receipts preserve original ID/account/scope/amount/term reference,
economic Date, observation, original receipt-line reference and a distinct
participation entitlement-line identity. That identity names the original
measurement; no solved entitlement amount is supplied. Each receipt contributes
`original_amount × original_share`. Every account's complete population states
original receipt IDs/gross total and period, including explicit empty views.

Authorities retain original ID/line, claimant/burdened accounts and both genuine
scopes, purpose, named basis, burden rate, minimum basis, cumulative cap,
sequence, effective interval and approved/recorded Dates. Requests retain their
own original ID/line and measurement label, exact authority/endpoints/scopes,
complete current claimant receipt IDs, final recognition Date and observation.
Requested/permitted/applied amounts are derived, never input answers.

Payments retain original amount, actual paid Instant, account/scope, participation
settlement purpose and unique original bank-statement line. Separate approved
applications link a payment to an original receipt's participation line, with
their original amount/Date/source/evidence. Every payment must be fully applied;
the sum applied to each participation line cannot exceed its independently
derived entitlement. Thus paid101 against gross200/participation100 rejects.
The linked paid60 comparator measures18, independently of accrued100. Whole
payment artifacts without distinct original line suffixes cannot evade aliases.

Complete payment populations pin period, account, payment/application IDs and
actual total. Evidence has its own ID/coordinator/account coverage/kind/approval/
exact observation/source. Partial cash evidence is not a known numeric balance.
When no population/events are supplied, the accrued method records `actual_paid`
as null and `no_event_supplied`; the paid method cannot finalize that unknown.
An approved complete-empty view records actual paid0. No claimant payment or
cash movement is inferred from the burden.

The baseline independently derives claimant gross200/share.5/accrued100 and
other gross400/share.5/accrued200. A30% accrued-basis burden gives requested30,
cap remaining45, applied30, target170 and cap remaining15. Claimant remains100;
actual source payment60 remains60. Combined entitlement300 becomes270, which
satisfies `sum(adjusted)=sum(original)-sum(applied burdens)`. It does not satisfy
the conserved-transfer equation. In the paid variant basis60 gives18 and182.
Fractional original basis2/3 gives participation1/3 and exact burden1/10, without
a cent rule. Minimum100 includes basis100;100.0000000001 excludes it.

Static account/term/authority/evidence registries are pinned for the whole
bounded ledger. Genesis is zero at or before each authority's inception; a late
bootstrap cannot silently reset an original cap. Subsequent runs retain all
original raw period facts and their individual historical cutoffs. The oracle
replays that history from zero, rederives every prior accrual/payment/application/
burden and cap, and compares both stored historical results and the supplied
opening. Numeric opening cap consumption is never trusted as its own proof.
Changing a cap/rate/scope/evidence registry is an unsupported amendment/reset.

Closing `entitlement-burden-state/1` contains coordinator, policy, review pins,
the original registry, boundary, origin, `source_case_id`, raw history/results,
cap limits/consumed/remaining and consumed original identities/semantic keys.
An actual adjacent predecessor supplies
`{source_case_id,period,closing_state,result_ref?}`. The optional external result
reference is provenance, not an oracle-computed canonical digest. Oracle case
identity is never claimed to be `result@sha256:...`.

The three serialized periods independently demonstrate cap45 consumption
30→15→0, target170→185→200, no re-earning old receipt history and no residual
cap-excess carry. A DAG witness uses original B200 for its next burden20 after
B is adjusted170; using17 would incorrectly introduce feedback. All failures
are atomic oracle exceptions. Deterministic immutable replay is not an external
transaction service or a defense against a maliciously fabricated predecessor.

Original IDs are nonempty valid Unicode Text. The oracle does not trim, casefold,
normalize or impose declared `Id<Kind>` ASCII rules on them. Distinct composed
and decomposed originals remain distinct. A later canonical source adapter must
respect its actual NFC/ID transport boundary and retain original raw lexemes plus
any explicitly approved external mapping; these controls do not claim native
acceptance of decomposed canonical JSON or invent a silent normalization policy.
Exact offset/subsecond lexemes are retained while comparisons use exact UTC
rationals. Physical input permutation preserves financial results; raw audit
history keeps the original supplied row order.

The coordinator is execution metadata, not a replacement agreement or a grant
of authority across all pools. Future canonical integration must deliberately
validate genuine scopes and authority edges, rather than disguising other
contracts as ordinary participants of one outer agreement. Native/reference/
emitted source equivalence, operational atomic publication and generic cross-
contract type guarantees require separate implementation/acceptance evidence.
This author implements no SPL against this oracle.

External frozen verification retains the five owned LF files, unchanged package
initializer, exact supplied-review snapshots/pins, source-independent imports,
hand controls and actual three-period serialized results. It establishes the
bounded independent oracle only, with no native execution or professional
approval claim.
