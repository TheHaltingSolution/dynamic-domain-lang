# Explicit report and intended issue dates

`B-RUN-DATES` adds optional `manifest.report_date` and `manifest.issue_date` to
both registered `spl-module/1` packages and the existing bounded canonical
profiles. Each is an explicitly supplied Gregorian Date in `YYYY-MM-DD` form,
validated with the existing Date codec, including leap-year and year-range
checks. Omit absent dates; null, timestamp strings and invalid Dates reject.
Legacy packages may omit both fields. There is no default from the invocation
clock, financial period, cutoff, other metadata or ambient local timezone.

These labels record the supplied presentation date and intended issue date.
Their presence does not make a statement actually issued or paid. The generic
runner preserves them in the result manifest and published package. It supplies
neither field to financial inputs, parameters, opening state or source filters.
No relative ordering between report date, issue date, financial period and
observation cutoff is imposed without a selected economic policy.

Financial recognition continues to use the explicitly selected source Date,
period and observation inputs. An SPL program may independently declare a
financial Date port, including a port named `report_date`; that port is an
ordinary explicit semantic input. The metadata exclusion applies only to these
two top-level manifest fields and never recursively excludes similarly named
source facts or input fields.

## Identity and compatibility

Date-only variations compared under **one implementation pin** have the
following effects:

| Identity/output | Registered module | Bounded canonical profile |
| --- | --- | --- |
| `semantic_run_digest` | Unchanged; presentation dates excluded alongside `run_id` | Unchanged; economic manifest fields are selected explicitly |
| Financial output and logical trace | Unchanged | Unchanged |
| Candidate closing quantity, boundary and `prior_result_ref` | Unchanged | Unchanged |
| Result manifest | Retains supplied dates | Retains supplied dates |
| Default `array-v1` `result_digest` | Changes; the existing full-envelope digest includes the manifest | Unchanged; the existing legacy digest excludes the entire manifest |
| Opt-in `compact-v2` `result_digest` | Unchanged; the existing publication digest excludes the manifest | Unchanged; the same publication digest excludes the manifest |
| Published result/package bytes and completion file hashes | Change | Change |

The module closing cell's predecessor reference continues to use the semantic
run digest. It does not switch to the full-envelope result digest. The bounded
profile's distinct existing default digest contract remains intact. The opt-in
compact publisher already uses a separate semantic result digest for both
families: it excludes the manifest and physical audit paths/target build bytes
while retaining logical audit and financial dependencies. This feature preserves
that rule rather than replacing it with the default module-envelope digest.
Publication still
validates the complete referenced file bytes; an unchanged bounded result digest
does not imply an unchanged manifest or artifact file hash.

Adding the new validator and module schema changes compiler/module build pins.
No cross-build digest preservation or transparent rebinding of issued packages
is claimed. Old build-bound packages remain old artifacts; deliberate binding
against the selected implementation is required for new execution. Optional
absence preserves the input shape convention and creates no inferred date.
The financial source, IR, Date semantics and state schema are unchanged.

## Focused evidence contract

[The focused tests](../../Tests/test_run_dates.py) cover each optional field,
both together, reversed/far-past/far-future metadata Dates, leap Dates, malformed
and null inputs, preserved unissued labels, exact same-pin identity behavior,
independent explicit financial Date ports and original incurred-date recognition,
and actual validated publication. The existing invocation-label exclusion is
checked with dates present. Failed reruns publish an atomic blocked result with
empty finance and no consumable state. Saved predecessor carry uses the actual
validated closing cells and leaves the previous result/artifact unchanged;
preview retains supplied dates and produces no consumable state.

Reference-only methods and explicit native compare methods are separate. Native
compare observes reference evaluation, native IR/audit and native emitted values;
this change does not require or claim a new financial method or correctness
proof. Build, indexed build and both smokes qualify the isolated implementation.
Root integration and its new pins remain a separate step from this isolated
candidate. No main compiler or other frozen case files are edited by this lane.
