# Synthetic reserve stages, caps and finite releases

Policy `SYNTHETIC-RESERVE-STAGES-01`, revision `1`, is an explicitly supplied
research assumption for the remaining generic C09 stage/cap/schedule controls.
It is not an interpretation or professional approval of a source agreement.
The original casepack is [neutral.json](neutral.json); its original receipts,
elections, applications, authorities, complete populations and terms drive the
independent calculation. Additions, earned amounts and release dates are outputs.

## Two purposes and financial stages

Each ledger has one genuine agreement, participant, pool, asset, currency and
purpose. Currency is USD. The two purposes have distinct economic measures even
though both use USD amounts:

| Selected stage | Required purpose | Reserve measure |
| --- | --- | --- |
| `basis_reserve` | `synthetic_gross_basis_reserve` | `gross_basis_USD` |
| `producer_holdback` | `synthetic_producer_entitlement_holdback` | `producer_entitlement_USD` |

Let original receipt gross be `G`, supplied fixed fee `F`, participation share
`s`, reserve rate `r`, current retained balance of the same purpose `R`, and
supplied retained cap `C`. The fixed fee is charged once per original receipt,
including a receipt with a false reserve election. Its consumption identity is
the tuple `(original term ID, original receipt reference)`. This fixture has no
fee floor, fee carry, tier or fee-on-release. `G < F`, or insufficient gross
remaining after a basis addition to fund `F`, requires a different policy and
rejects the entire calculation.

For an affirmative election:

```
E = (G - F) * s
rawAddition = G*r                         [basis reserve]
rawAddition = E*r                         [producer holdback]
room = max(C - R, 0)
addition = min(rawAddition, room)
unretainedCurrent = rawAddition - addition

producer = (G - addition - F)*s            [basis reserve]
nonparticipant = (G - addition - F)*(1-s)  [basis reserve]
producer = E - addition                   [producer holdback]
nonparticipant = (G - F)*(1-s)             [producer holdback]
```

A false election makes `rawAddition = addition = 0`. Cap clipping leaves the
unretained amount in the current basis or producer earnings. It does not reject
an otherwise valid over-cap receipt. Cap, fee, schedule and all original terms
remain pinned across ordinary carry; cap migration is outside this profile.

The main discriminator uses original `G=100`, `F=10`, `s=1/2`, `r=1/5`:
basis addition20/current producer35/nonparticipant35 versus producer hold9/
current producer36/nonparticipant45. The declared nonlinear fixed fee makes the
stage difference material. With fee0 both current producer totals are40; that
commuting example alone cannot establish stage distinction. Fractional controls
also use original gross1/3 and fee1/10, giving current producer1/12 versus7/75.
All arithmetic is exact; no currency rounding is supplied in this profile.

## Original order and cap capacity

Within each original Date, the source policy is:

1. Original receipts and their elections in unique supplied receipt sequence.
2. Original applications in unique supplied application sequence.
3. Computed due releases in vintage ID and schedule order.

Dates are processed in increasing order. There is no inferred timestamp order
between these three declared stages. An unresolved same-Date sequence tie
rejects. A later same-day application or release does not retroactively free cap
capacity for an earlier receipt.

The cap boundary uses V1 opening12 and original V2 gross105, giving raw basis
addition21. Cap32 allows20 and current receipt producer37.50; cap33 allows21 and
producer37. With cap20, V2 addition is8 even though V1 later applies7 and
releases5 that Date. The corresponding post-earnings control uses original
gross220: earnings105, raw hold21, cap32/33 additions20/21 and current receipt
producer85/84. These are distinct original-basis examples, not unit casts.

## Vintage attribution and application authority

Every original receipt has exactly one approved election, establishing a unique
vintage. An application names one vintage, economic measure and separately
approved original authority linked to that application. The authority must be
observed by the application observation, its approval Date cannot follow its
observation or application Date, and the original vintage election must already
be known. Applications cannot borrow from another vintage or purpose. Receipt
IDs/references, election IDs, application IDs/references, authority IDs and fee
consumption are checked across the entire supplied history.

