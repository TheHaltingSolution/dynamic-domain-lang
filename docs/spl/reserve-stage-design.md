# Independent C09 stage, cap and schedule controls

This design supplies finite independent original-fact controls for
`B-C09-STAGES` and the generic stage/finite-release obligations associated with
`C09.PAYMENT_HOLDBACK`, `C09.VINTAGE_MOVEMENTS` and
`C09.FINITE_RELEASE_SCHEDULE`. Its synthetic basis-stage comparator also informs
the stage distinction without completing `C09.GENIUS_BASIS_RESERVE` source semantics.
It adds no compiler capability or native evidence.
The accepted Genius source profile remains partial; its signed excess-return
and after-liquidation corrections are separate open interpretations.

Read [the selected synthetic policy](../../cases/reserve-stages/policy.md) for
the equations and source limitations, [original casepack](../../cases/reserve-stages/neutral.json),
[independent oracle](../../oracles/reserve_stages.py) and
[executable controls](../../Tests/test_reserve_stage_oracle.py). No expected
financial values were derived from an existing reserve implementation, compiler,
financial runtime, adapter or previous financial oracle. The independent code
uses only `copy`, `datetime`, `fractions`, `calendar` and `re`; it reads no files
and consults no clock. Tests load the original casepack and use exact Fraction
expectations from its declared original terms.

## API and original data

`reserve_stages(data)` returns computed values with `Fraction` numbers and a
JSON-compatible closing state. `exact_json(result)` serializes computed
Fractions as canonical rational strings while preserving raw original numeric
and timestamp lexemes. Invalid/incomplete inputs raise `ReserveStageOracleError`
without returning numeric output or changing the input.

The top-level neutral input has `schema_version=reserve-stages-neutral/1`,
`scope`, selected `policy`, original `terms`, `registry_evidence`, `opening_state`,
optional `prior_result`, and one original frame. Scope contains agreement,
participant, pool, asset, currency and purpose; each original row carries that
same scope. Selected policy is the exact explicit dictionary returned by
`policy(stage)`. There is no external policy registration/authenticity claim.
Ordinary carry pins the complete supplied context through exact predecessor
state comparison; no policy migration or revision-history service is provided.

Original terms carry ID/version, approval Date/status, effective interval,
observation, source/evidence references, reserve rate, participation share,
fixed fee, retained cap, reserve measure, calendar mode and release schedule.
An original schedule rule supplies ID, calendar-month offset and kind. Its first
optional rule supplies a fraction of original actual addition; its final rule
releases all remaining. No precomputed deadline, addition or earnings is input.

Each frame supplies:

| Original field | Meaning |
| --- | --- |
| `case_id`, `period`, `as_of`, `cutoff` | Unique original checkpoint identity, half-open Date interval, complete last Date, exclusive exact UTC observation boundary |
| `receipts` | ID/original reference, original gross, event Date, same-stage sequence, scope/source/evidence/observation |
| `elections` | Original receipt and vintage IDs, affirmative/negative election, approval Date/status, original event Date and provenance |
| `applications` | Original ID/reference, designated vintage/measure, amount, Date/sequence, linked authority and provenance |
| `authorities` | Original authority linked to one application/vintage/measure, approval Date/status and provenance |
| `population` | Complete original row-ID sets, gross/application totals, original period, completeness and provenance |
| `evidence` | Original ID, genuine scope, kind, approval, observation and source reference, including all unused rows |

Original amounts are nonnegative decimal strings or reduced rational objects
`{"numerator":"1","denominator":"3"}`. Floats, negative values, scientific
notation and unreduced rational objects reject. Ratios lie within0..1. Original
IDs permit all nonempty Unicode scalar strings, including delimiters and NUL;
there is no financial identity constructed by concatenating user strings.
Fee identities and release identities remain explicit ordered components.

## Independent calculation and material outputs

The oracle independently orders the finite original Dates and supplied stage
sequences. It derives raw and capped additions, current cap room, fee consumption,
producer/nonparticipant amounts, authorized vintage applications, calendar
deadlines, tranche quotas, unused releases and full closing state. Every original
receipt is evaluated even when it elects no reserve; every evidence row is
validated even when unused. The two financial purposes are separate ledgers,
not a conversion of gross basis into producer earnings.

The result exposes current/cumulative gross, fee, producer, nonparticipant,
applications, additions and releases; opening/closing reserve; per-receipt raw
addition/cap-room/clipping and allocation; complete original application and
availability; per-release original addition/quota/deadline/available balance,
producer/nonparticipant split and zero fee; all vintages and fee consumption
keys. Every vintage satisfies `original addition = applied + released + available`.
Every period satisfies:

```
gross + opening reserve = fee + producer + nonparticipant + applications + closing reserve
```

