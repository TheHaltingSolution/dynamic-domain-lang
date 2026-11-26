# Payment-aware original revision and authorized recovery

`SYNTHETIC-AUTHORIZED-OFFSETS-01`, revision `1`. This is a bounded synthetic
`research_assumption`, not a universal refund, clawback, compensation, offset
or historical correction right. All amounts are exact USD without rounding.

One original measurement determines original gross entitlement at its original
rate. Its separately supplied original issue equals that entitlement in this
profile. A frozen original payment snapshot retains independent actual payment
and application records and complete-population controls. Original paid cash
is not inferred from the issued notice. Original payments are never rewritten
when a later return or cash repayment is recognized.

Only explicitly approved linked reversals revise that original obligation.
Multiply returned measurement by the original rate, not a current rate; cumulative
returned measurement cannot exceed the original. Revised entitlement equals
original gross less recognized reversal. Outstanding old obligation is
max(revised-original_paid,0); potential old overpayment is
max(original_paid-revised,0). The signed reversal remains visible but is not
also deducted from new future earnings as a second loss.

A separately approved prospective authorization may create a positive recovery
claim no larger than the remaining unallocated original overpayment capacity.
Previously authorized principal continues to consume that source capacity even
after recovery; it cannot be authorized again under a fresh claim ID. Without
such authority, potential overpayment remains unresolved and new earnings are
not automatically reduced. A negative earning or return alone creates neither
a bank refund nor an offset claim. Separately supplied other claims have their
own original source/amount limits and authority; they are not inferred advances.
Prospective original claims use only reversals recognized by their eligible Date,
with equality included, and are registered by that Date then unique sequence.
A later recognition cannot supply capacity to an earlier claim.

Actual cash repayments are distinct original bank receipt records, fully applied
to identified authorized claims before calculated earning offsets. There is no
recognized unapplied cash in this finite policy: missing or excessive applications
block. Cash received Date is its explicit UTC received_at date; received_at must
precede or equal observation, with both available before cutoff. Support evidence
must identify actual cash recovery. These repayments do not lower the immutable
original amount actually paid; they separately reduce the authorized claim.

Process nonnegative future earning rows by effective Date then unique explicit
sequence. Offset only claims whose prospective eligible_from date has arrived.
All new claim authorizations are known by the explicit civil as-of Date; eligibility
starts no earlier than their recorded approval date. Original-return revision is
not another deduction from these fresh earning rows. The calculated earning
capacity remaining after authorized offsets is unissued payable, not cash paid.

Two explicit priority recipes exist: `clawback_first` and `other_claim_first`.
Each authorization states the matching priority and unique sequence. No physical
row order, equal-priority tie or assumed statutory priority selects a winner.
Claims retain authorized principal, actual cash recovery, calculated earning
offsets and remaining balance separately. For each claim:
authorized = actual_cash_recovered + earning_offsets + remaining.

The baseline original basis200/rate.5 gives gross100, separately issued100 and
actual paid80. Authorized returnbasis80 reverses40, revises entitlement60 and
leaves outstanding0/potential overpayment20. Separately authorizing20, with an
explicit complete-empty cash-recovery view and fresh earning30, offsets20 and
leaves calculated payable10. Without offset authority, the same fresh earning
remains30 and potential overpayment20 is unresolved. Original paid stays80.

With a separate supplied competing claim25 and earning30, clawback-first recovers
20/10; other-claim-first recovers5/25. Actual cash repayment5 followed by earning10
against a sole authorized20 claim leaves cash recovered5, earning offset10 and
remaining5. No bank payment is inferred from an earning offset.

Original payment completeness pins payment/disbursement/application IDs and paid
total at its frozen snapshot as-of. Each current cash-recovery population pins
cash/receipt/application IDs and cash total for the exact period. Missing population
evidence blocks unknown amounts and successor state; it never supplies numeric
paid or recovered zero. Complete-empty populations are separately and explicitly
attested. Dropping or aliasing source facts fails population/identity controls.
Population observations must follow the observations they summarize. Original
actual payment transactions precede the first recognition period, even when their
frozen snapshot is captured later. The snapshot is available by the first cutoff.

State pins original source bundle, scope, policy/priority recipe, cumulative
returned measurement, claims and complete original period history. The oracle
replays that history and requires exact adjacent actual predecessor state.
Each period retains its original approval as-of Date and exact Instant cutoff;
later evidence cannot retroactively make an old period observable.
Reusing original event IDs, bank receipt IDs, earning-line references, claims or
authorizations blocks. No debt is transferred across scopes, and no actual new
settlement payment, original payment-snapshot amendment, negative correction,
cash refund execution or general legal approval is supplied by this profile.
