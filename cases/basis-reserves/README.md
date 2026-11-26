# Elected within-vintage basis reserve

This registered SPL method implements the selected bounded
[Genius policy](policy.md) over [original facts](neutral.json). The independently
authored [oracle/design](../../docs/spl/basis-reserve-design.md) remains separate
from source and adapter code. Source support is partial: excess-return and
after-liquidation Net Receipts reductions require a separately selected signed
policy. This implementation rejects those cases explicitly.

An approved election reserves20% of original qualifying cash before the fee.
Explicit non-election reserves0 while still recognizing positive cash. Each
original receipt creates its own vintage. Matched actual returns consume only
that vintage and are not deducted from Net Receipts a second time. SPL derives
the six-calendar-month anniversary with `add_calendar_months` and `clamp_day`,
then releases all unused balance on the due day inclusively. April30 becomes
October30; August31,2009 becomes February28,2010. No deadline or release amount
is supplied by the adapter.

SPL processes each original day in chronological order, with ordered receipts
and elections first, ordered original returns next, and computed due releases
last. Thus a due-day return consumes reserve before unused balance releases.
Original nonnegative sequence numbers must distinguish events within their
stage/day. Release order uses the original vintage ID. Neither physical array
order nor another vintage's available money authorizes a return.

The original five checkpoints derive:

| Checkpoint | Gross | Added | Return applied | Released | Net Receipts | Fee | Allocation | Closing reserve |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| January | 1,000 | 200 | 0 | 0 | 800 | 80 | 720 | 200 |
| April | 800 | 160 | 0 | 0 | 640 | 64 | 576 | 360 |
| May | 0 | 0 | 60 | 0 | 0 | 0 | 0 | 300 |
| July | 0 | 0 | 0 | 140 | 140 | 14 | 126 | 160 |
| October | 0 | 0 | 0 | 160 | 160 | 16 | 144 | 0 |

The complete history reconciles1,800−60 =1,740 =174+1,566. Positive
non-election gives Net Receipts1,000, fee100 and allocation900. Source output
includes every movement, checkpoint, cumulative amount and vintage, including
original election records and consumed return/claim/release identities.

## Boundaries and transport

The adapter validates physical shape, parses exact quantities, transports UTC
midnights and preserves raw originals. It does not calculate any reserve,
deadline, release, Net Receipts, fee or allocation. Current and historical
evidence selection remains in SPL: each original checkpoint keeps its own
as-of Date and exact exclusive observation cutoff. Original receipt/return
dates are independent from observations; old evidence cannot be made timely
by using a later checkpoint's cutoff.

The structured quantity explicitly pins `basis-reserve-original-json/1`.
Hot financial/validation loops use narrow typed projections; complete original
records are retained at input and post-replay state boundaries as exact JSON
Text envelopes `{category,id,record}`. Serialization/restoration is checked
against all original fields and raw numeric/timestamp lexemes. SPL selects each
snapshot's proper original prefix and compares the complete incoming opening
with its own replay. Scope, authority, research, policy, original facts,
vintages, cumulative meters and movements remain pinned. This physical encoding
does not hide a solved financial answer.

Original evidence positions supply transient integer lookup slots. The adapter
associates a slot using only the original evidence reference, while SPL checks
all original ID uniqueness, slot uniqueness/range, selected original-ID equality
and every applicable scope/kind/approval/cutoff condition. Slot0 is valid.
Positions may change with evidence-array order; original economic identities
and restored results must remain unchanged. Raw physical-binding tests bypass
the adapter to exercise native slot guards.

SPL has no Text concatenation primitive. The selected movement identity is
therefore represented as `Tuple<Text,Text>`: fixed validated category
`addition`, `return` or `due-release`, plus the exact original receipt, return
or vintage ID. Mechanical join/split restores the oracle's category-qualified
Text identity, preserving embedded delimiters and Unicode. Canonical Text keeps
the existing NFC admission boundary; these Unicode controls do not establish
native acceptance of every normalization form. Dates and all
financial effects are still calculated in SPL. The reserved logical movement
field`date` is transported as typed`movement_date` and restored mechanically.
Optional movement fields preserve their original absence.

