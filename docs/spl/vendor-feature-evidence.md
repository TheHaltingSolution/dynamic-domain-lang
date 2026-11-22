# Royalty calculation feature evidence

Reviewed 21 November 2026 for LD-02/RR-03. This is a proposed calculation inventory,
not a vendor parity assessment or a declaration that SPL implements every row.
The current comparison baseline is `spl-implementation/0.3.0-dev`, described in
[implementation.md](implementation.md) and [development-plan.md](development-plan.md).
The historical 132-test result is not a fresh execution result for this review.
Existing SV/RQ-07/LG outputs remain 18,000/18,000/35. No baseline pins or executed
test claims are changed by this documentation update.

**RR-03 is answered** by the user-supplied external
`ResearchAgent/documents/SPL_RR03_Coverage_Benchmarks_and_Workload.md`, dated
21 November 2026. It supplies ranked feature recommendations, public development
candidates and synthetic workload brackets. New neutral fixtures, independent
oracles, case interpretation review and measured capacity remain separate gates.

## Evidence strength and scope

**Documented** means official instructions describe behavior. **Advertised** means
an official product page lists a capability but does not specify its full operator
semantics. **Observed** refers only to the existing privately recorded November
2026 Curve Lite synthetic session, not a new run. **Proposed** identifies our
feature priorities and independently authored discriminators. None implies a
historical accounting interpretation or independently verified vendor execution.

The external `SPL_RQ10_Vendor_Interoperability.md`, industry reference and compiled
testing guide were read first. This review refreshes selected official public
sources; it does not copy private trial material, vendor templates or screenshots.
No purchases, outreach, tenant access or held-out research occurred. Online help
pages are independently changing documents, not pinned engine releases.

## Source register

