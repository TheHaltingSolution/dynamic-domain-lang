# Research answers adopted for the named synthetic cases

20 November 2026. The user supplied these rights-management research answers in
the conversation. This records their meaning and engineering disposition. The
original questions remain in [implementation-questions.md](implementation-questions.md).

## RR-01: prospective participant advance (SV-03)

Use actual funding as the economic effective date. Approval, an obligation or a
due date alone does not increase the prepayment pool. Require stable issue and
disbursement identities, evidence of actual funding and scenario eligibility,
and separate observation timestamps for the issue and supporting evidence.
Include funding in the half-open accounting period only when both records are
available strictly before the pinned cutoff. June 30 funding first observed
July 2 may enter Q2 with a July 3 cutoff. An advance due June 30 but actually
funded July 1 belongs to Q3.

Match agreement, participant, authorized pool, currency and the
`participation_prepayment` purpose. Retain source title for traceability. Count a
disbursement once even when cash and evidence records both describe it. Add
selected issues to opening availability, then recover from pooled eligible
nonnegative earnings. Opening 0 + funded issue 15,000 against earnings 10,000
means recovered 10,000, payable 0 and closing carry 5,000.

This is settlement-stage order. It does not select FIFO, require the quarter's
earnings to arise after funding, or give priority over competing offsets.
Reversals, backward recovery and competing offsets remain outside this case.

Implemented in `cases/mechanisms/advance-issues.spl` and its typed bindings.
This separate mechanism does not change SV-01 or the RQ-07 policy.

## RR-02: correction versus actual payment

Confirmed: revised entitlement 90 less independently evidenced actual payment
80 leaves 10 outstanding on the same obligation. The mechanism may accept
entitlement and actual payment as supplied inputs. The 10 is an outstanding
balance; a new payment or prospective offset requires separate authority.

A full CORR-01 restatement additionally requires scoped synthetic authorization,
stable correction and replacement IDs, the affected period, and the original
opening snapshot. Keep Q4 economic effect, February approval and observation,
and actual payment disbursement dates distinct. Apply the correction once.

The current correction mechanism reconciles supplied entitlement and payment.
It does not reconstruct the historical period or implement the full restatement.
The additional requirements above remain follow-up work.

## RR-02: reserve vintages

The aggregate identity is correct, but comprises two distinct vintages:

| Vintage | Opening | Addition | Linked actual return | Unused release | Closing |
| --- | ---: | ---: | ---: | ---: | ---: |
| V1 | 12 | 0 | 7 | 5 | 0 |
| V2 | 0 | 20 | 0 | 0 | 20 |
| Total | 12 | 20 | 7 | 5 | 20 |

Key each movement by stable ID, reserve purpose, scope, currency and vintage.
Use effective date for period selection and a separate observation timestamp
for cutoff. Evidence must identify the authorized addition, linked actual return
or authorized release. Reject applications/releases above the available balance
of their own vintage. Aggregate availability does not permit cross-vintage use.

Implemented in `cases/mechanisms/reserve-vintage.spl`, replacing the prior
single-vintage fixture. Both per-vintage and aggregate results are asserted.
This is a reserve balance rollforward. The separate post-earnings holdback tests
payable; the contractual video-reserve stage and treatment remain unresolved.

## Relationship to the language-design answer

[LD-01-D1](implementation-answers.md) retains the financial-rules-first authoring
direction with visible, incorporated economic definitions and pinned support.
It is the language-design answer. RR-01 and RR-02 are the research answers for
these named mechanisms. Both agents may review the combined package; their
answers have distinct primary ownership. No new question is needed for these
bounded refinements. These replies do not approve wider historical policies.
