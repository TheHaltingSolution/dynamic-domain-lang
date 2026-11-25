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
On an allocated receipt, the existing lineage `policy_ref` names the decision
that authorized the applied weight. The lineage `allocation_id` locates the
full original allocation, including its separately supplied policy reference.

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
known. Failed declared reference checks can locate a missing member in a
directly addressed row. Output scope and failed reconciliation identify the
corresponding result port. The binding check, source assertion and
post-execution reconciliation retain their own stages.

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

## Verification

The report candidate `9e8e5fce56d021a8fe3f887a816c738427c0133a`
passes the pinned build and both native smokes, plus 62 focused methods in
203.590 seconds. An overlapping five-method cohort checks the precise
reference pointer and the original RQ-07 and LG evidence links in 28 seconds.
A static inventory resolves 44 tracked output registrations and matches their
declared and checked port sets. Their rendered type shapes agree apart from
one compatible named usage-detail alias. Named record distinctions remain
part of the language's type rules.

At the earlier report checkpoint `379c912`, two retained original-data
publications reload through the public readers. The compact numeric fixture
matches the independent original-packet oracle and retains 1,036 audit nodes.
The array profile's unequal Cedar split produces 10 for Oak and 30 for Pine,
with actual policy terms, reconciliation and 85 audit nodes. The first report
test cohort's missing declared-reference pointer is visible in its retained
failure record.

Reproduction, source archive, logs, original comparisons and evidence hashes
are indexed by `artifacts/spl/report-audit-integration-20261125-a/verification.json`
under the external project root. The final integrated release has separate
verification.
