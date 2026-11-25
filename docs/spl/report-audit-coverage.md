# Report and audit coverage

The bounded legacy and registered module runners return calculated or
provisional results. They report issuance as `unissued`. Payment has its own
evidence requirements. A completed publication identifies the files belonging
to one invocation and checks their bytes before exposing its result.

| Supported profile | Report and audit evidence | Scope |
| --- | --- | --- |
| Legacy SV and RQ-07 | Pool statement, per-title amounts, source batch controls, funding-based shares, receipt/allocation and cost-date lineage, input dispositions, movement and closing boundary. The RQ-07 control reconciles 33,000 earned, 15,000 recouped and 18,000 payable, with no evidenced payment. | The share of pooled recovery remains at pool level. Ineligible costs and invoices contribute to their own financial spaces. |
| Legacy cleared LG | Selected branch and financial comparison, actual policy terms, explicit gate and worksheet evidence, opening and closing movements. | This profile requires the supplied cleared-gate evidence, crossed group and single work. |
| Registered module interface | Results keyed by emitted port, statement and detail views, declared reconciliation ports, policy values and source navigation, final state transitions. The Cedar fixture checks recipient attribution, including an included-zero result. The readable two-participant fixture checks distinct outputs and IDs after a public reload. | The descriptor defines the role and checked type of each output. The admitted package must cover every scoped ID used in a result. |
| Numeric precision | Exact inputs, original policy and ID coverage, row amounts, pre-round and rounded totals, and signed rounding bridge. The half-even row fixture gives 0 at row placement and 0.01 at aggregate placement with a 0.01 bridge. | The named case wrapper qualifies correspondence with the complete original packet. A generic prepared-input run depends on the preparation boundary. |
| Registered burden, gate, correction and reserve cases | The case-specific reports expose requested/applied amounts, original contributions, branch eligibility, earlier issued versus actual paid values where supplied, and scope-qualified closing movements or restatement lineage. | Consult the specific qualified profile and historical evidence for its original-data and state reviews. These cases have different report shapes and policy assumptions. |

See the [canonical run contract](data-and-run-contract.md), [module
interface](module-interface-v1.md), [numeric precision
fixture](../../cases/numeric-precision/README.md), [case qualification
index](session-handoff-2026-11-25.md) and [run metadata](run-dates.md).

Legacy `evidence_to_target_lineage` links exact original event IDs in the owned
`canonical-package.json` to inputs in `bindings.json`. SV groups funding IDs
by picture and retains the complete-population reference. A covered picture
with no funding events has an empty ID list. LG links its three evidence
inputs to the corresponding hurdle, gate and worksheet events. This keeps
original evidence navigable alongside the existing receipt and cost lineage.

## Audit and diagnostics

Both native profiles decode emitted and closing values by their checked
types. This preserves Text records with fields named `numerator` and
`denominator` even when the two strings could spell a fraction. The historical
array trace view uses untyped normalization for fraction-shaped values.
Use the raw compact-v2 iterator when interpreting such trace records.

The native compare paths check failure codes against the independent
reference implementation before publishing its message and any authored
source span. The native trace keeps the observed failure and skipped nodes.
Native observation-limit failure still stops before emitted execution.
Pre-source binding scope diagnostics locate a nested input field when one is
known. Output scope and failed reconciliation identify the corresponding
result port. The binding check, source assertion and post-execution
reconciliation retain their own stages.

Compact-v2 keeps the complete native logical graph with original statuses,
values, dependencies and consumed-file pins. A blocked run with an error
graph can be inspected. A preflight block or interrupted publication exposes
no financial or state authority. A preview can show prospective movements
and has no consumable closing cells. A v1 carry receipt qualifies the exported
closing cells under its bounded reader contract. Calculation, state carry,
issuance and payment remain separate.

See the [compact format and reader](compact-publication.md), [publication
contract](artifact-publication-design.md) and [v1 carry
receipt](v1-carry-receipt.md).