The three-checkpoint control establishes V1 addition12; the next checkpoint
establishes V2 addition20, then applies7 to V1 and releases its unused5:
`V1:12-7-5=0`, `V2:0+20=20`. A second V1 application8 after application7 rejects
because V1 has only5, while V2's20 remains unavailable to it. The basis ledger
uses original gross60 then100; the producer holdback ledger uses gross130 then
210 to establish the separately measured additions12 and20.

Each vintage must satisfy `originalAddition = applied + released + available`.
Original applications are assumed authorized uses of the designated retained
measure. They do not assert an actual cash settlement, paid refund or bank event.

## Supplied finite calendar schedule

The original term schedule contains one or two strictly increasing positive
calendar-month offsets, at most24. Deadlines derive from the original receipt
Date. The supplied calendar mode is `clamp_day` or `reject_invalid_day`; the
January31 control distinguishes February28 clamping from rejection.

The final rule is `all_remaining`. An optional first rule is
`fraction_of_original_addition`: its quota is the supplied fraction of the
**actual capped addition established for that vintage**, and its release is the
minimum of that quota and unused available balance. It is not a fraction of the
remaining balance or of the unclipped raw candidate. Zero releases still process
their rule exactly once. Final liquidation prevents further applications in
this selected profile; after-liquidation source reductions remain outside it.

The separate two-tranche control establishes12, applies4, and at +1month releases
`12*1/4=3` from available8. A remaining-basis quarter would release2 and is a
different policy. A later application2 leaves3; +3months releases all3:
`12 = applications6 + release3 + release3`. The single-final variant releases all
unused funds at +3months.

A basis release enters producer/nonparticipant allocation using the original
share and charges no second fee. A producer holdback release goes wholly to the
producer and charges neither a second fee nor a second participation share.
For original gross100, both completed stage examples reconcile fee10,
cumulative producer45 and nonparticipant45, with reserve0.

## Completeness, knowledge and serialized carry

The calculation uses complete adjacent half-open Date periods, each with as-of
Date equal to its last Date and a supplied exclusive UTC observation cutoff at
or after the end boundary. Each original event Date lies in its period. A
complete supplied population lists every receipt, election, application and
authority ID, original gross total and original application total. Its
observation follows the period end and all included original observations.
Missing, unknown or inconsistent population information blocks calculation.

Every row and every evidence row, including unused evidence, retains original
scope, source reference, approval and observation. Referenced evidence must have
the expected kind and be observed by its row. Static terms and registry evidence
must be known before the minimum cutoff across the entire prefix; cutoffs need
not be monotone. Original raw decimal and timestamp strings remain in state.
UTC comparison accepts RFC3339 lower-case `t`/`z` and `-00:00` as known UTC with
an explicitly unknown local offset; it infers no local Date or zone. Unqualified
times, leap seconds and normalized UTC outside years0001..9999 reject.

The neutral state contains the exact original context and full original frame
prefix, computed frame results, all vintages, processed tranche flags, consumed
identities, fee keys and cumulative controls. The next invocation supplies the
actual JSON-serialized preceding closing state and its matching predecessor
summary. Replay recomputes every prior checkpoint and reconciles all state.
The supplied `result_ref` is provenance metadata, not cryptographic authenticity
or external registration. A real canonical source implementation must use the
actual validated predecessor reference supplied by its generic runner.

The finite profile allows at most4 frames/4 vintages,8 rows per ordinary table,
32 evidence rows per frame or registry, and one or two term release rules. It
produces unissued calculations. It does not implement partial-history previews,
payment execution, bank movements, FX, professional approval or a state service.

## Source interpretation still open

Generic due release here is **unconditional under supplied synthetic terms**.
Absent claim-active or distributor information is not interpreted as sourced
clearance. This schedule and clipping cap do not resolve the Genius signed
excess-return/after-liquidation Net Receipts, fee and allocation corrections,
source fee bands, source caps, active-claim eligibility, reasonable liquidation
lags or extensions. The separately accepted Genius within-vintage profile and
its remaining obligations retain their own scope. The Pacific Gold CAD cap
comparator in RR04 uses a source-specific rejection policy; it is not this USD
synthetic clipping policy.

This fixture/oracle completes an independent engineering control design only.
Native SPL, canonical publication, actual canonical predecessor and emitted
backend evidence require separate implementation by a different author.
