# Original revision and separately authorized recovery

This selected C08/C13 composition preserves original issue/payment history and
calculates only separately authorized recovery. The independent
[oracle](../../oracles/authorized_offsets.py),
[design](../../docs/spl/authorized-offset-design.md), [policy](policy.md) and
[neutral facts](neutral.json) precede the executable SPL. These are synthetic
research assumptions, not a general refund, creditor or legal clawback right.

Original basis 200 at original rate .5 gives gross 100, separately issued 100
and independently paid 80. A linked authorized return of basis 80 reverses 40,
revises the old entitlement to 60, leaves old outstanding zero and potential
overpayment 20. Original issue 100 and actual paid 80 remain unchanged in every
successor. A cash repayment is a separate receipt; it does not rewrite that
historical payment.

Potential overpayment alone creates no claim. Without offset authority, fresh
earned 30 remains calculated payable 30. Separate authority for principal 20
permits offset 20 and calculated payable 10. The signed reversal remains visible
and is not deducted again from fresh earnings. Total principal ever authorized
against the original, including fully recovered claims, continues to consume
its cumulative overpayment capacity. A new claim cannot recycle closed authority.

Prospective original capacity includes only reversals recognized on/before the
claim's eligible Date, with equality included. A later return cannot fund an
earlier approval. Other supplied claims retain separate original amount/source
limits; they are not inferred funded advances. Scope never crosses the declared
agreement, participant, pool, asset and USD currency.

## Cash, accounting offsets and explicit order

Actual cash receipts are fully applied to identified eligible authorized claims
before earnings offsets at the selected run boundary. Cash received UTC Date,
received/observed Instants, actual-cash support and original receipt/application
identities are checked. Unapplied cash, claim overapplication or reused receipt
identity blocks the entire run. This stage order does not assert that historical
bank transactions chronologically preceded economic earning dates.

Fresh unissued earnings use effective Date then unique explicit sequence. Claims
use the supplied, checked priority and globally unique claim sequence. Two named
recipes remain distinct: `clawback_first` and `other_claim_first`. With an original
claim 20, separate other claim 25 and earning 30, they allocate 20/10 versus 5/25.
Physical row order supplies no priority. The adapter never computes a priority.

For each claim, authorized principal equals actual cash recovered plus calculated
earning offsets plus remaining. Cash repayment 5 followed by earning 10 against
principal 20 gives cash 5, offset 10, remaining 5 and payable zero. Actual adjacent
periods then offset 3 and 2 from new earnings, retaining original paid 80 and
never repeating the original reversal or repayment. No new settlement actual
payment or bank refund is inferred from those calculated offsets.

## Complete populations and original history

The original payment snapshot pins issued ID, capture as-of, original payment,
disbursement and application IDs, and exact source paid total. Every payment is
positive, fully applied to the original issue and historically paid before the
first recognition period. Its snapshot can be captured later, but must be
available by the first cutoff and remain unchanged across carry. It is not a
newly measured payment population in every later period.

Every current and replayed recovery period independently requires exact cash,
receipt and application IDs and an attested cash total. Complete-empty lists
with total zero differ from missing completeness. Dropped/aliased facts and
population observations earlier than the facts they summarize fail controls.
Missing payment or recovery population blocks consumable finance and state,
with `no_event_supplied` rather than a numeric unknown amount replaced by zero.
Selected blocked-evidence labels enter the generic runner before atomic
publication; successful digest-bearing results are never post-mutated.

State pins the full original source bundle, scope, policy/recipe, cumulative
returned basis, all open/closed claims and original period history. Each history
retains its own approval as-of Date and exact observation cutoff plus all six
original arrays. SPL replays original movements from genesis, validates every
authority including unused declarations, reconstructs every claim and reconciles
the actual opening. Required evidence for old movements must precede that old
period's cutoff; later evidence cannot silently satisfy history.

Replay exposes each already supplied, globally unique `source_case_id` as the
transient period wrapper's `id`. This gives native audit scopes a short original
economic identity instead of recursively embedding the whole anonymous period
record in every observation ID. Full records, observation values, financial
order and state remain present. No identity is synthesized from array position
or concatenated financial fields; duplicate period case identities already
block the selected oracle and source policy.

Adjacent carry serializes the actual canonical closing cell, retains its actual
`prior_result_ref` and matches the supplied predecessor case/period/snapshot.
This establishes consistency of supplied provenance, not external custody or
cryptographic authentication of a bank payment or professional approval.

## Representation and reproduction

The adapter transports original exact values, Dates, Instants, explicit integer
positions and source/evidence IDs. It mechanically checks original-line syntax
(`artifact#line`), derives a receipt's UTC Date and supplies explicit UTC opening
midnight from a validated civil Date. It computes no gross, paid total, claim,
prospective capacity, priority, repayment or offset. Those calculations and
comparisons run in SPL. Original numeric and timestamp spellings accompany typed
values and survive neutral export, including authority records and historical
cutoffs. Full source snapshot changes cannot disappear through normalization.

The canonical template and no-authority example are intentionally unbound;
execution binds current compiler/runtime/module identities. Both priority recipes
accept caller-supplied declarations checked in source. With the pinned environment
and existing native kernel:

```powershell
python -m cases.authorized-offsets.build_modules
python -m unittest Tests.test_authorized_offset_oracle Tests.test_authorized_offset_modules -v
```

Native test methods request canonical compare (native IR, native-emitted Lean and
reference), then separately execute Lean from the Python emitter using identical
decoded bindings. Independent controls compare every financial field, claim,
earning/offset movement, historical prefix and complete successor state.
Successful and unknown-population artifacts are validated with
`load_completed_result`; review `result.json` equals the returned object.

Finite lists/filters/folds preserve arbitrary original Text identities. Repeated
identity scans and earning-by-claim updates grow with the supplied populations;
the generic resource guard is not a capacity result. The profile excludes new
original-payment snapshot revisions, actual settlement payment/refund execution,
cross-scope claims, negative raw corrections, FX, general recourse, bankruptcy
priority and whole-contract approval/proofs. Issuance remains unissued.

The input and publication guards are separate. The package requests the generic
100,000 input-row bound; that is neither a history-period limit nor a guarantee
that an admitted history's full audit can be published. In the retained three-
period witness, final result JSON is 67,025,493 bytes under the unchanged
67,108,864-byte publication cap, leaving 83,371 bytes. This is a tightly bounded
successful witness, not an eight-period or larger-publication capacity claim.
Larger prefixes or source populations may fail the publication guard honestly,
without a completed consumable state. The earlier failed publication cohort and
its full size diagnostic remain retained; no guard was raised and no trace was
truncated to obtain the successful source-qualified result.
