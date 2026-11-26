# SPL data and run contract

Status: proposed draft 0.1, 15 November 2026. This is a logical and transport specification for implementation review, not an implemented parser or a production accounting schema. The language reference controls calculation definitions; this document controls their input and output boundary. All changes below require fixture validation before a schema freeze.

Research integration: 20 November 2026. The additions below reconcile the
research responses without declaring a frozen schema. See the
[compiler handoff](compiler-handoff.md) for current implementation policy and
the RQ-07 import boundary.

Implementation update: the three bounded physical profiles and their strict
validator now exist, with an [actual mapped RQ-07 package](../../cases/rq07/README.md).
See [implementation.md](implementation.md) for reproduction and limits. Physical
StateCells additionally pin `scenario_id`, and manifests pin fixed resource
limits. Typed allocation/cost authority terms prevent substituting a conserved
but unapproved allocation or deduction. The wider logical schema below remains
a target, and accountant review/schema freeze are still pending.

M1b update, 22 November 2026: verified profile `0.4.3-dev` adds finite dimensional
transport through the separate [`spl-module/1` interface](module-interface-v1.md).
It is implemented and recorded locally on `feature/spl-typed-quantities`.
The published `0.4.2-dev` record remains
[archived](baselines/implementation-0.4.2-dev.json); prior runs and legacy
physical profiles are not silently migrated. The wider logical target below
retains its original scope.

## Ownership and versions

Adapters preserve source bytes, normalize identifiers using a separately versioned mapping, and report rejected or unmapped rows. The schedule determines contractual eligibility, bases, allocation and economic order. A run binds those objects to immutable snapshots. Reporting may format results but must not change amounts.

Use independent versions for `schema_version`, `surface_version`, `core_version`, schedule content, interpretation, adapter, mapping and runtime. Initial version labels are `0.1-draft`; no backward compatibility is promised until a tested freeze. A reader must reject unknown required fields, unsupported versions and unknown enum values. Namespaced extension fields in an `extensions` object may be preserved and ignored only if declared non-economic. Any economic extension requires a supported schema and schedule dependency. Migrations create a new snapshot and record source digest, migration version and resulting digest; they never rewrite a prior run.

## Primitive encodings

JSON is UTF-8 without BOM. Duplicate object keys, nonfinite numbers and trailing content are invalid. IDs are nonempty case-sensitive strings; identifier comparison uses exact Unicode code points after requiring NFC at ingestion. References include namespace and version when the target changes independently. No locale-dependent normalization is permitted.

Exact decimals are JSON strings matching `-?(0|[1-9][0-9]*)(\.[0-9]+)?`, with no exponent, comma or leading plus. Transport preserves the original source representation separately; canonical numeric serialization removes trailing fractional zeros and maps negative zero to `0`. Decimal scale is not a rounding instruction. Rates are exact decimal ratios (for example `"0.075"`) or normalized rational objects `{ "numerator": "3", "denominator": "40" }`; denominators must be positive integer strings, numerator and denominator coprime, and zero represented as `0/1`. Core intermediate amounts may use these same normalized rational objects because division need not have a finite decimal representation. Integers use decimal strings when arbitrary precision is needed. Financial calculation never passes through binary floating point.

A monetary value is `{ "value": "100000", "currency": "USD" }`; currency codes reference a versioned dictionary. One output currency and no FX conversion are supported in the initial executable slice. Other currencies are rejected for that scope. A later explicit FX operator must name the observation, quote direction, date selection, fallback and rounding; supplying an FX table alone does not enable conversion.

### M1b exact quantity and per-unit transport

The finite dictionary `spl.units/1` admits exactly `Download` and `UsageMinute`,
with exact case and no implicit unit conversion. `Quantity<Download>` input is
`{"value":"100","unit":"Download"}`. `Rate<Download,USD>` input is
`{"value":"1.50","per_unit":"Download","currency":"USD"}`. Each `value`
uses the exact decimal-string or reduced rational-object codec above. Floats,
booleans, missing tags and unknown envelope fields fail. Tags survive recursive
decoding and encoding through records, lists, tuples, Options and map values,
and remain present in outputs, audit and successor state. Quantity/rate values
are not interchangeable Ratio inputs. Non-USD rates and FX are unsupported.

