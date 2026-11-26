# Finite fiscal calendar and amended terms

This is one synthetic C14 calculation method under
`SYNTHETIC-CALENDAR-TERMS-01@1`, a proposed `research_assumption`. The
[policy](policy.md), [original neutral rows](neutral.json),
[independent design](../../docs/spl/calendar-terms-design.md) and
[oracle](../../oracles/calendar_terms.py) precede this implementation.
Existing records, Date-keyed maps, filters and finite folds express the method;
no calendar primitive, compiler or canonical schema change is added.

The selected fiscal interval is April 6 through, excluding, May 6, 2026. Original
daily rows determine the eligible denominator: 30 in the baseline. Both terms
apply only April 26-May 6, leaving 20 explicit inactive days. As of April 19,
revision 1 at 240 contributes 80 over ten active eligible days. Recording-date
equality on April 20 selects revision 2 at 300 and gives 100. A separately
selected May 1 amendment at 600 contributes 100 for its five days, alongside
50 for five days under revision 2: total 150.

The source counts eligible and active days itself, selects the unique greatest
known effective revision for every daily row, and sums exact `monthly / D`
amounts. It preserves per-term and per-day lineage when amounts differ. Empty
eligible populations block; no available term is the explicit `inactive_zero`
outcome. A selected zero amount remains active and keeps its term identity.
Competing highest revisions block even at equal money. Original predecessor
IDs, revision order, scope and recorded dates are validated before calculation.

Signing and recording are civil Dates selected with `<= as_of`. Separate
observation Instants must satisfy exact `< cutoff`; a later observation before
cutoff does not alter the civil Date-as-of rule. This is not full bitemporal
observed-knowledge replay. The method retains all supplied terms, including
later-known and unselected terms, and rejects invalid ones.

Business-day rolling uses the same original daily rows across the complete
supplied coverage, including margins outside the selected fiscal interval.
Following chooses the minimum open supplied date on/after the due date;
preceding chooses the maximum open supplied date on/before it. The synthetic
May 1 holiday gives May 4 following or April 30 preceding. An already open day
stays unchanged. Missing due rows or open neighbors block; no outside date or
modified-following convention is invented. Closed weekdays and holiday flags
are supplied policy, while financial eligibility is a separate flag.

## Mechanical input boundary

`validate_calendar_inputs` independently checks original Gregorian dates,
ordinal epoch and ISO weekday metadata, Boolean closed/holiday/eligibility flags,
calendar version/scope/source/evidence references, complete coverage and a fiscal
partition with no gaps or overlap. The declared engineering bound is 400 covered
days. This validator imports no oracle, calculates no proration denominator,
selects no financial term and returns no solved values.

The adapter copies the selected original fiscal record into canonical manifest
scope, tags exact money and integer spellings, and transports every original
daily/fiscal/term record. It mechanically renames reserved source field `date`
to `calendar_date`, and deadline `date` to `due_date`. No solved eligible count,
active count, prorated money or rolled deadline enters the source inputs.

SPL derives the financial numerator/denominator and business relation from those
rows. Integral counts are represented as exact sums of Ratio zero/one so money
can be divided by the denominator without a new numeric conversion operator.
Source/descriptor checks also enforce identities, scope, evidence, declared
closed relations, finite partition, term constraints and atomic failure.
Direct typed execution cannot independently derive Gregorian ordinal/weekday
truth or complete coverage from the current Date API; it relies on the declared
mechanical input boundary. That boundary is not a proof of arbitrary calendars.

## Register and check

Use the pinned repository Python/Lean setup and prior successful build. Run from
the repository root:

```powershell
& 'C:/Projects/Film_TV_participation_dynamic_DSL/environment/python/python.exe' -m cases.calendar-terms.build_modules
& 'C:/Projects/Film_TV_participation_dynamic_DSL/environment/python/python.exe' -m unittest Tests.test_calendar_terms_oracle Tests.test_calendar_terms_modules -v
```

The builder deliberately generates `calendar-terms-module.json` and an unbound
`canonical-package.json`. Fresh invocations call `calendar_package` with the
registered reference, then `run_module_package(..., backend="compare")`.
Because the case folder has a hyphen, Python callers can load its builder with
`importlib.import_module("cases.calendar-terms.build_modules")`.

Comparison tests use temporary registrations and check every financial summary,
daily line, term line and business-day identity against the independent oracle
through reference/native IR/native-emitted Lean. Other tests explicitly identify
reference-only financial negatives and pre-calculation mechanical failures.
The calculation has no state slots or payment events; it creates no issued or
paid amount and makes no professional approval claim.

On 23 November 2026, one combined run passed all 29 methods: 18 independent
oracle and 11 module methods in 119.861 unittest seconds (119.976973 process
seconds), exit code zero, with all checked source/template bytes unchanged.
The raw log, exact pins and source freeze are retained under
`C:/Projects/Film_TV_participation_dynamic_DSL/artifacts/spl/calendar-terms-checks-57573d5c`.
This is supplemental bounded-method evidence, not a full repository regression
or full C14 completion.

The baseline supplied population has 40 days and 30 selected fiscal rows. A
native audit observation is a different cost from pure emitted calculation;
passing the 400-day admission check is no capacity result. Larger term tables,
calendar populations and audit traces need measurement before a useful envelope
can be claimed.

Fiscal/legal-calendar universality, timezone inference, automatic holidays,
amortization/other day-count conventions, dependent-period correction, payment
execution and full C14 coverage remain outside this selected method.