| ID | Official source, inspected 21 November 2026 | Evidence and limit |
| --- | --- | --- |
| C1 | [Curve royalty versus profit share](https://help.curveroyaltysystems.com/article/44-the-difference-between-royalty-profit-share-deals), page updated 13 November 2026 | Documented distinction between receipt royalties with cost recoupment and sharing a selected profit pool; music-label scope |
| C2 | [Curve sales terms](https://help.curveroyaltysystems.com/article/47-adding-sales-terms-to-your-contracts), updated 13 November 2026 | Documented receipt/price/unit bases, participation exception for fixed unit rates, multipliers/reductions; some features are Pro add-ons |
| C3 | [Curve term selection](https://help.curveroyaltysystems.com/article/392-if-multiple-terms-match-a-sales-line-which-term-will-be-applied), updated 21 November 2025 | Documented dimension hierarchy and direct/group specificity; not a universal contract priority rule |
| C4 | [Curve escalations](https://help.curveroyaltysystems.com/article/56-using-escalations-to-increase-or-decrease-royalty-rates), updated 8 July 2025 | Documented date, weighted-unit and value trackers; entire crossing sales line uses old rate; Pro add-on |
| C5 | [Curve deductions](https://help.curveroyaltysystems.com/article/48-adding-deductions-to-your-contracts), updated 18 November 2026 | Documented percentage/alternate-base/unit deductions, calculation stage and selection of one matching deduction; Pro add-on |
| C6 | [Curve reserves](https://help.curveroyaltysystems.com/article/55-using-reserves-to-delay-royalties), updated 18 November 2026 | Documented pre/post calculation bases, positive-sales restriction and future-period release scheduling; stage wording needs verification before an adapter |
| C7 | [Curve cross-contracts](https://help.curveroyaltysystems.com/article/51-using-cross-contracts-to-transfer-or-subtract-royalties), updated 13 November 2026 | Documented conditional component/balance transfers, add-versus-subtract effects and order; Pro add-on, not generic authorized film pooling |
| R1 | [Rightsline royalties](https://www.rightsline.com/royalties/), no release/update date established | Advertised complex allocation, stacking, participant shares, advances and related capability categories; no complete operator contract |
| R2 | [Rightsline feature list](https://www.rightsline.com/features/), no release/update date established | Advertised unit/price/percentage/tiering, caps, guarantees, subscription allocation, correction and accounting categories; exact policy/plan availability unverified |
| R3 | [Rightsline royalty split API](https://api-docs.rightsline.com/financial/create-a-royalty/create-royalty-split) | Existing official REST-v4 metadata evidence; template selections do not prove engine semantics |
| R4 | [Alliant API entry](https://alliant.redoc.ly/), [release documentation](https://alliant.redocly.app/alliant-api-definition-release), [public overview/version JSON](https://alliant.redocly.app/page-data/alliant-api-definition-release/data.json) | Independently retrieved official JSON HTTP200 on 21 November: public metadata marks 8.1 SP5 default/active; overview documents REST resources/item tools, tenant-defined fields and adjustment detail/control totals. Tenant-specific calculation semantics remain unverified |

The current public Rightsline pages broaden the research vocabulary beyond the
initial two methods. Their claims support investigation; they are not numerical
oracles. A Rightsline Rights API example must not be called an Alliant calculation
specification. The existing private Curve observation supports only the small
default/override/zero/mapping-repair/cost subset already recorded externally.

## Proposed calculation inventory

Status below describes the present project at the granularity established by the
implementation report, not a new source-code conformance audit. **Expressions**
means ordinary arithmetic/conditions may express a bounded method while reusable
language/schema support is incomplete. A physical profile or registered policy
can remain absent even where an expression is possible. LD-02 must settle that
distinction in the final conformance ledger.

The original table uses P1 for a proposed next-release candidate, P2 for later
case-driven work and P3 for an explicit broader scope decision. RR-03 instead
uses P0 for next release and P1/P2 for later work. These are different planning
scales; use the accepted release plan for the final priority, not either vendor.

The [LD-02 release decision](release-scope-ld02.md) now proposes C1 as that
broader calculation target, with phased implementation gates. Its inclusion and
ordering of methods govern the proposed release; the P labels below retain
their meaning as evidence-led candidate recommendations, not contradictory
implementation statuses. FX, units, guarantees and generic weighted allocation
can enter later C1 gates while vendor-specific variants remain evidence-gated.

| ID | Calculation behavior and evidence | Current SPL position / concrete gap | Proposed priority |
| --- | --- | --- | --- |
| F01 | Scoped rule selection, explicit zero, overlaps (C3 documented) | RULE-01 priority tables absent; implement explicit numeric priority/tie failure rather than importing vendor specificity | P1 first |
| F02 | Distinct gross/net and negotiated basis definitions (C1/C2 documented; R1 advertised) | SV/LG distinct bases exist; richer source measures and reusable eligible-deduction definitions need case/profile integration | P1 |
| F03 | Share after costs versus costs after share (C1 documented) | Expressions available; separate named methods and tests needed beyond current pilot | P1 |
| F04 | Unit/price royalties and fixed-unit participation exception (C2 documented; R2 advertised) | Arithmetic possible; typed units/price/quantity inputs and registered method support need deliberate scope | P2 |
| F05 | Multipliers/reductions and named independent deduction bases (C2/C5 documented) | Expressions available; stage, selected deduction and composition must be explicit in source/profile | P1 |
| F06 | Capped deductions and cumulative cap consumption (R2 advertised) | Simple min possible; period/vintage cap ledger, cap scope and approval-driven overrides not generally integrated | P1 case-driven |
| F07 | Prospective versus marginal/retroactive tiers, weighted trackers (C4 documented; R2 advertised) | General deterministic ordered fold absent; crossing-row behavior and tracker measure need selected policies | P1 case-driven |
| F08 | Advances, new issues, recovery and remaining balances (C1 documented; R1 advertised) | SV and adopted RR-01 funded-advance scenario implemented; competing claims/vintage priority remain outside that case | P1 composition |
| F09 | Cross-contract deduction versus transfer and pooled loss recovery (C7 documented; R1 advertised) | SV pool is bounded; dependency graph, conserved transfers, authorization and no repeated-balance deduction need design | P2 |
| F10 | Staged reserves and scheduled liquidation (C6 documented; R1 advertised) | Adopted RR-02 V1/V2 mechanism exists; contractual basis-stage reserves, due releases and return application need new case | P1 composition |
| F11 | Multiple participants and capped priority/proportional waterfalls (R1 advertised shares; film evidence separate) | Shares/arithmetic possible; constrained redistribution and deterministic ordered claims need fold/allocation semantics | P1 case-driven |
| F12 | Minimum guarantee and shortfall settlement (R2 advertised) | Simple max possible; guarantee period, eligible credited earnings and whether paid guarantee becomes recoupable state unspecified | P2 |
| F13 | Contracts deducting other licensors' royalties (R2 advertised) | Cross-method dependencies possible conceptually; avoid cycles, specify accrued/paid basis and cap/period identity | P2 |
| F14 | Bundle/component allocation (R1 advertised) | RQ-07 approved fixed weights implemented; dynamic weights, joins/grouping, caps and residual assignment need extensions | P1/P2 |
| F15 | Subscription allocation/defer/prorate by usage (R2 advertised) | Not a current registered method; coverage interval, usage denominator, unallocated revenue and rounding require evidence | P3 |
| F16 | Currency conversion and tax effects (R1/R2 advertised) | USD only; FX date/quote/rounding and supplied withholding facts need selected requirements; tax administration is external | P3 |
| F17 | Late sales, retroactive corrections and amended periods (R2 advertised) | Supplied revised entitlement/payment check exists; full authorized replay/replacement and prospective correction chains absent | P1 selected case |
| F18 | Forecast/scenario calculations (R1/R2 advertised) | Scenario variants possible; forecasting inputs/models and forecasting-vs-issued state separation need definition | P3 |
| F19 | Exact arithmetic, financial-ratio precision, rounding/residuals (project evidence) | Exact USD and five modes exist; broaden boundary/composition tests without assuming vendor cent semantics | P1 |
| F20 | Interest/surcharge and time-dependent cost accrual (filed SV research, not vendor inference) | Expressions possible; supplied reference observations, day count, compounding and cost eligibility need case approval | P2 |

The inventory draws C1/C2/C4/C5/C6/C7 meanings from the linked official help
instructions and R1/R2 categories from the linked official product pages. It does
not infer a missing vendor capability when public detail is unavailable.

## Synthetic discriminators for feature selection

All values in this section are project-authored synthetic arithmetic, unexecuted
in either vendor. They specify competing semantics, not approved agreement rules
or new goldens for existing cases. Require independent hand review and a neutral
financial oracle before accepting a new executable method.

| Test | Explicit assumed policy and expected result | Error exposed |
| --- | --- | --- |
| D01 Rule priority | 100 receipt, default 20%, Canada higher priority 40% → 40; highest-priority zero → 0; equal winning priorities → ambiguity | Accidental first-match/default or treating zero as absent |
| D02 Cost stage | Revenue 1,000, costs 500: 80% revenue less full costs = 300; 80% of profit = 400 | Conflating royalty and profit-share methods |
| D03 Named alternate base | Net 100, gross 110, royalty 50%, deduction 10% of gross: before share → 44.50; after share → 39 | Applying an absolute-base deduction at wrong stage |
| D04 Unit participation | 10 units × 0.20 unit amount, allocated participation 50%: participation-sensitive → 1; explicitly participation-independent → 2 | Unconditional reuse of participation multiplier |
| D05 Tier crossing | Opening units 95; first line 10 units and revenue 100; second line 5 units/revenue 50; old/new rates 10%/20%, trigger 100: whole crossing line old → 20 total; marginal split → 25; whole first line new → 30 | Unstated threshold/row granularity; different policies require different named methods |
| D06 Scarce priority | Cash 70, first claim 50, second 40: pay 50/20, carry second 20; same-tier proportional 5:10 claims with cash 6 → 2/4 | Treating equal priority as equal amounts or ignoring remaining caps |
| D07 Cap carry | Opening used 80 of cap 100, eligible cost 30 → current deduction 20, closing used 100; next cost 5 → zero absent authorized reset | Per-row cap substituted for cumulative cap |
| D08 Guarantee | Period minimum 100, eligible credited earnings 70, no prior guarantee credit → shortfall 30; earnings 120 → zero shortfall | Double-counting guarantee and earnings; advance recoupability is a separate policy |
| D09 Transfer identity | A current income 50 transferred once to B → A transfer-out 50, B transfer-in 50. Replay from the same opening reproduces that one transfer; duplicate event identity cannot apply it twice, and publication/retry must not commit it again | Subtracting opening-plus-current unpaid balance repeatedly; confusing deterministic replay with automatic no-op calculation |
| D10 Subscription denominator | Pool revenue 120, accepted usage A=1/B=3 → 30/90; no accepted usage → declared carry/error, never division by zero or invented equal split | Unspecified denominator and no-activity policy |
| D11 Reserve lifecycle | RR-02 adopted V1 and V2 remain isolated; no release can consume the other's balance; due release and realized return are distinct events | Reopening adopted policy or treating a generic reserve keyword as complete stage semantics |
| D12 FX/withholding | Explicit quote 1 EUR=1.10 USD: EUR100→USD110; supplied 10% withholding on that converted base→USD11 withheld/USD99 cash due, gross entitlement110 | Inverse FX quote, wrong base and conflating entitlement with payment; hypothetical only |

D02/D03 are aligned with documented method distinctions; no vendor output was
used to derive the expected values. D05 deliberately shows why a language must
declare a policy rather than inherit Curve's crossing-line convention. D06's
film waterfall needs its own public development clause and approved allocation
interpretation. D11 adds composition coverage without requesting RR-02 again.

## Accounting pipeline versus external operations

Adapters own source parsing, aliases, normalized dates, lineage and input control
totals. Contract economics own eligibility, attribution mandated by an agreement,
named bases, selected rates, caps, gates, recoupment, reserves and resulting state.
The run wrapper owns pinned snapshots, validation, atomic output/state publication,
replay identities and deterministic reporting. Dynamic joins/maps/folds are
language/runtime capabilities; an import/export layout is an adapter contract.

Rights administration, availability/conflict checks, signing, portals, approval
routing, bank transfers, GL posting and tax filing are external operations. They
may provide typed facts used by calculations. Their existence in a vendor suite
does not require SPL to implement their UIs or administration. Rightsline's
[feature page](https://www.rightsline.com/features/) advertises both accounting
events and workflow facilities; these categories should remain separate.

## What the evidence does not yet answer

Public Rightsline categories do not establish exact tier crossing, cent rounding,
cap resetting, guarantee crediting, reserve bases or correction replay behavior.
Curve's detailed instructions still leave exact tenant/version behavior and some
ties or stage wording to verify before a translation adapter. Current Pro labels
are documentation context, not a recommendation to purchase access.

There is no evidence here of complete SPL coverage, broad vendor equivalence,
independent historical reproduction or measured large-input performance. See
[RR-03 status](research-request-rr03.md) for the answered request and remaining gates.

## RR-03 public development candidates

The response recommends rule selection, validated allocation/grouping and one
ordered accounting case first. Keep the two existing methods, then promote the
following in order. The checkpoints are supplied hand-derived synthetic scenarios
tied to public clauses, not historical accounting pairs or newly executed goldens.
Each needs a neutral fixture, case-specific interpretation review and separate
financial oracle. This integration independently verified Alliant metadata;
the clause interpretations/checkpoints below are attributed to RR-03.

| Rank | Development candidate and coverage | Supplied synthetic checkpoints | Promotion gate |
| --- | --- | --- | --- |
| 3, first addition | Angel 010–Mofac, *King of Kings*, signed 26 February 2025, §5(a)(vi), Exhibit C §4.1 and Exhibit D §4(b): Guild platform denominator allocation | Gross1,500 − marketing375 − other costs125 = net1,000; filmmaker pool500; title170/1,000 minutes →85, other titles415. Another1,000 other-title minutes →42.50 | Complete metric/denominator, cost eligibility, precision and collection-account linkage; isolate Guild from ordinary distribution. [Filed agreement](https://www.sec.gov/Archives/edgar/data/2060101/000110465925022517/tm258018d1_ex6-2.htm) |
| 4, ordered accounting | MQP–Lions Gate TV, 25 July 2007 Exhibit 10.42§§4.1,6.3–6.4,7.2 plus 10.40: actual-payment/dispute escalation and receipts-limited correction | Paid tracker900→1,000. Three100 receipts yield fees10/10/20=40, adjusted260 under named agreement-date policy. Actual-date sensitivity fee50/adjusted250. Correction10 with capacities4 then12 applies4/6, closes6/0 | Pin trigger effectiveness, same-day order, dispute facts, receipt capacity and waterfall role; isolate second project. Same Lionsgate development family. [Distribution exhibit](https://www.sec.gov/Archives/edgar/data/929351/000095014807000187/v32671exv10w42.htm), [RP companion](https://www.sec.gov/Archives/edgar/data/929351/000095014807000187/v32671exv10w40.htm) |
| 5, optional waterfall | FAME–Roundlake, 1 August 2005 Exhibit 10.1.32§§7A,10: fee, expenses, proportional principal and residual split | Opening capital80/20. First100 receipts −fee25 −expenses15 leaves60 → principal48/12, closing32/8. Next100 −fee25 leaves75 → principal32/8 then residual35 split17.50/17.50 | Confirm capital/expense balances, proportional priority and competing third-party participation before selecting the bounded waterfall. [Filed exhibit](https://www.sec.gov/Archives/edgar/data/1309152/000094344006000046/exh10132.txt) |

Ranks 1–2 remain SV and LG-01. RQ-07 intake versus SV intake and readable versus
original syntax do not add independent methods. Angel adds a family; MQP adds
ordered economics within Lionsgate; optional Roundlake adds capital recovery.
Three-to-five is the overall development corpus target, not five new additions.
No held-out detail is part of these disclosed development cases.

## RR-03 workload brackets and dynamic extension

The response's brackets and budgets are **synthetic and unmeasured**, not observed
per-settlement film distributions or SPL capacity results. The60/30/5/5 mix means
receipt-parent/cost/evidence/lineage records. Include a cost-heavy counterprofile
and vary rule counts/match multiplicity. Count a canonical parent once for the
input limit; count its allocation children separately for projected economics.

| Synthetic bracket | Topology/fan-out | Proposed warm budget, unmeasured |
| --- | --- | --- |
| 100 inputs | 2titles;10% of60 parents split2ways →66 projected receipts | p95≤5s |
| 1,000 inputs | 8titles;600 parents,10% split2ways →660 projected receipts/120 allocation rows | p95≤15s per close |
| 10,000 inputs | 40titles;6,000 parents,10% split4ways →7,800 projected receipts/2,400 allocation rows;4/8 sequential quarters | p95≤60s per close |
| 100,000-input portfolio | Balanced25×4,000 independent components versus shared80,000 pool plus20×1,000 independent components | Balanced≤10min bounded workers; characterize hot pool first |
| Limit/fan-out stress | 99,999/100,000/100,001 inputs;60,000 parents with20% split8ways →144,000 projected receipts/96,000 allocation rows; separate32-way tail | Characterization only |

The 100,000-input guard and 180-second subprocess limit are resource checks, not
capacity evidence. Passing the count limit does not promise completion. Identify
actual hardware, cache state, workers and audit mode; the response suggests an
example 8-core/32 GiB/SSD machine. Record cold/warm stage time, p50/p95, CPU/memory,
input/projected/output sizes, rule matches and trace nodes/edges/bytes. Three cold
and 30 warm runs are a proposed starting protocol, not results. Retain failures.
The response's tiny stored-trace sizes are artifact observations, not per-row
scaling coefficients; this update did not independently remeasure them.

Shared pools/gates, bundle parents, platform denominators and correction chains
connect work into coordinated scopes. Partition independent components before
parallelizing; preserve ordered events, predecessor identity and exactly-once
state advancement. Permitted anonymized real-close count/topology/elapsed/audit
summaries are still useful before external turnaround commitments. Vendor or
industry aggregate volumes cannot provide that distribution or an SPL result.

Broad coverage also needs a deliberate **dynamic extension experiment**, not just
dedicated hardcoded case profiles. Record a parameter change, a new method from
existing operations, reusable sugar and any genuinely new core capability, with
effort and compatibility evidence. Follow the integration owner's
[extensibility experiment](extensibility-experiment.md). This is disclosed
development work, separate from independently custodied held-out evaluation.