The cumulative bridge has zero genesis opening. Outputs explicitly identify
unissued calculations, payment evidence outside the profile, no bank movement,
no sourced clearance inferred, and unconditional supplied generic release terms.
Original `-00:00` observations retain their raw lexeme and an explicit unknown
local-offset path; UTC is known and no local calendar inference follows.

The six original scenarios give16 actual serialized checkpoint invocations:
two two-period stage ledgers, two three-period vintage ledgers and two
three-period tranche ledgers. Test discriminators include:

- Fixed fee10 and gross100: current producer35 versus36; completed producer45,
  nonparticipant45, fee10 in both ledgers. Fee0 gives40/40 and cannot by itself
  distinguish stage policy.
- Original V1 addition12 less application7 less due release5 is0 while new V2
  remains20. A second V1 application8 cannot borrow V2 funds.
- V1 opening12 and V2 gross105: raw basis addition21; cap32/33 clips to20/21,
  changing receipt producer37.50/37. Post-earnings counterpart uses gross220,
  earnings105, producer85/84. Same-day later release cannot increase earlier room.
- Original addition12, application4, +1month quarter-original release3,
  application2, +3month remaining release3; the remaining-basis counterfactual
  would release2 at the first rule. A capped-original and a clipped-unused
  control distinguish original actual addition from raw candidate and availability.
- Exact fractional stage differences, zero cap/rate/election, zero gross/fee,
  month-end clamp/reject, strict cutoff equality, submicrosecond observations,
  signed-offset normalization and preserved unknown local offset.
- Complete-population/authority/scope failures, unsupported fee funding and
  post-liquidation applications, duplicate originals, context/state/history
  mutation, missing predecessor and unresolved sequence ties.

## Exact serialized predecessor and knowledge

Genesis has exactly the declared first boundary and empty history. Each
successor receives a JSON round-trip of the actual previous returned closing
state with its matching case/period/opaque reference summary. Full original
frames and computed results are replayed from genesis; every historical result,
vintage, processed tranche, cumulative meter, consumed identity and fee key
must reconcile exactly. The predecessor period must match the original preceding
period, including its start, and end at the current start. Prior result objects
and caller input remain unchanged.

The oracle uses each original frame's own cutoff. Static original terms and all
registry evidence must also precede the minimum applicable cutoff across the
prefix; there is no hidden monotone-cutoff assumption. Approvals and event Date
admission remain distinct from observation admission. Exact UTC comparison does
not require constructing next-midnight beyond year9999. Physical row permutations
with resolved sequence preserve computed economics, while original physical order
is deliberately retained in the raw state snapshots. Thus different raw order
is not claimed to produce byte-identical state.

The result reference is supplied provenance metadata. The stateless oracle
does not prove original-source authenticity, cryptographically authenticate
state, register terms externally or run a distributed state service. A later
canonical module must use the generic validated actual predecessor and preserve
these distinctions.

## Remaining implementation and sourced obligations

A different author must implement financial formulas, cap clipping, ordering,
vintage attribution, calendar deadlines, tranche release, fee consumption and
all material original/state intermediates in SPL. An adapter may transport and
validate original typed/raw correspondence; it may not supply solved additions,
deadlines, cap room, earnings, release quotas or allocation. Canonical wrapper
admission, native IR, native emitted, Python emitted, complete publication and
actual serialized native successors need their own bounded evidence. This
independent oracle does not close any of those backend axes.

This finite policy permits4 frames/4 vintages,8 rows per ordinary table,
32 evidence rows per frame or registry and1..2 release rules with1..24-month
offsets. It covers complete checkpoints. It defines no partial-history preview
policy, cap migration, multiple fee bands, fee deficit carry, rounding, FX or
bank settlement. Generic due releases are unconditional under the supplied
terms; missing source claim-active/distributor evidence is not clearance.
Genius source excess returns/after-liquidation signed Net Receipts and resulting
fee/allocation correction, source caps, active claims and reasonable release lag
remain separate open source questions.

## Resource basis

The engineering inventory and scope were read from
[completion backlog](completion-backlog.json), [atomic variants](c1-atomic-variants.json),
[RR04/LD03 integration](rr04-ld03-integration.md), the existing
[vintage policy](../../cases/mechanisms/reserve-vintage-policy.md), and the
[accepted partial Genius policy](../../cases/basis-reserves/policy.md) and
[design](basis-reserve-design.md). Existing executable financial implementations
and financial oracles were not consulted for the new expectations.

The external review documents are indexed by the integration document:
`SPL_RR04_Completion_Decisions.md`, SHA256
`c93433744619545c6f78eab3b50397c6c4765436d8a2c7e5b7fba18ba2c6fa2f`,
and `SPL_LD03_Completion_Review.md`, SHA256
`658740285501e66f39c44f31f4ada0f86d4d8ff35f8245e03fd3cb3e5cf42712`.
Their source-specific Genius/Pacific Gold assumptions are not relabeled as this
synthetic USD stage/cap policy.
