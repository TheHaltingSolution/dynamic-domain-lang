# Neutral R1 financial controls

These are project-owned synthetic records for the methods selected in
[RR-03 integration](../../docs/spl/rr03-response-integration.md). They are not
historical accounts, approved contract interpretations, vendor-certified goldens,
or unseen evaluation material. No independent financial or legal approval is
recorded. They are ready for arithmetic and compiler-integration review; passing
these controls alone does not promote either sourced case to accepted status.

The separately authored [oracle](../../oracles/r1.py) imports only the Python
standard library. It reads neutral facts, not compiler projections, SPL bindings,
native IR, generated answers, or fixture `expected` fields. Results retain exact
`Fraction` intermediates; `exact_json` renders reduced rational strings (`85/2`
means USD42.50). No cents rounding is inferred. Missing selections have no
economic default. The functions raise `OracleError` for rejected semantic inputs;
these plain dictionaries are a test input format, not a public JSON schema or
replacement for canonical validation.

Run from the repository root with a Python whose import path includes that root:

```powershell
python -m unittest Tests.test_r1_oracles -v
```

On the current workstation Python is
`C:\Projects\Film_TV_participation_dynamic_DSL\environment\python\python.exe`.

## Evidence and interpretation boundary

The source supplied for this work is the local research response
`ResearchAgent/documents/SPL_RR03_Coverage_Benchmarks_and_Workload.md`, under the
external project folder. Its recorded SHA-256 is
`66208830B259762BA6DF959904FBF4453CABEB53D7A8BF7458307B994D86CB82`.
The retained portable locators and short excerpts below identify its §2 table
and following MQP paragraph; no new external research was performed. Filed links
are provenance locators, not claims that their full provisions were re-reviewed
or that every fixture condition appears in the filing.

Each evidence record is expressly synthetic. Its identifier and observation date
establish test lineage and a civil-date cutoff, not authentic source verification.
Periods are start-inclusive/end-exclusive. Evidence observed after the cutoff
blocks the calculation. These cases assert no instant precision or time-zone
behavior. Every same-day MQP economic order is supplied explicitly; physical
input ordering has no effect.

## Angel Guild allocation

`angel-guild.json` uses the supplied response's Angel table row: “Title payable
$85 and other titles $415” and “Add 1,000 minutes consumed on other titles”.
Its filed locator is the signed 26 February 2025 Angel 010–Mofac agreement,
§5(a)(vi), Exhibit C §4.1 and Exhibit D §4(b),
[Exhibit 6.2](https://www.sec.gov/Archives/edgar/data/2060101/000110465925022517/tm258018d1_ex6-2.htm).

The selected Q2 2025 method is USD1,500 Guild cash, a 25% gross marketing fee
(375), other approved Guild costs125, and zero opening carry. Net1,000 splits
equally: Angel500 and filmmaker pool500. A declared complete platform population
contains focal170 and other830 qualified minutes, giving 85/415. Adding 1,000
other-title minutes changes the denominator to2,000 and gives 42.50/457.50.
Repeated records for one title aggregate before allocating. Zero-weight titles
receive zero; a zero population blocks. Negative net, missing completeness or
scope/period/metric mismatch blocks rather than selecting a fallback.

The ordinary-distribution cash999 is an explicit exclusion probe; it is not
part of the research checkpoint. All tests with changed amounts, counts or
scope are engineering variants. The focal title never supplies its own platform
denominator. The declared completeness of this synthetic population is not
evidence of the real platform population. Actual metric qualification, cost
eligibility, collection-account terms, precision and source-agreement linkage
remain unresolved for historical use. Full-period usage requires an observation
cutoff at or after period end.

## MQP ordered fee and separate correction

`mqp-ordered.json` follows the supplied response's MQP row, which describes
“$10/$10/$20 under the proposed prospective agreement-date interpretation”,
and its following event-sequence paragraph. The filed locators are 25 July 2007
MQP–Lions Gate TV Exhibit10.42 §§4.1,6.3–6.4,7.2,
[distribution agreement](https://www.sec.gov/Archives/edgar/data/929351/000095014807000187/v32671exv10w42.htm),
and companion Exhibit10.40,
[RP agreement](https://www.sec.gov/Archives/edgar/data/929351/000095014807000187/v32671exv10w40.htm).

The explicit synthetic selections are:

- The same project/pool opens with actual-paid900 and fee-available-paid900,
  against threshold1,000. Equality reaches the upper rate under `at_least`;
  `greater_than` is a tested alternative, producing total fee30 at exact equality.
- January10 accrual100 is not cash. January20 actual payment100 moves the cash
  ledger to1,000, but is declared disputed. A same-day dispute record documents
  that status. February5 agreement approves exactly that payment's amount and
  actual date; agreement-date credit becomes available prospectively then.
  Changed agreed amounts and unlinked agreements are outside this selected method.
- Eligible receipts100 on January15, January25 and February10 take rates
  10%,10%,20%, fee40 and adjusted receipts260. The separately selected
  `actual_date` sensitivity uses 10%,20%,20%, fee50 and adjusted receipts250.
  Neither variant reprices earlier receipts retroactively. There is no inferred
  default trigger, calendar offset, or 120/365-day rule.
- The added principal U.S. TV license700 is excluded. The added second project's
  payment10,000 cannot affect project A. These two probes are engineering data.
  All three checkpoint receipts are fee-bearing. Other deductions are zero.
- Adjusted receipts are **before RPPA allocation**. No final producer payable,
  bank payment, waterfall approval or historical settlement is established.
  Same-day receipt/agreement variants explicitly reverse sequence numbers and
  discriminate fee40 from50; a tied date/sequence blocks.

`mqp-correction.json` is a separate authorized prospective correction, not an
implicit step in the fee calculation above. It references one synthetic original
fee payment, authorizes an overpayment10, and supplies future available capacities
4 and12. Movements are4/6; remaining correction6/0; unused capacities0/6.
The capacity is supplied and evidenced, not derived from gross receipts or
assumed to be unrestricted cash. Zero/empty/insufficient capacity retains the
unapplied balance. Foreign-pool capacity, missing authority and recognition of
an already recognized correction block. The oracle covers one recognition and
its ordered applications in one supplied period. A successor close requires
separate opening-balance/lineage integration; re-recognizing the authorization
is prohibited. The project-specific pool isolates this correction's scope.

Trigger effectiveness, receipt capacity, equality and waterfall role remain
selected engineering interpretations awaiting case-specific review. A future
real agreement may require a different selected method.

## Supplied-date reserve and deliberate omission

`supplied-due-reserve.json` is the disclosed open experiment's **baseline**
comparison from [the experiment plan](../../docs/spl/extensibility-experiment.md).
It supplies a deadline2025-02-28 and available balance20 for a scoped vintage,
with no actual-return application. The selected inclusive rule releases0 on
February27 and20 on February28, leaving0 on that date. Vintage scope, period
and observation cutoff are checked; release is a reserve movement, not a bank
payment. The creation date2025-01-31 and the deadline are independent supplied
facts. The oracle does not derive or certify their month relationship.

There is intentionally no `add_calendar_months` implementation here. No day-count
substitute or hidden deadline derivation is added before the R1 freeze. E0/E1
attempt/freeze evidence and any subsequent extension belong to the separate
experiment protocol; this fixture alone does not execute that protocol.
