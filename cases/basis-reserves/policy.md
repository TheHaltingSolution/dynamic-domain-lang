# Elected basis-stage return reserve: selected bounded policy

For a qualifying original cash receipt `G`, a separately approved election creates
reserve addition `A = G × 20%`; an explicit non-election creates `A = 0`.
Current Net Receipts are `G − A + L`, where `L` is unused reserve released from
identified original vintages. A matched actual return consumes that vintage's
available reserve and is not deducted from Net Receipts again. The selected fee
is `10% × Net Receipts`; the remaining `90%` is the calculated ESPN allocation.
Every amount is an exact rational; this profile does not round.

Each elected addition has its own original receipt, election, purpose, source,
scope and six-calendar-month deadline. The selected operating convention releases
all unused balance on that deadline. Addition plus opening balance must equal
matched returns plus released balance plus closing balance, independently for
each vintage. No return can use another vintage's reserve.

| Original checkpoint | Original event | Addition | Return applied | Release | Net Receipts | Fee | Allocation | Closing reserve |
| --- | --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| 2009-01-15 | V1 qualifying cash 1,000 | 200 | 0 | 0 | 800 | 80 | 720 | 200 |
| 2009-04-15 | V2 qualifying cash 800 | 160 | 0 | 0 | 640 | 64 | 576 | 360 |
| 2009-05-15 | Actual return 60 against V1 | 0 | 60 | 0 | 0 | 0 | 0 | 300 |
| 2009-07-15 | V1 unused balance due | 0 | 0 | 140 | 140 | 14 | 126 | 160 |
| 2009-10-15 | V2 unused balance due | 0 | 0 | 160 | 160 | 16 | 144 | 0 |

The complete original history reconciles `1,800 − 60 = 1,740 = 174 + 1,566`.
The positive non-elected control is cash 1,000, reserve 0, Net Receipts 1,000,
fee 100 and calculated allocation 900. Reserve zero does not block receipt
recognition.

The source support is **partial: within-vintage returns only**. Section 10 also
reduces Net Receipts for actual returns exceeding reserve. This initial profile
rejects excess original-vintage returns with
`BR_EXCESS_RETURN_VARIANT_REQUIRED`, including a return against a non-elected
receipt. Returns after liquidation reject with
`BR_RETURN_AFTER_LIQUIDATION_VARIANT_REQUIRED`. A later named policy must specify
signed Net Receipts, fee corrections and allocation effects. Neither flooring
the excess to zero nor borrowing another vintage's balance completes that
source requirement. This slice must not be recorded as complete C09 source
support.

The July 7, 2006 [Genius–ESPN agreement](https://www.sec.gov/Archives/edgar/data/1098016/000119312506200074/dex101.htm)
§§10–11 place the elected 20% reserve before the fee and require unused additions
to be liquidated within six months, with the fee retained on release. The
published fee bands are redacted. Sections 1–4 identify covered programs,
territory and physical Videogram rights; §9(c) identifies Sales Period 3 (2009).
The [assignment disclosure](https://www.sec.gov/Archives/edgar/data/1098016/000101968706002845/genius_10q-093006.htm)
is retained as provenance; subsequent agreement history has not been verified.

The following are selected synthetic assumptions, not professional approval:

- USD cash actually received in the US from one approved physical Videogram
  program; the contract's wider territories and other media are outside the slice.
- Approved successor authority in 2009, covered-program status and fixed terms.
- A flat 10% fee replacing confidential source bands only for Sales Period 3.
  This is not a reconstruction of the undisclosed fee calculation.
- Explicit complete approved zero remaining guarantee/expense claims and no
  other adjustments. The fixture does not derive historic guarantee recoupment.
- Same-day receipt and reserve establishment. Six calendar months preserve the
  day number when valid and clamp to the last valid day when necessary;
  April 30 becomes October 30, without month-end preservation. Full unused
  release is booked on the deadline inclusively. Earlier release permitted by
  the source is outside this selected timing convention.
- Same-day processing is receipt/election, then ordered original returns, then
  computed due release. Distinct nonnegative integer sequence numbers order
  events within each receipt or return stage. A return on the due date consumes
  reserve before the remaining balance releases.
- Event dates are supplied UTC calendar dates. Each interval is half open;
  `as_of = end − one day`. Own observations and supporting evidence must be
  strictly before that interval's cutoff. Historical knowledge is replayed with
  its original cutoff, not the current cutoff.

The Jan/Apr/May/Jul/Oct checkpoint windows and completeness attestations are
synthetic ledger controls. Release dates/amounts are derived, including due dates
inside a later spanning interval. The population's numeric zero is supported by
an explicit complete original-fact statement; absent population evidence blocks.

The allocation and reserve release are calculated accounting measures. There
are no bank-payment records in this profile and no paid amount is inferred.
The output reports `not_assessed_no_bank_payment_measure`. No refund, currency
conversion, CAD comparator execution, legal approval or actual chain-of-title
verification is claimed.