Descriptors using these types explicitly require `spl.quantities/1`, codec
`spl-quantity/1` and an `interface.dictionaries["spl.units/1"]` list covering
their used admitted units. Every descriptor in the import closure is checked,
including unused local schemas and export signatures. New dimensional numeric
bounds and conservation targets must carry matching explicit tags. Empty typed
collections retain the declared dimension; scalar zero is not a substitute.
Legacy Money/scalar domain behavior is unchanged.

Any opening type containing a Quantity or Rate, including nested structural
payloads, requires unit `dimensioned:<sha256>` in its state slot, cell and cell
scope. `unit` must occur in declared key fields and the canonical state key.
The hash covers the complete checked type, units, currencies, argument order
and sorted record fields. The public helper
`spl_compiler.modules.dimensioned_state_unit` admits expanded AST input through
the checker first, so built-in structural types such as nested `Period` match
checked Type inputs. Money-only and legacy `structured` state retain their
previous state identity; no issued state is repinned automatically.

Evidence constraints default to `required:true`. A descriptor can explicitly
declare `required:false` to permit an empty evidence collection while still
checking every supplied event's authority, reference, kind and strict cutoff.
The [selected Download witness](../../cases/quantities/README.md) uses that
setting: empty usage plus empty evidence is valid zero activity; every supplied
usage row still requires its referenced evidence in checked source. Every
supplied observation, including unused evidence, must precede cutoff, and
out-of-period supplied usage blocks. Nonnegativity is this case's selected
policy; signed fractional quantities and rates remain valid exact core values.
The [arithmetic matrix](next-core-semantics.md#m1b-implemented-dimensional-boundary)
defines the implemented operations and explicit rounding boundary.

Dates are valid Gregorian `YYYY-MM-DD` values. Timestamps use RFC 3339 with an explicit numeric offset or `Z`; their conversion to a contract date requires a declared timezone and versioned timezone policy. The core consumes already selected dates. Reporting and effective intervals are half-open `[start,end)` and require `start < end`; a user-facing inclusive end date is translated by the adapter with that translation recorded. A source period cannot silently acquire a transaction date.

All listed fields are required and non-null unless marked `?`. An optional absent field is omitted in JSON; explicit JSON null is rejected. CSV uses an empty cell only for an optional missing value; a literal zero is present. Empty strings are not IDs or numeric values. A clause can promote an optional field to required within its scope. Missing, unknown, excluded and zero are distinct states.

## Canonical input records

This table defines schema `0.1-draft`. `Ref` is a typed stable reference, `Money` the tagged value above, `DateRange` two half-open dates, and lists are ordered only where their field contract says so. Foreign keys must resolve within the run closure. A record is immutable; new versions or linked events express changes.

| Record and unique key | Required fields | Optional fields and additional constraints |
| --- | --- | --- |
| Asset: `asset_id` | `asset_id`, `kind` | `parent_asset_id?`, `external_ids?`; kind is picture, series, season, episode, version or bundle; parent graph acyclic |
| Party: `party_id` | `party_id`, `name` | `external_ids?`; name is descriptive, never a join key |
| Role: `role_id` | `role_id`, `party_id`, `agreement_id`, `role`, `effective` | `payee_id?`; role is distributor, participant, funder or rights_owner |
| Agreement: `(agreement_id,version)` | `agreement_id`, `version`, `document_refs`, `interpretation_ref`, `effective`, `asset_ids`, `role_ids`, `calendar_ref` | `amendment_refs?`, `comparative_refs?`; each dependency pinned |
| Interpretation: `(interpretation_id,version)` | `interpretation_id`, `version`, `decisions` | Each decision has `decision_id`, `clause_ref`, `document_ref`, `question`, `evidence_label`, `adopted_policy`, `alternatives`, `scope`, `effective`, `review_status`, `discriminating_case_ref`; `approval_ref?` |
| Mapping: `(mapping_version,mapping_id)` | `mapping_version`, `mapping_id`, `kind`, `source_namespace`, `source_code`, `target_ref`, `effective` | `priority?`, `approval_ref?`, `weight?`; kinds asset_alias, territory, channel, cost_category, agreement_scope or pool_membership; collisions need explicit unique selection |
| SourceBatch: `(source_system,batch_id,version)` | `source_system`, `batch_id`, `version`, `snapshot_locator`, `sha256`, `format`, `adapter_version`, `ingested_at`, `row_count`, `control_totals` | `source_period?`, `replaces_batch_ref?`; totals separate currency and amount kind, with signed and absolute totals |
| FinancialFact: `fact_id` | `fact_id`, `batch_ref`, `source_row`, `event_kind`, `amount`, `temporal_basis` | `asset_id?`, `raw_asset_code?`, `territory?`, `channel?`, `category?`, `counterparty_id?`, `related_party?`, `dates?`, `quantity?`, `external_event_ref?`, `parent_fact_id?`, `correction_ref?`; temporal_basis is event date or source period with its kind |
| Allocation: `allocation_id` | `allocation_id`, `source_fact_id`, `target_scope`, `method`, `authority_ref`, `effective` | Exactly one of `weight` or `amount`; `remainder_policy?`; every complete allocation group conserves source value, weights sum exactly to one |
| EvidenceEvent: `event_id` | `event_id`, `kind`, `subject_ref`, `effective_date`, `observed_at`, `evidence_ref` | `amount?`, `approval_ref?`, `related_event_ref?`, `attributes?`; kinds funding, advance_issue, actual_payment, cap_approval, dispute, resolution, reserve_instruction or correction; clause-specific attributes must have declared types |
| StateCell: `state_key` | `state_key`, `balance_kind`, `agreement_id`, `scope`, `boundary`, `unit`, `quantity`, `provenance_ref`, `policy_lineage` | `participant_id?`, `pool_id?`, `vintage?`, `prior_result_ref?`, `opening_adjustment_ref?`; key is the full economic dimension tuple, never a row position |
| ReferenceObservation: `(series_id,observation_key)` | `series_id`, `observation_key`, `source_ref`, `date`, `value`, `unit` | `currency_pair?`, `quote_direction?`; initial slice permits non-FX reference inputs only when required by a typed schedule |

`scope` is an object with agreement, optional participant, asset set or explicit pool, and any territory/channel dimensions required by the calculation. A scope never silently widens to the whole dataset. Pool membership has a balance purpose and effective interval; crossing for one balance does not authorize crossing for another.

Financial event kinds are `cash_receipt`, `invoice`, `sale`, `incurred_cost`, `refund`, `reversal`, `actual_payment` and `adjustment`. A signed amount measures that event kind: receipts and costs are normally positive in their respective amount spaces; refunds/reversals negate their referenced source effect. A cost is subtracted by a schedule operation, not by changing its sign on import. Negative amounts require an allowed kind and referenced correction policy. Fact IDs are globally unique inside the run closure. Same ID with different bytes is an error; duplicate identical IDs are also rejected rather than silently counted or deduplicated. Distinct IDs referring to the same economic event require explicit measure selection or overlap validation. Invoice, sale and cash receipt are separate views, not automatically additive receipts.

An unmapped fact retains its raw code and source amount. Required unmapped references block the affected dependency component. Ineligible mapped facts receive a schedule exclusion reason. A selected zero rate generates a calculated zero result. None of these outcomes are inferred from an absent output line.

`evidence_label` is one of `explicit_clause`, `incorporated_material`, `documented_practice`, `research_assumption`, `unresolved_or_disputed`. `review_status` is proposed, reviewed or approved. Approval is a supplied evidence reference, never a status invented by execution. A deliberately selected research assumption permits a labeled reconstruction, not a claim of historical replay.

## CSV profile

Use UTF-8, comma delimiter, double-quote escaping by doubling quotes, one header row, and LF record separators on export. Import may accept CRLF and records must be parsed with a CSV parser, including quoted newlines. Reject duplicate or unknown headers, ragged rows, invalid quoting and unrecognized required codes. Column order is irrelevant on import and fixed by the export profile. Money is flattened as `amount_value,amount_currency`; foreign keys use their stable ID columns. Structured records use JSON or explicit reference tables rather than embedded ad hoc lists. Source rows have physical record numbers from the CSV parser, distinct from line numbers. Preserve byte snapshots and original row identifiers before normalization.

## Validation and run status

Validation proceeds through bytes and schema, identities and foreign keys, mapping and temporal selection, schedule-required fields and policy, then calculation invariants. Errors have stable codes, source pointers and dependency scopes. Never substitute zero for missing data or a failed expression. Zero denominators, unauthorized negative balances, overlapping unresolved rules, mixed currencies and broken allocation conservation block affected calculations.

Default execution is atomic for the declared settlement scope: any blocking error yields diagnostics and reconciled input dispositions but no final payable or consumable closing state. Explicit diagnostic preview mode may expose unaffected components only after proving they share no pool, gate, state or aggregate with the blocked component. Preview results have status `provisional`, cannot be used as opening state, and cannot be presented as a reconciled statement. Research alternatives run as distinct scenario manifests. Warnings do not change amounts; any economic override is a separately pinned policy/event.

Input disposition codes are `rejected`, `unmapped`, `excluded`, `included`. Calculation outcomes distinguish `calculated`, `calculated_zero`, `blocked`, and `provisional`. A row may contribute to multiple named accounting views, each reconciled separately; it must not be counted twice inside one view without a declared operator.

## Run manifest

A manifest requires `run_id`, `schema_version`, `surface_version`, `core_version`, `schedule_ref`, `interpretation_ref`, `mapping_refs`, `batch_refs`, `reference_refs`, `parameter_ref`, `opening_state_ref`, `period`, `calendar_ref`, `output_currency`, `mode`, `compiler_build`, `runtime_build`, `input_mode` and `cutoff`. The refs resolve to immutable content hashes and versions. `mode` is final or preview. `input_mode` is full_snapshot or explicit_delta; v0 implementation starts with full_snapshot. Delta mode remains unsupported until overlap, correction and opening-state reconciliation tests exist. Optional lineage fields are `supersedes_run_id`, `restates_period` and `scenario_id`. A rerun is a new invocation; publishing a result does not imply a bank payment.

Compute a separate `semantic_run_digest` from the canonical ordered dependency closure, schedule/core/schema versions, selected parameters, period, cutoff and opening state. Exclude run ID, local paths, ingest timestamps and runtime wall clock unless a field is explicitly a selected economic input. Preserve implementation build IDs for replay even where their business result agrees. JSON dependency arrays representing sets are sorted by stable key; ordered economic sequences retain their semantic order. Hash raw source bytes separately from normalized logical inputs. Initial canonicalization should be implemented and tested before any hash is treated as a portable identity.

A minimal logical binding looks like this; refs are illustrative names, not real hashes or a ready-to-run fixture:

```json
{
  "run_id": "sv-q1-r1",
  "schema_version": "0.1-draft",
  "surface_version": "0.1-draft",
  "core_version": "0.1-draft",
  "schedule_ref": "sv-pilot@draft1#sha256:<digest>",
  "interpretation_ref": "sv-reconstruction@draft1#sha256:<digest>",
  "mapping_refs": ["sv-mapping@1#sha256:<digest>"],
  "batch_refs": ["synthetic-sv@1#sha256:<digest>"],
  "reference_refs": [],
  "parameter_ref": "sv-terms@1#sha256:<digest>",
  "opening_state_ref": "sv-opening@1#sha256:<digest>",
  "period": {"start": "2026-01-01", "end": "2026-04-01"},
  "calendar_ref": "calendar-quarter@1#sha256:<digest>",
  "output_currency": "USD",
  "mode": "final",
  "input_mode": "full_snapshot",
  "cutoff": "2026-04-15T00:00:00Z",
  "compiler_build": "not-implemented",
  "runtime_build": "not-implemented"
}
```

## Results and audit contract

Return a structured result envelope with status, semantic digest, run metadata, statements, detail, trace, exceptions, closing state and reconciliation. Each statement key is `(agreement,participant,scope,period,currency,scenario)` plus run identity. Each line includes a stable business key, amount kind, exact pre-round amount, reported amount, source rule ID and trace node. A revision keeps business keys comparable and changes run identity. Actual payment is shown separately from payable and requires an evidenced payment record.

A trace node contains `node_id`, `kind`, `scope`, `rule_id`, `clause_refs`, interpretation version, ordered operand refs, fact/source-row refs, mapping refs, state refs, exact operands/result, rounding policy, selection reason and output refs as appropriate. Aggregate nodes reference constituent nodes. Branch nodes record selected branch and predicate; an unselected lazy branch is marked not evaluated, with no invented value. A greater-of node records both evaluated candidate amounts and tie policy. Logical node identities derive from rule, scope and contribution keys, not allocation address or execution order. The canonical trace is a dependency DAG serialized in topological order, choosing the smallest stable node key among ready nodes; optimizations must preserve these logical observations.

Closing cells use the opening state key dimensions and explain every movement. For a nonnegative advance: closing = opening + issued + approved increases - recovered - approved decreases. A reserve uses its own additions/releases and vintage. Payment arrears, cumulative fees and funding meters have distinct units and movement rules. A restatement starts from the approved opening boundary, not its superseded closing result. Replaying subsequent periods creates a new lineage. Prior actual payments remain facts; never pay a historical payable again merely because the period was recomputed.

For each source amount space and currency, reconcile signed totals through rejected, unmapped, excluded and included dispositions. Malformed amounts have an unknown numeric contribution; publish the count and unresolved control-total difference and block final reconciliation rather than inventing a total. Allocation reconciles children plus assigned remainder to parent. Basis reconciliation names all add/subtract operations; settlement reconciles earned, offsets, reserve movements and payable; state reconciles opening plus movements to closing. Source control totals do not add incompatible amount kinds or duplicate accounting views. Pool offsets remain pool-level unless the schedule supplies a justified attribution rule.

## Initial schema review gates

Before freezing, adapt and validate the supplied RQ-07 synthetic Skouras receipt/cost-to-statement package and build a separate Lionsgate rolling-state package; validate JSON and CSV round trips, correction/alias reruns and exact numeric serialization. RQ-07 is canonical-like research input, not schema-conformant input already accepted by a compiler. Add machine-readable schemas and real content-addressed manifests during compiler implementation. Bounded schedule arithmetic has received reported numerical review; full reader/interpretation review and independent review of RQ-07 remain incomplete. Vendor adapters remain separate named profiles with documented source granularity and field equivalence.

## Linked record examples

These fragments illustrate the canonical field shapes. They are not a complete run closure: the referenced batches, parties, agreements, source snapshots and interpretation decisions must also be present before validation succeeds.

```json
{
  "fact_id": "sv-r-a",
  "batch_ref": {"source_system": "synthetic", "batch_id": "sv-q1", "version": "1"},
  "source_row": "receipts.csv:record-2",
  "event_kind": "cash_receipt",
  "amount": {"value": "100000", "currency": "USD"},
  "temporal_basis": {"kind": "cash_received_date", "date": "2026-02-10"},
  "asset_id": "picture-a",
  "dates": {"cash_received_date": "2026-02-10"}
}
```

```json
{
  "state_key": "sv/skouras/participation-prepayment/pool-1/USD",
  "balance_kind": "participation_prepayment",
  "agreement_id": "sv",
  "scope": {"agreement_id": "sv", "pool_id": "pool-1"},
  "boundary": "2026-01-01",
  "unit": "USD",
  "quantity": "15000",
  "provenance_ref": "synthetic-opening-policy@1",
  "policy_lineage": ["sv-pilot-assumptions@1"],
  "participant_id": "skouras",
  "pool_id": "pool-1"
}
```

The corresponding successful pool statement reports exact USD amounts: earned `33000`, recovered `15000`, payable `18000`, closing participation prepayment `0`. It does not infer a payment event. The closing cell retains that state key, advances its boundary to `2026-04-01`, sets quantity to `0`, and links the result and `-15000` recovery movement. The picture-A earning line is `13000`; its trace references the `100000` receipt, `25000` fee, `10000` eligible deductions and `0.2` rate. Picture B contributes the other `20000` earnings. Neither line receives a share of the pooled recovery without a separate attribution policy.

## Identity and correction constraints

When `temporal_basis` selects a date kind also supplied in `dates`, both values must agree. All amount/unit fields must match their declared record and schedule types; a quantity unit must not be inferred from a currency or vice versa. Conditional reference checks apply before arithmetic.

A payment may be projected from either a FinancialFact or EvidenceEvent, but both representations must link to one authoritative economic event identity (`external_event_ref` or `related_event_ref`). Selecting both into the same payment measure is invalid. The same rule applies to advances/funding represented in multiple source views: evidence links do not constitute additional economic movements.

Allocation records additionally require `allocation_group_id`, `method_version` and `policy_ref`; `scenario_id` is required when alternatives coexist. A group identifies one source amount and one selected method/policy/scenario. Only one complete group may be selected per source amount and destination measure in a run. Validate conservation within that group, not by pooling alternative methods. A method producing a fractional remainder requires an explicit remainder destination or a declared unallocated remainder.

Correction, reversal, replacement and batch-supersession references must resolve and be acyclic. A full snapshot declares whether the active measure is an original plus signed reversals/adjustments, or a selected replacement view. It must not count a replacement together with its superseded original as unrelated amounts. Changes preserve both historical records and the selection trace. A correction event is applied once per economic identity within a run; rerunning a period recomputes from the same opening snapshot rather than applying it again to the prior result.

A deliberately reduced subset scenario is a distinct invocation with explicit selected scope and assumptions. It may illustrate a hypothetical subtotal but cannot be described as an unaffected component of a blocked original aggregate, and cannot reconcile or finalize the original settlement scope. A final synthetic reconstruction is consumable only within its explicitly pinned scenario and state lineage. Preview remains non-consumable.

## Research integration and RQ-07 import profile

Incoming follow-up status, 20 November 2026: this section supplied a written mapping
specification. Engineering subsequently implemented the bounded adapter and
[mapped execution](../../cases/rq07/README.md). The source/demonstration reconciliation is 160,000 received, 33,000
earned, 15,000 recovered, 18,000 calculated and unissued, zero closing prepayment,
and no payment event supplied. These checks do not establish canonical schema
conformance or accountant approval of a mapped output. Before schema freeze,
produce and review the actual mapped package, including control comparison and
lineage, bank-value cash, GL-posted costs, allocation authority, complete funding
evidence and preservation of missing incurred dates.

The 20 November integration uses `SPL_Research_Responses.md` and the detailed RQ-07 package dictionary as supplied research evidence. The package has version `1.0.0`, fixture ID `SPL-RQ07-SV-BUNDLE-01`, and files under the external `ResearchAgent/fixtures/screen-accounting-package/` directory. Its `scenario.json`, `normalized_facts.json` and `expected_statement.json` deliberately use a demonstration envelope. They are not a replacement for the canonical schema above. A versioned adapter must reject unsupported source structure, explicitly map every economic extension, and validate its canonical output; do not weaken unknown-field validation to accept the package verbatim.

### Required mapping decisions

| Source feature | Required target treatment |
| --- | --- |
| Inline scenario deal, roles, approvals and economic rules | Create pinned agreement/role/interpretation objects; approval is `research_assumption` with scenario-only authority, not independent human approval |
| `source_batches` with digest/count but incomplete canonical metadata | Preserve original byte hashes/counts; add adapter version, format, snapshot provenance, recorded ingest timestamp and amount-space controls from the actual adapter run. Do not substitute ingestion for economic dates |
| Numeric numerator/denominator metadata | Convert exact integer values to normalized canonical integer strings without binary-float conversion; preserve original representation and policy identity |
| Invoice line, bank deposit and application joins | Resolve `(invoice_id,line_no)`, `bank_ref`, `application_ref`; match currency and validate no overapplication within this declared complete snapshot. Preserve each amount space and parent links |
| `APP-02` allocation children sharing one economic event | Preserve distinct child fact IDs, allocation group and source parent. Children exhaust the selected parent; sharing an event ID is authorized allocation, not duplicate revenue. Never add parent cash to its own children |
| Bank date March 31, application posting April 2 | Select cash by bank value date under the named profile, retain posting separately, and select observations available before the April 4 midnight UTC cutoff |
| Costs with GL posting but no incurred dates | Keep `posting_date` as the selector; retain known paid dates and leave absent paid/incurred dates absent. A legacy `incurred_cost` event-kind label does not evidence an incurred date. Bind a cost view with `recognition_date` and `recognition_policy_ref`, or use a separately typed posting-date case view; never fill `incurred_date` with posting date |
| `eligibility` deduct/exclude and `approval_id` | Interpret through a pinned scenario cost-policy decision; keep excluded `E-X` in controls and trace. GL classification by itself does not authorize deduction |
| Funding rows before the run period | Preserve as qualifying opening evidence, not current receipts or an additional deductible acquisition cost. Complete snapshot coverage must explicitly establish party/title/as-of population before missing PART funding for A can mean zero |
| Funding events lacking canonical `subject_ref`, `observed_at`, `evidence_ref` | Construct subject/evidence links from the scenario; require a separately supplied recorded time or explicit synthetic observation policy. Do not fabricate a historical observation date from an effective date |
| Opening/closing support fields and output status `calculated_unissued` | Map the balance into StateCell plus linked controls/movements; keep issuance status separate from calculation outcome. A calculated final reconstruction can be unissued; `no_event_supplied` is a payment-evidence status, not a numeric amount paid |

RQ-07 and the original SV-01 schedule have the same expected monetary result but different cost-date assumptions. Retain both named profiles and a test that an incurred-date schedule rejects an input missing that date. The RQ-07 profile must explicitly select GL posting for costs. Keep this economic selection in the schedule/pinned interpretation and the date normalization in the adapter.

### Additional conditional evidence fields

The physical schema implementation must supply typed envelopes for these fields when their selected clause demands them. They are additions to the draft record contract, not permission for arbitrary economic `attributes`.

- Gate attestation: `event_id`, `gate_kind`, agreement and work/group scope, covered interval, `satisfied`, effective date, recorded time, source identity, interpretation reference and evidence class. The broad Contingent Participation Hurdle and work-level True-Cash Breakeven have distinct gate kinds/scopes. A false or missing required attestation blocks this cleared-gate fixture. A throughout-interval attestation may be synthetic; two endpoint balances are not proof of the event path. A linked supplied crossed-net subtotal has its own group scope, worksheet reference, period and policy lineage.

  For LG-01 specifically, the selected outside-hurdle effective date must be
  strictly less than the period start. Equality or a later date yields
  `LG_HURDLE_TIMING_POLICY_REQUIRED` and no finalized settlement/state for this
  seed. This is a case-policy check, not a global date-comparison rule. Its
  separate work-history attestation must still cover the entire period.
- Reserve movement: balance purpose, vintage, amount, creation/application/release kind, distributor condition, affected calculation stage and named basis, effective/recorded dates and evidence reference. A basis-stage video-return reserve cannot be merged with a post-earnings payment holdback. Redacted cap, release timing and vintage recognition remain explicit case parameters/policies.
- Ratio rounding: expression/rule ID, scope, unit of expression (fraction or percentage), expressed decimal places, equivalent dimensionless quantum, mode and policy reference. For the synthetic positive example, two percentage decimals mean Ratio quantum `0.0001`; `0.12345` becomes `0.1235`. This does not authorize rounding all quotients or money amounts.
- Events and corrections: retain effective, credited, earned/nonrefundable, execution, incurred, due, paid, approval and recorded dates independently where applicable; attach corrections and actual payment applications to the relevant issued obligation identity as well as source fact/run identity. Restatement and prospective recognition are distinct selected policies. Absence of a payment event never establishes zero cash paid.

Require source-date precision explicitly: a date-only posting cutoff is not a fabricated timestamp. RQ-07 supplies posting dates, so the named scenario rule admits application posting dates strictly before the cutoff's UTC calendar date (`2026-04-04`), rather than inventing an intraday observation time. Timestamp-bearing sources require the actual instant and declared cutoff comparison. Missing required evidence blocks broader claims, while a deliberately supplied synthetic policy remains visible in the reconstruction lineage.
