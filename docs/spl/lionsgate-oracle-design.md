# Independent Lionsgate cleared-gate controls

23 November 2026. The oracle in [oracles/lionsgate.py](../../oracles/lionsgate.py)
targets the accepted synthetic `lg-cleared@1` / `lg-cleared-v1` method. Its author
used the adopted [readable policy](policies/lg-cleared.md), original canonical
source package, published data schema and requirements. The author did not read
the executable LG `.spl` files, projected bindings, evaluator or projection
implementation. A different author owns native/canonical pipeline comparison.
This is independent financial control for one selected method, not historical
account reproduction, complete agreement coverage or professional approval.

## Neutral input and original source records

The [neutral fixture](../../cases/lg/neutral-oracle.json) has exactly:

```text
schema_version = lg-neutral/1
policy_ref = lg-cleared@1
source_profile = lg-cleared-v1
allocation_authorities[]
package { unchanged original canonical-shaped source records }
```

`package` is an unchanged parsed copy of the original
`cases/lg/canonical-package.json`, including raw financial facts, batches,
allocations, evidence, interpretations, roles, mappings, aliases and opening
state. It contains no compiler-projected receipt/cost views or calculated
control answers. The oracle validates original identities and selected economic
scope itself; it imports only the Python standard library. Exact `Fraction`
outputs retain all material intermediate amounts and original contribution and
evidence identities.

Content-pin retrieval, source-file hashes, compiler/schema identities, emitted
execution, canonical finalization and publication are responsibilities of the
separate runner. This financial oracle does not reproduce their cryptographic
or orchestration checks. Unknown fields in financial facts and the neutral
envelope are rejected; it is not a general implementation of every canonical
schema or metadata constraint.

## Selected policy and financial controls

Scope is the explicit agreement, seller-group participant, single derivative
picture, net pool, USD currency and half-open Gregorian quarter. Agreement roles,
membership, policy decisions and opening state must agree. The net-group scope
does not expand this work's full-receipt gate or gross payout branch.

The outside Contingent Participation Hurdle is a separate supplied attestation.
It must be true, scoped to the agreement, observed strictly before the exact
cutoff and effective **strictly before** the quarter start. A 2026-01-01 effective
date blocks a quarter beginning that day; observing the record earlier does not
replace its effective date. This adopted conservative fixture restriction is
not a resolved historical same-event policy or a professional approval.

Independently, one true work gate-history attestation must cover the exact work
and full quarter. Opening and closing full-receipt gate balances must satisfy
gross `>=` cost; equality is allowed. Endpoint totals do not establish continuous
clearance. The oracle retains the supplied attestation and does not reconstruct
an intraperiod path, latch, crossing row, dip or reopening policy.

Original `cash_receipt` facts are selected by their actual `cash_received_date`.
Invoices are separate context and excluded from cash. The full eligible amount,
including all home-video cash, enters True Cash. The separate payout base is
ordinary cash plus home-video cash times the supplied proxy. This profile
requires an explicit `home_video` or `other` channel classification for each
cash fact; a missing classification cannot silently become non-video cash.

Actual costs use the actual `incurred_date`, never a posting or paid substitute.
Every supplied incurred-cost fact needs an explicit `lg` eligibility decision,
reason and matching original policy `cost_terms`. An explicitly excluded cost
remains visible. Missing incurred dates block even when another date exists.
This checks supplied eligibility authority; it does not independently determine
which historical third-party, affiliate or Soft-Money classifications a contract
allows. Out-of-period source rows are retained with their selected-date reason.

The crossed-net amount remains the single identified, scoped and period-matched
`crossed_net_worksheet`, with the authorized member set and `LG-NET-BRANCH`
authority. Its 175 is not a receipt, override, independently derived net ledger
or evidence that the work gate is clear.

| Control | Baseline USD |
| --- | ---: |
| Opening full gate gross / cost | 100 / 100 |
| Current ordinary / home-video cash | 180 / 120 |
| Current full cash / approved actual cost | 300 / 0 |
| Closing full gate gross / cost / surplus | 400 / 100 / 300 |
| Payout base at proxy .25 | 180 + 120 × .25 = 210 |
| Gross before offset / gross candidate | 210 × .20 = 42; less 12 = 30 |
| Supplied crossed net / net candidate | 175; times .20 = 35 |
| Selected greater-of / calculated payable | 35 / 35 |

The fixed producer-fee offset is a synthetic supplied parameter applied once
to the gross candidate alone, with the explicitly selected zero floor. It is
not subtracted from the net candidate or greater-of earnings. Gross/net equality
is labelled `tie`; exact rational arithmetic has no implicit monetary rounding.
Changing the supplied net subtotal to 150 produces a tie at 30, and to 100
selects gross 30. Changing only the video proxy to .5 leaves full gate gross
400 while changing payout base to 240 and gross candidate to 36.

Synthetic payment holdback is separate state and acts after earnings. With
opening H, addition A and release R, require nonnegative movements, `R <= H`
and `A <= earned + R`; payable is `earned + R - A`, closing holdback is
`H + A - R`. Baseline movements and opening holdback are zero. This is not the
agreement's sourced basis-stage video-return reserve or a vintage/cap policy.

## Allocation, lineage and missing evidence

Allocations consume one original cash parent once. Each original selected group
must match a separately supplied neutral `allocation_authorities` record:
source, group, method/version, policy, scenario, authority, effective interval
and exact weights. Its original interpretation decision must contain the same
allocation terms. Conservation alone does not approve a changed split.

The physical allocation `policy_ref` identifies a selected interpretation
decision, such as `LG-TRUE-CASH`; it does not use the neutral envelope's registry
policy namespace `lg-cleared@1`. Independent pipeline comparison exposed and
corrected that initial interface assumption on 23 November. Both the physical
allocation and separately supplied authority now name the explicit decision;
the oracle independently checks its scope, effective interval and terms. No
decision alias, wrapper relaxation or financial golden changed.

The selected LG profile has one authorized work, so the bounded allocation
witness assigns a registered raw bundle parent wholly to that work. The parent
stays in original facts and contribution lineage; the oracle does not add it
again as direct work cash. Parent graphs must be acyclic, explicit cash parent
plus cash child representations are rejected, duplicate economic event IDs
within a selected amount kind are rejected, and batch row counts and supplied
amount-space controls reconcile the raw population. Invoice parent context
does not create another cash amount.

Raw financial facts in this physical profile have **no `observed_at` field**.
The oracle retains this absence and treats them as the supplied available
snapshot. It does not fabricate observations from ingestion, cash or incurred
dates. Explicit evidence observations use exact fractional-second/offset cutoff
comparisons. Source-byte custody and historical availability of financial facts
cannot be proved from fields that were never supplied.

The result retains original hurdle/history/worksheet records and used review
decisions. Proposed `research_assumption` metadata remains proposed, and
`professional_approval` remains `not_established`. Calculated payable is
`unissued`, with `payment_evidence_status = no_event_supplied` and **no numeric
actual-paid field**. Missing or invalid prerequisites raise an error carrying no
payable or consumable state. Supplied worksheet scope and attestations do not
establish professional approval, payment execution or the broader hurdle's
underlying calculation.

The independent tests cover full versus proxy bases, work-gate equality versus
strict hurdle timing, exact cutoffs, scope, actual-cost dates/authority,
gross/net/tie/floor choices, synthetic holdback, parent allocation controls and
input permutation. They are oracle tests only; native/emitted/canonical
comparison must be recorded separately by the integration owner.