Default registration materializes the first original checkpoint with an explicit
genesis frame; the original fixture supplies no opening financial answer.
Later actual runs JSON-round-trip the previous validated closing cells, remove
only output-only`movement` from a separate input copy, and retain quantity,
state key, boundary and the real`prior_result_ref`. Previous returned/loaded
results must remain unchanged after constructing the successor. A separately
labeled supplied-history opening is a different evidence mode and does not
fabricate a canonical predecessor or authentication claim.

Preview is the generic provisional review of the **same complete known
checkpoint calculation**. It preserves the independent candidate amounts and
returns no consumable closing state. It is not a newly introduced partial-history
policy. Missing/false populations or missing/uncleared claims block all financial
outputs and state; they do not manufacture zero claims or zero bank payments.
The profile has no bank-payment measure and reports
`not_assessed_no_bank_payment_measure`.

## Checks and limits

```powershell
python -m cases.basis-reserves.build_modules
python -m unittest Tests.test_basis_reserve_oracle Tests.test_basis_reserve_modules -v
```

`compare` checks reference evaluation, native IR and native-emitted Lean.
Selected module controls also execute separately Python-emitted Lean and compare
all values/errors/closing state. Full restored original state and every material
checkpoint/vintage/movement are checked against the independent original-fact
oracle. Native-IR observations do not measure emitted-target branch coverage.

The first targeted native final-checkpoint supplied-history witness publishes
49,457,767 bytes, agrees with reference/native-emitted output and restores the
independent full closing state. Its completed loader equals the returned object.
It is retained under external SPL artifacts as `basis-reserves-native-draft-a`;
it is not the five actual native predecessor runs or full acceptance. A targeted
calendar/Unicode identity method also passes in48.992s. Reference-only checks
retain their narrower execution scope.

The subsequent frozen acceptance is retained externally as
`basis-reserves-checks-6b3d9171/verification.json`:46 methods (32 independent
oracle and14 module), zero failures/errors/skips,871.471678s for the test
process. All56 watched source files and compiler/module/runtime identities
remained unchanged. The separate actual five-period plus preview phase took
191.034076s; total campaign elapsed1062.540950s. These are correctness and
resource witnesses, not quiet-interval performance comparisons.

Actual January, April, May, July and October closing cells were serialized and
loaded into their adjacent successors, retaining their real canonical
`prior_result_ref`. The predecessor returned object and completed stored bundle
remain unchanged after carry construction. Each period agrees with the
independent full financial/vintage/movement/original-state controls, native IR,
native-emitted Lean and separately Python-emitted Lean. Every published bundle
passes the completed-result loader. January through October `result.json`
sizes are8,517,071;20,328,340;31,665,578;40,984,655;50,337,661 bytes. The
same-complete-checkpoint October preview publishes50,247,260 bytes, preserves
the candidate144 allocation, and exposes no consumable closing state. The
five-period result independently reconciles1,740 Net Receipts to174 fee plus
1,566 allocation, with60 applied returns and300 unused reserve released.

The frozen identities are compiler/reference
`20ea52ba37b7d84b4d5d7ed62c9c38b44a928cf1ffc2287f2bec358bda31c260`,
module `a5165f5db8a42a7365afc553e6e518913ded0065389c1e0a717dd197cd6d412a`,
and runtime
`673bb0fe936c48a60c1cf5a1a265fb1d1f9f3cd432f380ee9b3011b7729dace9`.
Only this README's evidence record was extended after that acceptance.

The declared input profile allows12 checkpoints,24 receipts,48 returns and
256 rows in each original array. These bounds do not guarantee successful
publication for every admitted combination. Completed result publication keeps
the unchanged64MiB guard; no trace truncation or higher timeout is authorized.
Incomplete/running artifacts cannot provide consumable state.

The synthetic10% fee substitutes for confidential source bands. Covered-program,
successor and zero remaining guarantee/expense findings are supplied synthetic
approvals, not professional accounting or chain-of-title verification. Other
media/territories, earlier discretionary liquidation, signed excess-return fee
corrections, actual payments and CAD/FX comparator execution remain outside this
selected slice. The source's excess-return requirement remains open even when
these within-vintage controls pass.
