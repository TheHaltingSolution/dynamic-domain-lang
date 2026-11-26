# Independent Skouras incurred-date controls

23 November 2026. This oracle targets only the disclosed synthetic
`sv-incurred-v1` / `sv-incurred@1` profile. Its author read the adopted readable
policy, requirements, handoff, canonical source records and published JSON
schema, without reading the executable SV SPL or compiler calculation helpers.
It does not interpret the whole agreement or certify professional approval.

The [neutral fixture](../../cases/sv/neutral-oracle.json) preserves an unchanged
copy of the original `cases/sv/canonical-package.json` under `package`. This is
the original fact/evidence/allocation/state population, not projected bindings,
precomputed title funding shares, eligible-cost arrays or an evaluator result.
Historical source dates, source rows, batches, missing fields, funding parties
and opening provenance are retained. Native/canonical comparison belongs to a
separate implementation author after these independent controls are stable.

```text
schema_version = sv-neutral/1
policy_ref = sv-incurred@1
source_profile = sv-incurred-v1
allocation_authorities[]
package { original canonical-shaped source records }
```

The oracle entrypoint is `skouras(data)` in `oracles/skouras.py`. It imports only
the Python standard library and returns exact Fraction intermediates, original
contribution identities and pool state. Its optional `exact_json` helper is
neutral serialization, not the canonical compiler codec. The copied package
remains directly available for a separately authored canonical run. Content
pins, original file retrieval, source-byte digests, compiler/schema identity,
canonical finalization and publication are responsibilities of that runner;
the financial oracle does not claim to reproduce those mechanisms.

Scope comes from the explicit policy agreement, participant, period and pool.
Agreement roles identify the distributor and participant; display names have no
effect. The registered agreement asset set defines the title universe, including
zero-activity titles. Authorized membership is specific to the participation
prepayment purpose and must cover the selected period. Interpretation decisions,
scope, dates, state purpose/currency/scenario and opening alias must agree.

Cash is original same-picture `cash_receipt` amount selected by actual
`cash_received_date` in the half-open Gregorian quarter. Invoices are another
measure and never become cash. Missing cash dates block. Costs are separately
approved by `parameters.cost_decisions`, with the branch, authority and reason
retained. They use actual `incurred_date` in this quarter. Missing incurred dates
block; posting and paid dates are preserved but never substituted. Explicitly
excluded and outside-period facts retain their original identity and reason.
The two branch eligibility schedules remain distinct supplied decisions, even
when their aggregation formulas have the same shape.

The complete funding snapshot must cover exactly the participant/distributor
and registered titles at the quarter opening. Funding amounts are nonnegative
USD face values, approved and observed strictly before cutoff, with effective
dates on/before the opening for the selected valuation. Later effective funding
is excluded from this opening valuation and labelled separately; it does not
silently revise a prior funding share. Missing participant rows establish zero
only because explicit complete coverage was supplied. Funding is a separate
accounting view, never new receipt cash or an automatic additional deduction.

For participant funding S and distributor funding V, positive S selects the
funded branch with share `S/(S+V)` and fee `.075 * cash`. Otherwise the unfunded
branch uses share `.20` and fee `.25 * cash`. Basis is cash less fee less the
separately approved branch costs. Earned is basis times share, with exact
arithmetic and no rounding. Negative earnings block; no loss floor is inferred.

| Picture | Cash | Participant / distributor funding | Fee rate / fee | Approved cost | Basis | Share | Earned |
| --- | --- | --- | --- | --- | --- | --- | --- |
| A | 100000 | 0 / 50000 | .25 / 25000 | 10000 | 65000 | .20 | 13000 |
| B | 60000 | 40000 / 60000 | .075 / 4500 | 5500 | 50000 | .40 | 20000 |

The available opening advance is an approved **supplied remaining** participation
prepayment of15000, with original state key, provenance, policy lineage,
agreement/participant/pool/USD/scenario/boundary. This input is not reconstructed
from historical funded events, and no new funded advance is invented. Recover
`min(sum(title earned), supplied opening)` at pool scope. Thus earned33000,
recovered15000, calculated unissued payable18000 and closing advance0. Recovery
is not allocated back to pictures without another policy. No payment evidence
was supplied; the output labels `no_event_supplied` and has no numeric paid
amount. Payable is not an issued or paid amount.

Physical allocations are checked against separately supplied independent
`allocation_authorities` records. Each record contains source_fact_id,
allocation_group_id, method, method_version, authority_ref, policy_ref,
scenario_id, effective period and `weights:[{asset_id,weight}]`. Source is one
original cash parent, targets are authorized member pictures, weights are exact
and sum to one, and one selected group consumes the parent once. The original
parent remains in the neutral input and lineage; it is not also added as direct
cash after allocation. Altering a conserved split without changing independently
supplied authority must fail. Parent invoice links remain source context, not
additional receipt amounts. Duplicate/overlapping cash representations require
explicit authorization and otherwise block.

Raw financial facts in this physical profile have dates and temporal basis but
**no observed_at field**. The oracle preserves that absence and treats them as
the explicitly supplied available input snapshot. It does not synthesize an
observation from economic or ingestion dates. Explicit evidence observations
are checked with exact fractional-second cutoff comparisons; financial fact
observation-time custody cannot be established from fields that are absent.
Source ingestion is provenance, not receipt or incurred recognition.

`rq07-posting-date-v1` is another profile and is rejected here. Its original
missing incurred dates remain missing, even though its named GL-posting policy
can independently calculate18000. Equal totals do not establish equivalent
recognition methods. SV new advances, negative/signed earnings, historical
restatement, allocation rounding residuals, broad contract eligibility and actual
payment execution remain outside this oracle's declared scope.

Authoring verification on 23 November 2026: `python -m unittest
Tests.test_skouras_oracle -v` passed 18 test methods in 0.024 seconds. These check
the title/pool hand controls, source/date/authority boundaries, original parent
allocation conservation and exclusion, and exact calculation without implicit
rounding. This records independent oracle checks only; it is not a native,
emitted or canonical execution result or a whole-contract review.
