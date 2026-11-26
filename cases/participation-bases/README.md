# Original participation bases

The independently authored [policy](policy.md), [neutral originals](neutral.json)
and [design](../../docs/spl/participation-base-design.md) select four explicit
synthetic methods. They do not assert professional contract approval.

| Method | Native calculation | Baseline USD |
| --- | --- | ---: |
| `gross_percent` | Original gross Money × percentage Ratio |25 |
| `net_percent` | (Original gross Money − deductions Money) × percentage Ratio |20 |
| `unit_rate` | Original Download Quantity × USD/Download Rate |150 |
| `unit_rate_then_participation` | That unit royalty × one separately supplied share Ratio |75 |

SPL derives each original table's total, net, selected basis, rate application,
pre-participation royalty and earned amount. Monetary and quantity bases use
separate `Option<Money<USD>>` and `Option<Quantity<Download>>` outputs; selected
percentage and unit rate use separate `Option<Ratio>` and
`Option<Rate<Download,USD>>` outputs. There is no money-to-quantity cast.
Deductions45 changes net to80 while quantity100 still yields150/75. Quantity80
with unchanged net100 yields120/60. The share is applied once only by the fourth
method. Fractions remain exact, with no cent rounding.

Every method validates all three original populations and all their rows,
including unused measures. Complete-empty populations are known zero. Absent
completeness, mismatched totals/IDs, duplicate IDs or original references,
negative measures, wrong scope, unapproved terms, wrong unit/currency and invalid
date/knowledge/cutoff relations block atomically. Deductions exceeding gross
require a separate loss policy; no implicit floor is inserted. The finite profile
allows32 rows per table and has no state, carry, amendments, issue/payment
execution or FX.

## Transport and boundaries

`build_modules.py` uses physical profile `participation-bases-original-json/1`
and identity codec `unicode-utf8-hex/1`. Canonical lowercase even-length strict
UTF-8 hexadecimal preserves original Unicode scalar identities and their lexical
order without normalization. The real agreement, participant, asset and pool
remain distinct, checked domain scopes. USD, Download, dates, numbers and enums
retain native domain meanings.

The adapter checks shape and reversibly transports original scalar values and
scope, supplies mechanical original-date UTC midnights, and retains the complete
escaped raw input JSON with its original number/timestamp lexemes. It does not
calculate totals, choose a basis or supply earned amounts. Native source checks
ordered original-ID population headers against its typed rows; the canonical
transport checks full raw/typed correspondence before binding. Arbitrary native
bindings do not gain a claim that SPL parses JSON, authenticates source records
or proves the mechanical Date/Instant conversion. Generic wrapper scope/type
rejections and adapter lexical errors remain separate from executed SPL guards.

The public `run_participation_base_package` wrapper takes a private copy and
rechecks the complete prepared typed facts, original headers, selected method,
cutoff, period and execution scope against the retained raw originals before
calling the generic runner. A mismatch produces an atomic blocked preparation
result with no financial values, digest or state; a reused artifact destination
replaces its previous completed result. This is a canonical transport check,
not a native financial guard. The generic module runner/CLI instead accepts
trusted prepared typed bindings and does not parse this profile's raw envelope.
Calling it directly requires the caller to establish that correspondence.
Neither interface authenticates external source facts.

Observations compare exact fractional UTC Instants, including submicroseconds
and supplied numeric offsets, including lowercase `t`/`z`. Original `-00:00`
means known UTC with unknown local offset: physical UTC transport uses `Z`, while
raw lexemes, explicit field-path labels and the unknown-local-offset meaning
survive in original detail. No local date or zone is inferred. No-offset times,
leap seconds, malformed spellings and normalized UTC dates outside0001..9999
reject. Terms must cover the whole period and be known by every original row;
rows precede their complete population, and population observations are at or
after period end and strictly before cutoff. No ambient timezone is inferred.

Generate the descriptor and four fresh unbound templates with:

```powershell
python -m cases.participation-bases.build_modules
```

The25 independent oracle methods and17 reference/adapter/checker methods compare
all material outputs, dimensioned options, asymmetries, exact fractions,
zero/empty/split/equal contributors, Unicode/raw lexemes, original scope/time
controls and invalid unused data. Reference final and same-complete-input preview
bundles use the validated completion loader and contain no closing cells. The
separate native selector covers four methods plus two asymmetric controls and
explicitly compares the Python-emitted target when run. The accepted native/compiled/publication evidence and its exact limits follow below.


## Accepted bounded execution evidence

The final mechanical-wrapper reference freeze is
`participation-bases-reference-34f381db`:42 methods and8 completed reference
bundles. The earlier41-method snapshot and the prepared/raw mismatch diagnostic
remain archived. Current maina0/c287/a7 passes43 methods (25 oracle,17
reference/adapter/checker and one six-case native selector),75.303439s, with no
failures/errors/skips/source drift; build98 and both smokes pass. That native
selector compares reference, native IR, native-emitted and separately
Python-emitted values through the default array-v1 path.

A separate physical4b586441 import-only snapshot qualifies25 named bounded
compact-v2 cases across four financial paths and validated complete publications:
all four policy controls, both unit policies' asymmetric money/quantity cases,
fractional results, zero and empty for every policy, preview, exact temporal
markers/knowledge boundaries and two native source failures. All original
numbers/timestamps/Unicode and unknown-local-offset labels survive. All supplied
bindings pass the selected mechanical preparation check before generic execution.
The whole original-fact result is compared, not only earned totals. Compilation
retains1GiB/180s; runtime/audit/reader/reference retain256MiB/60s and existing
wire/logical/node limits. Separate Python emission is compiled and executed
without a direct-olean or interpreter fallback.

This is composite evidence: the first compact campaign completed17 positive/
preview controls then FAILED because an intended native-scope test was actually
rejected by canonical Id<Pool> scope admission. Its overall status stays FAILED.
Fresh source-negative follow-up uses a typed Text currency mismatch and a late
terms observation (native BASE_ROW_SCOPE/BASE_ROW_OBSERVATION), while a separate
six-case follow-up covers remaining zero/empty policy combinations. No source
code changed between these snapshots. These are separate layer credits, not a
fictional passing25-case single run. The source guard rejects bad originals;
the wrapper independently rejects inconsistent prepared transport, including
reused-success destinations.

All paths are under the external SPL artifacts root. Exact records:

- `participation-bases-main-integration-20261123-a/verification.json`
- `participation-bases-native4-20261123-a/verification.json` and `terminal-source-audit.json`
- `participation-bases-native4-negatives-20261123-b/verification.json`
- `participation-bases-native4-boundaries-20261123-c/verification.json`

Native4b records retain81c8/d792/77a pins; main records retaina0/c287/a7.
They are not repinned or a latest whole-project regression. Admission32rows
per table is not an all-bound Cartesian native capacity promise. No emitted
target decision coverage, state carry, FX, bank execution or compiler proof is
claimed by this stateless method. Source/descriptor/templates/tests remain
frozen; this evidence section is the sole post-run README addition.
