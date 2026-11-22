# SPL requirements and validation plan

Status: initial design draft, updated 20 November 2026 from the research responses
verified November 19. This is a proposed acceptance contract for implementation;
reviewed arithmetic is identified below, separately from unexecuted compiler
checks and policies awaiting domain approval. The specifications form one
versioned draft; no claim of historical reproduction follows from the examples.

## Evidence and coverage boundaries

The controlling design input is the external research handoff
`ResearchAgent/documents/Language_Design_Requirements.md`, proposed v0, November
2026. Its requirement IDs are preserved below. Additional inputs are
`Compiled_Language_Testing_Guide.md`,
`Rights_and_Royalty_Accounting_Industry_Reference.md`,
`Curve_Lite_Workflow_Research_Notes.md`, and
`Curve_Lite_Synthetic_Workflow_Test.md` in that directory. See the source index
in the [design overview](README.md) for local locations. Research documents stay
outside Git; small independently authored fixtures and specifications belong here.

The current research response is `SPL_Research_Responses.md`, supported here by
`SPL_RQ01_RQ02_Skouras_Research.md`, `SPL_RQ05_RQ06_Accounting_Policies.md` and
`SPL_RQ07_Accounting_Package.md`. Review status and custody rules come from
`SPL_RQ08_RQ09_Review_Protocol.md`; restricted evaluation answers are not design
inputs. The earlier [research questions](research-questions.md) remain historical;
only unresolved implementation/review requests appear in
[research followups](research-followups.md).

**Compiler work can start.** The bounded synthetic SV slice has sufficient
economic and fixture detail. The two development schedules have reviewer-checked
arithmetic on the November 15 schedules, but DOC-01 is partial. The targeted
November 20 reviewer follow-up is prepared and has not been sent. RQ-07 has a
reconciled source demonstration, mapping specification and now an
[adapter-produced canonical package and mapped execution](../../cases/rq07/README.md),
and neither historical settlement nor complete contract interpretation has been
approved. These are separate gates, not reasons to delay the bounded compiler.

Skouras–Ventura §§7–9 and Lionsgate derivative works §2.4(a)(ii) are development
families. The examples below reconstruct selected economics using synthetic
facts, approved-cost assumptions and synthetic replacements for redactions.
They do not establish complete coverage of either agreement. Curve observations
motivate workflow tests; its music-domain configuration is neither the oracle
nor the authority for screen-contract economics. A vendor account is unnecessary.

For each payment-affecting interpretation, the future case pack must record
`decision_id`, document/version, clause, question, evidence class, selected
interpretation, alternatives, dates/scope, review status, and one discriminating
example. Evidence classes are explicit clause, incorporated material, documented
practice, research assumption, and unresolved/disputed. A proposed research
assumption may support a labeled scenario; it cannot silently become an approved
contract interpretation.

## Requirement traceability

The surface contract is in [language-reference.md](language-reference.md); the
execution contract is in [core-and-compilation.md](core-and-compilation.md).
This table maps obligations to review artifacts and future executable checks.

| Requirement | Design obligation and review evidence | Acceptance checks |
| --- | --- | --- |
| R-01 Readable economics and evidence | Named clause-backed definitions, visible calculation dependencies, two development schedules, interpretation register | DOC-01, SV-01, LG-01; contract reader can explain the basis, controlling fee/rate, pool and changed result |
| R-02 Versioned data boundary | Independent fact, adapter/mapping, policy, invocation and state identities; schema fields, units, keys and null rules | DATA-01, DATA-02, RUN-01; complete reproducible case manifest |
| R-03 Validate before arithmetic | Required references resolved, strict authoritative mode, diagnostic dispositions distinct from eligible zero | DATA-01, WF-01, FAIL-01; rejected runs cannot expose finalized payable |
| R-04 Scope and priority | Explicit agreement/title/pool membership, version intervals, rule precedence, missing-match and tie semantics | RULE-01, SCOPE-01, SV-02; explanations identify winning and rejected rules |
| R-05 Exact numbers and dates | Exact decimal ingestion and rational intermediates, explicit rounding and calendar/date selectors | NUM-01, TIME-01; exact intermediate and boundary assertions |
| R-06 Different methods over common primitives | SV conditional funding methods; LG separate rolling gate and payout bases, branches, comparison and reserves | SV-01, LG-01, LG-02, RES-01; same facts yield method-dependent amounts |
| R-07 Explicit state and external decisions | Typed opening/closing balances/meters, pool and vintage keys, supplied approval/payment facts, linked corrections | SV-02, RES-01, CORR-01, SCOPE-01 |
| R-08 Deterministic replay | Frozen manifests, explicit ordering, immutable revisions, no implicit clock/network in settlement | RUN-01, WF-01, CORR-01; semantic result and trace replay exactly |
| R-09 Statements and reconciliation | Structured statement/detail/trace/exceptions/state, source controls and economic bridges, scope-accurate reporting | AUDIT-01, SV-01, WF-01, FAIL-01 |
| R-10 Independent core and Lean boundary | Specified core evaluation, separate lowering/emitter boundaries, pinned Lean, frozen held-out protocol | COMP-01, HOLD-01; independent oracle, core evaluator and emitted execution agree |

The handoff's remaining sections impose these additional deliverables:

| Handoff area | Required artifact or constraint | Gate |
| --- | --- | --- |
| Accounting vocabulary | Receipt/basis/earned/recoupment/reserve/payable/payment meanings stay separate | DOC-01 and all numeric cases |
| Responsibility boundaries | Adapter normalization separate from schedule economics; external operations outside pure settlement | DATA-02, RUN-01 |
| Canonical records | Asset; party/role; agreement/interpretation; membership/mapping; batch; financial fact; allocation; external event; state; FX/reference; manifest | DATA-01 schema review covers every present record and every conditionally required field |
| Industry boundary | Stable internal IDs with external namespaces; no assumed universal vendor schema | DATA-02; optional vendor adapter deferred until exact consumer layout and equivalent subset are known |
| Financial operations | Base formation, fees/deductions, recovery, gates, alternatives, reserves, dates and corrections | Numeric cases below; unsupported mechanisms produce diagnostics |
| Output contract | Statement, detail, decision trace, exceptions, closing state, run/revision metadata | AUDIT-01 |
| Development evidence | Clause-to-schedule map and explicit coverage gaps | Case packs and research questions RQ-01 through RQ-06 |
| Freeze decisions | Null/zero, empty groups, duplicates, replacement, overlap, ordering, trace and partial-run status | DATA-01, RULE-01, NUM-01, RUN-01, FAIL-01 |
| Research targets | Three to five sourced cases overall; at least two materially different calculations; independent held-out exercise | Later research milestone, not a first compiler completion claim |
| Proof claims | Separate source/target semantics and trusted assumptions; current toy theorem remains infrastructure only | COMP-01 and explicit theorem scope review |

## Prioritized conformance scenarios

### Clause to schedule coverage

| Source provision | Draft schedule responsibility | Demonstrated scope and unresolved portion |
| --- | --- | --- |
| Skouras–Ventura §7(a) | Named participation-prepayment opening, pooled recovery and closing state | SV-01 remaining balance and SV-02 simple forward carry; historical backward offsets and priority remain unresolved after RQ-02 |
| Skouras–Ventura §8, no acquisition contribution method | Cash-received basis, 25% fee, separate approved deductions, 20% share | Picture A synthetic subtotal reconstruction; RQ-01 supplies category distinctions, while incorporated title records, accrual details and full eligibility remain open |
| Skouras–Ventura §8, acquisition contribution method | Separate adjusted-gross basis, 7.5% fee and supplied funding proportion | Same-picture qualifying SFI funds divided by combined SFI/Ventura funds; later-funding timing and complete eligible records remain open |
| Skouras–Ventura §9 | Quarterly reporting and traceable settlement period | Quarter cutoff fixture only; complete statement/administration obligations require provision review |
| Lionsgate derivative §§2.3(c), 2.4(a), 2.4(d) | Separate broader Contingent Participation Hurdle attainment evidence | LG-01 explicitly supplies a synthetic attainment attestation; the strict-exceeds broader hurdle and work-level equality are different conditions |
| Lionsgate derivative §2.4(a)(ii), True-Cash Breakeven | Full-receipt rolling gate distinct from payout base | Equality reaches work-level breakeven; crossing-row treatment and intra-period dip/recovery remain unresolved |
| Lionsgate derivative §2.4(a)(ii), gross/net alternative | Home-video proxy gross candidate, supplied reviewed crossed-net subtotal, greater-of and explicit fee-offset assumption | Partial selected-provision coverage only; RQ-03 identifies missing net ledger derivation, fee convention and redacted parameters |
| Lionsgate derivative §2.4(a)(ii), applicable reserve treatment | Purchaser-distributor condition, named calculation stages and liquidation within twelve months | Cap redacted and recognition/vintage details unresolved; post-earnings RES-01 remains synthetic rather than sourced reserve treatment |

The map identifies responsibilities, not an assertion that the entire cited
section has been implemented or its interpretation approved. Clause-backed
decisions must be linked to the eventual stable definition IDs during case freeze.

P0 denotes the first end-to-end implementation slice. P1 completes the contrasting
development method and critical state/revision boundaries. P2 is later expansion
driven by approved case evidence. These are test specifications, not test code.
Each case must compare intermediate values, statuses, stable lineage and state,
as well as the final amount. Amounts below are exact USD unless stated otherwise.

### DOC-01 Readability and interpretation review P0

Research status: targeted follow-up reviewers reproduced SV-01, its 12,000
opening-balance variant, LG-01 at the 25% video proxy and the 50% proxy variant.
The accountant additionally supplied the equal-receipts SV and full-receipts LG
comparisons. This completes the reported bounded numeric review, not DOC-01.
Individual task ratings, complete clause trails, wording edits and interpretation
approval remain open. Counsel disclosed no prior exposure; the accountant's
follow-up exposure disclosure is incomplete. Record packet identities and these
limitations before claiming independent readability approval. The reviewer
packet was pinned to the November 15 draft; changed drafts need a version delta.
The targeted November 20 request is prepared, not sent; no new reviewer response
or approval of the November 20 changes is recorded. In particular, the new LG
hurdle timing guard below has not received reviewer approval. The arithmetic
review attaches only to the pinned November 15 schedules and reported variants.

Ask a contract reader and participation accountant to find the selected provisions,
receipt definition, each fee base, eligible deduction schedule, participant share,
recovery scope, rounding boundary and payable in both schedules. Record review
results and disagreements. If neither reviewer is available, record an unmet
review gate. Demonstrate a parameter change separately from a method change.
Removing a required approved interpretation must identify the clause and prevent
an authoritative settlement for its affected scope.

### SV-01 First quarterly settlement P0

Assume cash actually received within the quarter, preclassified eligible costs,
nonnegative earnings, no FX/reserves/adjustments/new advances/payments, and a
supplied remaining participation-prepayment pool of 15,000. Picture B's funding
share is 40,000 / 100,000 = 40%; this share is an input with evidence, not inferred
from receipts. Participant prepayments are not picture cost deductions.

| Picture | Receipts | Fee rule | Fee | Other deductions | Named basis | Share | Earned |
| --- | ---: | --- | ---: | ---: | ---: | ---: | ---: |
| A, no participant acquisition contribution | 100,000 | 25% of receipts | 25,000 | 10,000 | 65,000 | 20% | 13,000 |
| B, participant acquisition contribution | 60,000 | 7.5% of receipts | 4,500 | 5,500 | 50,000 | 40% | 20,000 |

Assert earned = 33,000; recovered = min(33,000, 15,000) = 15,000;
payable = 18,000; closing advance = 0. With opening advance changed to zero,
earned stays 33,000 and payable becomes 33,000. Preserve picture-level fees,
bases and earnings, and pool-level recovery. Do not invent a title allocation of
the pooled 15,000. An attempted second deduction of that prepayment as a cost
must be excluded or rejected under the approved cost policy and identified in
the trace. Distinguish a source acquisition advance included in a contractual
basis from this participation-prepayment balance.

Additional reviewed controls: opening prepayment 12,000 changes payable to 21,000
without changing earnings. With both titles instead receiving 100,000 and their
original costs/shares unchanged, A earns 13,000 while B earns
`(100,000 − 7,500 − 5,500) × 40% = 34,800`; pool earned is 47,800 and payable
32,800 against opening 15,000. This changes receipts, not the method definition.

### SV-03 Event role, funding evidence and new advances P1

On 100,000 cash with no funding contribution, no other costs and zero opening
pool, a qualifying 5,000 Ventura-to-Licensor acquisition advance gives basis
70,000 and earned/payable 14,000. A separate 5,000 participant prepayment under
the expressly selected prospective policy gives basis 75,000, earned 15,000,
recovery 5,000 and payable 10,000. No interest or surcharge is included. This is
a classification discrimination, not permission to apply both treatments to
one economic effect. One acquisition payment may support both qualifying funding
evidence and an authorized basis deduction, with separate observation paths.

For branch selection, a complete snapshot evidencing zero SFI funding selects
the unfunded method, including when both parties supplied zero. A missing SFI
record without completeness evidence blocks the branch. The funded branch with
zero denominator fails. Same-picture funds SFI 40,000 and Ventura 60,000 yield
40%; on a 60,000 basis earnings are 24,000. Adding a later Ventura 20,000 would
yield one-third and 20,000 if the adopted valuation policy includes it. The
effective period and any restatement are unresolved; label competing scenarios.

A separate positive new-advance scenario has Q1 opening 15,000, earned 20,000,
recovery 15,000, payable 5,000 and closing zero. Q2 issues a new evidenced 15,000
advance before the adopted cutoff and earns 10,000, recovering 10,000 and closing
5,000. A Q2 sibling title earning −3,000 blocks the narrow first slice. Explicit
positive-only versus signed-net sensitivity policies would close 5,000 versus
8,000; neither is the default. Reopening Q1's already-paid 5,000 requires its own
authority and overpayment identity, never an automatic duplicate basis deduction.

### SV-02 Explicit carry and pool isolation P0

This is a simple forward-carry research policy, not a reconstruction of disputed
historical crossing. Supply Q1 opening advance 40,000.

| Period | Basis calculation | Earned | Opening | Recovered | Payable | Closing |
| --- | --- | ---: | ---: | ---: | ---: | ---: |
| Q1 | SV-01 | 33,000 | 40,000 | 33,000 | 0 | 7,000 |
| Q2 | A: 40,000 − 10,000 fee − 5,000 costs = 25,000 | 5,000 | 7,000 | 5,000 | 0 | 2,000 |
| Q3 | A: 80,000 − 20,000 fee − 10,000 costs = 50,000 | 10,000 | 2,000 | 2,000 | 8,000 | 0 |

Serialize each closing state and read it as the next opening. An inserted empty
quarter carries 2,000 unchanged. Replacing Q3 with in-pool picture B receipts
40,000, fee 3,000, costs 12,000, share 40% gives the same 10,000 earned and
8,000 payable, with B-only current-period input lineage. An out-of-pool title
must not consume this advance balance. Replaying Q2 from its original opening
must not mutate Q3 or consume the balance again.

### LG-01 Distinct bases and greater-of P1

Use synthetic rates for redactions, a gate already at equality, no new costs or
reserve activity, a reviewed crossed-net subtotal as a supplied input, and a
synthetic fixed producer-fee offset of 12 applied to the gross candidate only.
Separately require an identified synthetic attestation that the broader
Contingent Participation Hurdle has been attained for this pathway. A cleared
work-level gate does not imply that outside hurdle. Missing attestation blocks
this case. The fixture supplies zero reserve activity and a supported crossed-net
worksheet reference; it does not compute the complete crossed-net ledger.

The conservative synthetic timing profile requires the scoped attainment event's
`effective_date < period.start`, honoring the pilot's existing “before the period”
restriction. This is a new implementation precondition, not an interpretation of
historical same-day eligibility and not a reviewer-approved change. With a period
starting 2026-01-01, acceptance checks are:

| Attainment evidence | Expected outcome |
| --- | --- |
| True, correct agreement/pathway scope, effective 2025-12-31 | Baseline earned/payable 35 and normal candidate closing state, provided other pilot preconditions pass |
| True and correctly scoped, effective 2026-01-01 | Timing diagnostic; no final payable or consumable closing state |
| True and correctly scoped, effective 2026-01-02 | Timing diagnostic; no final payable or consumable closing state |
| Absent, false, missing effective date or wrong scope | Required evidence/scope diagnostic; no final payable or consumable closing state |

An observation/recording date does not replace the effective date. Preserve it
separately in provenance. Do not use this guard to infer either side of the broader
hurdle's unresolved same-event recognition policy. SV-01 remains 18,000 and the
valid earlier-attainment LG-01 remains 35.

| Calculation | Expected |
| --- | ---: |
| Opening cumulative eligible full receipts / actual costs | 100 / 100 |
| Current non-video / home-video receipts | 180 / 120 |
| Closing cumulative full receipts / actual costs | 400 / 100 |
| Closing gate surplus | 300 |
| Gross payout base with synthetic 25% video proxy | 180 + 120 × 25% = 210 |
| Gross candidate after synthetic 20% rate and offset | 210 × 20% − 12 = 30 |
| Net candidate with reviewed crossed-net subtotal 175 | 175 × 20% = 35 |
| Greater-of earnings | 35 |

Change only the crossed-net subtotal to 100: net = 20, gross = 30, selected = 30.
Change it to 150: both = 30, selected amount = 30, trace records the tie according
to the comparison policy. The full home-video 120 belongs to the gate while only
30 enters the payout base. Reusing the proxy for the gate fails this test even
if a coincidental final amount remains unchanged. The offset's stage and the
supplied crossed subtotal remain declared assumptions after the RQ-03 response.
Changing only the video proxy to 50% gives payout base 240, gross candidate 36,
net candidate 35 and earned 36, while work-level cash remains 400. Using all
current receipts as the payout base under a separately labeled method gives
gross candidate 48, net 35 and earned 48. The latter is a method comparison,
not the agreed home-video proxy calculation. The synthetic zero floor, gross-only
offset and positive pilot do not establish negative candidate or fee-carry policy.

### LG-02 Gate boundary and ordered crossing P1

Under an explicitly selected `cumulative receipts >= cumulative actual costs`
scenario policy, compare closing receipt totals 99, 100 and 101 against costs
100. Gate outcomes are false, true and true. Gross candidate evaluation is gated;
the net candidate remains independently evaluable. Record whether the fixture
uses a period-closing gate or an ordered receipt-by-receipt gate. Do not assign
contractual crossing-row earnings until an adopted interpretation resolves
prospective/retroactive treatment. A chosen policy gets its own independently computed expectation and
explicit event-order key. A missing required gate policy blocks final status.
The authored cleared-gate pilot should reject below-breakeven opening and ending
recrossing through distinct diagnostics. Endpoint checks alone cannot detect an
intra-period dip and recovery; require an explicit uninterrupted-clearance
scenario attestation, or validate an approved ordered event ledger. Do not treat
two passing endpoint checks as proof of continuous eligibility.

Research crossing sensitivities use costs 100 and opening receipts 80, with
ordered receipts taking cumulative receipts to 90, 120 and 140. Reported alternatives
include 6 versus 7, but the crossing-policy arithmetic remains unresolved for
implementation. None is a golden result or default. Wider crossing, negative
economics, offset carry and reserve policies are deferred; do not select an answer
while implementing the positive cleared-gate slice. Preserve and reconcile each
policy's complete rate/proxy/offset inputs and obtain the adopted treatment before
promoting a crossing sensitivity to an executable golden. The broader hurdle's strict-exceeds condition must
not be replaced with work-level `>=` semantics.

### WF-01 Zero, unknown mapping and repaired rerun P0

Use a project-owned illustrative schedule: default share 20%, Canada override
40%, France 0%, one 15 post-earning deduction, and known-asset receipts of 100 US,
200 CA, 75 FR plus unknown-asset 50 US.

| Snapshot | Included receipts | Quarantined | Earned | Deduction | Illustrative net |
| --- | ---: | ---: | ---: | ---: | ---: |
| Mapping v1, blocked run with diagnostic arithmetic only | 375 | 50 | 100 | 15 | 85 |
| Mapping v2, alias approved and facts revalidated | 425 | 0 | 110 | 15 | 95 |

Final mode with strict validation on v1 emits no authoritative payable. Because these rows share a
contract aggregate and deduction, this is not an unaffected-component preview.
The illustrative 85 is independently calculated diagnostic arithmetic, marked
blocked, rather than a permitted provisional payable or a reconciled result.
Neither it nor partial successor state can become the next run's opening state.
The FR row remains
eligible with zero earnings and contributes 75 to included receipt controls.
The unknown row has a mapping diagnostic rather than zero earnings. Alias repair
keeps original fact/batch/row identity and records new mapping/run identities.
The source total is 425 in both runs; first-run included 375 + quarantined 50
reconciles it. Earlier results remain reproducible.

### DATA-01 Canonical validation P0

For every published record, cover its key, required fields, conditional fields,
unit, nullability and version. Reject malformed decimal/date, unknown schema,
missing amount, broken reference, duplicate ID with conflicting payload, missing
required event date, unsupported currency, missing declared parameter and zero
funding denominator. Explicit zero is accepted where its type permits it. A
missing amount is never zero. Distinguish absent optional field from malformed
field. Verify duplicate-delivery handling separately from a new correcting event
with a linked original. Check allocation weights and amount conservation,
effective intervals, pool membership and replacement/reversal cycles before
finalization. Empty sums return typed zero; missing required selection or state
does not become an empty sum.

### DATA-02 Adapter boundaries P0

Preserve raw code/value, source system, batch/version, row locator, source digest,
adapter version and mapping version. Test quoted CSV fields, optional blank,
explicit zero, line endings and decimal precision. An aggregate period receipt
without a sale date must not acquire an invented date. A sale, invoice and cash
receipt linked to one economic activity must not all enter a cash-received basis.
An adapter cost-category mapping does not itself authorize contractual deduction.

### PKG-01 RQ-07 linked accounting package P1

The delivered external `fixtures/screen-accounting-package/` is shareable,
project-generated synthetic material. Its five raw CSV hashes/row counts were
verified by research, but its canonical-like JSON, inline approvals, missing
implementation identities and optional source fields require an explicit adapter
and schema validation before use as compiler input. Do not silently claim its
JSON already conforms to `spl-data/0.1-draft`. Retain original byte hashes and
logical record pointers through any mapped copy; do not commit private historical
records or vendor material. Accountant approval of this package remains open.
The current deliverable is the reconciled source demonstration plus a mapping
specification, followed by the [bounded implemented run package](../../cases/rq07/README.md).
Before schema freeze, give that package and its validation/reconciliation outputs to the
accountant. Review of the source demonstration alone does not satisfy this gate.

Use Q1 `[2026-01-01,2026-04-01)`, cash selected by March 31 bank value date,
applications posted April 2 and a supplied April 4 UTC cutoff. Costs use GL
posting because incurred dates are absent. This is a distinct intake policy
from the original SV incurred-date projection. Never manufacture incurred dates
from posting, invoice or paid dates. B's approved 5,500 cost remains eligible
despite an unavailable paid date under this scenario. B's unsupported 2,000 cost
is explicitly excluded for its documented fixture reason; do not generalize that
outcome into exclusion of every marketing/overhead cost.

| Independent amount space/control | Expected USD |
| --- | ---: |
| Invoices billed − uncollected | 210,000 − 50,000 = 160,000 |
| Bank deposit = cash applications = allocated title receipts | 160,000 |
| Direct A application | 60,000 |
| Bundle collected amount allocated A 2/5, B 3/5 | 100,000 → 40,000 / 60,000 |
| Raw GL costs = approved eligible + explicit exclusion | 17,500 = 15,500 + 2,000 |
| Separate same-picture acquisition funding | 150,000 = A 50,000 + B 100,000 |
| Earnings − prepayment recovery = calculated payable | 33,000 − 15,000 = 18,000 |

The funding population does not become an additional acquisition cost. Invoice,
bank, application and allocated cash are linked views, not additive receipt
amounts. Validate application totals against deposit and invoice balances and
validate allocation authority as well as conservation. The statement is calculated
and unissued; absent participant cash evidence is `no_event_supplied`, not paid
zero or proof of a newly issued obligation. Closing prepayment is zero.

Discriminating alternatives: using billed rather than collected amounts produces
25,500 calculated payable; deducting unsupported B cost produces 17,200; a
conserved but unauthorized 50:50 bundle allocation produces 15,800. Selecting
cash by April posting instead excludes both applications from Q1 and produces
negative bases outside the fixture policy; there is no approved alternative
payable for that route. Passing conservation alone does not validate economics.

### RULE-01 Selection and scope P0

Use a 100 receipt with default 20% and expressly higher-priority Canada 40% rule:
US earns 20, CA earns 40. A higher-priority zero rule earns zero. Equal winning
priority with multiple matches produces the documented ambiguity diagnostic;
physical file order must not choose the rule. Missing required match fails unless
the schedule declares an explicit excluded outcome. Near misses for title,
territory, channel and effective date must not match. Trace candidate identities,
priorities, winning rule and explanation.

### NUM-01 Exact arithmetic and rounding P0

Two receipts of 0.05 at 10% yield exact contributions 0.005 each. Half-away-from-zero
rounding to cents yields 0.02 when each contribution is rounded, and 0.01 when
the exact sum is rounded once. Under half-even, individual contributions round
to zero, while their sum rounds to 0.01. The chosen schedule policy controls;
these are different labeled fixtures, not interchangeable expectations. Signed
ties under half-away-from-zero: 0.005 → 0.01, −0.005 → −0.01. Under half-even:
0.005 → 0.00, 0.015 → 0.02, −0.015 → −0.02. Exact one-third remains exact until
a specified rounding boundary. Mixed currencies fail in the one-currency slice.
Division by zero fails before payable publication. No binary floating-point
tolerance is permitted for monetary equality.

Research recommends a named synthetic cent profile with half-away-from-zero
once at the specified aggregate posting boundary, retaining exact intermediates.
Select it explicitly in the case manifest; do not infer it from USD or from
Lionsgate's ratio clause. For a separately approved in-scope positive financial
ratio expressed with two percentage decimals, 12.345% rounds to 12.35%, giving
1,235 on a 10,000 base versus unrounded 1,234.50. The clause does not establish
a general monetary rule or the handling of negative ratio ties.

For a later approved proportional allocation of 0.01 to equal claims X and Y,
a declared largest-remainder policy with stable key X before Y yields X=0.01,
Y=0.00; never silently lose a cent. Add this only when allocation semantics exist.

### TIME-01 Calendar and effective boundaries P0

Use a quarter represented by the half-open local-date interval
`[2026-10-01, 2027-01-01)`: cash received on 2026-10-01 and 2026-12-31 belongs;
cash received on 2027-01-01 does not. Posting in January does not displace a
December receipt under this cash-basis fixture. December sale with January cash
does not belong. A pure calendar date must round-trip unchanged in different
machine timezones. Timestamp-to-date normalization requires the declared timezone;
test both sides of midnight and a daylight-saving transition in that zone.
An amendment effective 2026-11-01 applies on that date under its approved selector,
with the previous version ending exclusively at that date. Missing selector or
overlapping unresolved versions fails. The Curve one-day discrepancy motivates
these tests without establishing a cause or desired vendor behavior.

Concrete selectors: cash 10 received/posted Oct 1, cash 100 received Dec 31 and
posted Jan 3, and cash 60 received Jan 1 against a Dec 31 sale give Q4 110 under
cash date and 10 under posting date. A frozen Jan 2 snapshot lacking the Dec 31
row may also show only 10; missing evidence and period membership are different
causes. An Oct 31 receipt 100 posted Nov 3 earns 20 under a cash-date 20%→30%
amendment effective Nov 1, versus 30 under posting-date selection. A Nov 1 receipt
earns 30 in a snapshot containing the amendment signed Oct 20, recorded Nov 5.
Earlier runs retain the earlier capture snapshot.

An eligible 20 cost incurred Dec 31 and paid Jan 3 with 100 Q4 cash and 25 fee
gives earnings 11 under incurred-date recognition versus 15 under paid-date
recognition. A 15 prepayment due Dec 31 but funded Jan 3 with 20 earnings gives
5 payable under a due-date balance policy versus 20 under actual-funded policy.
These are alternative synthetic timing choices; neither due date nor paid date
automatically determines recovery recognition.

The supplied RR-01 answer now selects **actual funded date** for the named
synthetic SV-03 mechanism. Approval/due date does not add availability. Both
issue and matching disbursement/eligibility evidence must be observed strictly
before the timestamp cutoff. June 30 funded and July 2 observed enters Q2 under
a July 3 cutoff; July 1 funded belongs to Q3. This selection does not generalize
to all agreements. See [the adopted research answers](research-answers-2026-11-20.md).

### RES-01 Reserve lifecycle P1

This is an arithmetic mechanism fixture, not a sourced Lionsgate reserve policy.
For a post-earnings reserve, opening reserve 10, current earnings 100, current
withholding 20 and release of opening vintage 5 yields closing reserve 25 and
current payable 85 before other offsets: 100 − 20 + 5 = 85. Assert opening 10
+ addition 20 − release 5 = closing 25. The trace distinguishes release from new
earnings. Test release beyond the available vintage as invalid. Add a contrasting
pre-basis reserve case only with a separately stated basis and expected arithmetic;
moving the same reserve percentage between stages can change earnings.

The researched Lionsgate return reserve, conditional on Purchaser distributing,
acts on named basis calculations and requires liquidation within twelve months;
it is not established as this post-earnings holdback. Its cap is redacted and
recognition/vintage/release policy remains open. A separate mechanism rollforward
is opening 12 + additions 20 − applications 7 − releases 5 = closing 20, then
applications 8 and releases 12 close zero. Each movement must identify its vintage
and avoid releasing the same reserve as both new cash and earnings.

RR-02 resolves the separate rollforward as **V1** opening 12, application 7,
unused release 5, closing 0; **V2** opening 0, addition 20, closing 20. Assert
both vintages as well as aggregate 20. The subsequent application 8/release 12
liquidates V2. Stable movement and evidence IDs, scope, purpose, currency,
effective date and separate observation timestamp are required. No vintage may
borrow another vintage's availability. The implemented mechanism accepts a
complete selected-period snapshot and blocks supplied out-of-period or
cutoff-unavailable reserve movements; it is not a general ledger intake filter.

### CORR-01 Immutable revisions and actual payments P1

Under a synthetic restatement policy, original payable 100 and independently
supplied actual payment 80 remain distinct. A corrected receipt changes revised
payable to 90; reconciliation shows originally issued 100, revised 90, delta −10,
actual paid 80 and remaining obligation 10. Do not subtract the original payable
as if it were cash paid. A new run links the old run and original opening snapshot;
it does not advance from the old closing state. A prospective adjustment is a
different policy with a separately identified recognition period and state effect.
Reusing a correction identity cannot apply it twice. Never infer permission to
offset unrelated future earnings from this mechanism test.

Use the researched correction ledger: underlying cash 500 and application to
invoice `INV-01` support original fact v1 and payable 100. Actual participant
payment 80 remains linked to the original obligation. Approval in February
reallocates 50 to another reconciled scope, replacing the eligible application
with 450 effective in Q4; it does not erase the original 500 bank receipt. Q4
restated payable is 90, outstanding 10. Q1 receipts 150 add earned 30, yielding
40 outstanding before further payments. A separately authorized prospective
route retains Q4 unpaid 20 and posts Q1 earned 30 plus adjustment −10 = 20,
also totaling 40 but with different period/state lineage. Choose one recognition
route; never both. Replaying the stable correction identity must be idempotent
within that recognized history. These mechanics do not generalize the separate
Lionsgate distribution agreement's specific correction authority to every deal.

### SCOPE-01 State identity P0

Hold agreement/participant/pool/currency/balance-kind/vintage constant while
changing one key at a time. Recovery must touch only its declared key. A reserve
is not an advance, and a gate meter is not a payable. Cross-title amounts remain
at pool scope unless an approved attribution rule exists. Validate opening period
boundary and lineage. Absence of a required opening balance fails; an explicit
approved zero opening succeeds.

### RUN-01 Determinism and revision P0

Identical effective facts, schedule, approved policy, mappings, parameters and
opening state produce identical economic results and semantic trace. Run ID,
elapsed time and wrapper observation timestamp may differ only where identified
as operational metadata. Permute inputs to sums and maps and expect unchanged
results; for ordered folds, use canonical event keys and demonstrate a policy case
where order changes the outcome. A new alias/policy/fact version yields a new
manifest and reproducible difference explanation. No clock or network access is
allowed inside the pure calculation.

### AUDIT-01 Reconciliation and explanation P0

Reconcile each amount kind and currency separately: source = included + deliberate
exclusions + quarantined/rejected controls, with allocations balancing to their
parent amounts. Do not add invoices to cash controls merely because both are
money. Explain each statement line through scope, named basis, operation/rate,
clause and interpretation, source rows, mapping and state movements. Check title
earnings roll up to 33,000 in SV-01 and pool recovery bridges them to 18,000;
there is no invented title-level recovery. Pre-round and rounded values explain
any rounding bridge. Zero-row presentation suppression preserves the internal
trace and reconciled included amounts.

### FAIL-01 Atomic finalization P0

Unknown schema, invalid required row, missing policy or failed Lean compilation
must produce diagnostics and no finalized statement/state. Where provisional
mode exists, its artifacts have explicit nonfinal status and cannot masquerade
as authoritative outputs. Run in a clean output directory; interrupt before
completion and ensure earlier files cannot satisfy the new run. Stable diagnostic
codes and source/field/clause locations are asserted; prose wording need not be.

### COMP-01 Independent execution paths P0 and P1

Start with reviewed hand arithmetic. Implement the research plan's independent
C# oracle from neutral facts and interpretation records, with its own arithmetic,
grouping and state logic. It may share schemas but must not call the parser, core
evaluator, generated Lean or runtime arithmetic helpers. Compare hand expectations,
oracle, direct core evaluation and emitted Lean execution on every supported
operator and representative composition. Compiler/interpreter agreement alone
cannot rule out a shared design bug. Validate emitted modules using the pinned
Lean 4.35.0 toolchain and the repository build arrangement.

Parser tests include a minimal valid and invalid example per construct. Checker
tests include unknown/duplicate names, scope mismatch, currency/type errors,
missing parameters and forbidden cycles. Trace source spans into lowering/emitter
errors. Generated-code compilation establishes target well-formedness; a later
proof must state separately whether it preserves amounts, state and semantic
trace, and what remains trusted. Do not use `sorry` or custom axioms. The existing
toy compiler theorem proves none of these participation calculations.

## Case packaging and implementation milestones

A future small tracked case pack should contain `case.json` (evidence, scope,
assumptions and review status), `schedule.spl`, schema-versioned facts and external
events, explicit opening state, a run manifest, and independently reviewed
expectations for statement/detail/trace/diagnostics/closing state. File names are
proposed packaging, not an implemented CLI. Store hashes or evidence locators
for large/private originals outside Git. Golden changes require an explanation
of changed economics or compatibility, not merely regeneration from the compiler.

1. Start the bounded synthetic compiler with explicit research-policy manifests;
   review this update and freeze minimal transport/type/rounding/date/diagnostic
   contracts. Historical and professional approval remain separate later gates.
2. Implement canonical validation, exact arithmetic, a core evaluator and SV
   schedule lowering. Complete all applicable P0 checks with independent values.
3. Emit Lean and integrate its pure result with wrapper/reporting. Run `lake build`,
   `lake exe smoke`, and new relevant checks after code changes. Demonstrate SV-01,
   serialized SV-02 and the blocked-run/independent-preview workflow contract.
4. Add LG distinct bases, cumulative meters, lazy gated comparison and reviewed
   reserve/offset policies. Complete relevant P1 checks without widening historical
   coverage claims beyond the evidence.
5. Freeze versions and perform HOLD-01. Broaden to three to five sourced public
   cases as a separate research milestone. Vendor integration, performance and
   formal verification claims each require a separate evaluated scope.

### HOLD-01 Frozen-language extension evaluation

Keep Lionsgate derivative and distribution agreements, amendments and related
exhibits in the same case family. With LG used for development, reserve a different
family for evaluation; Ilshin is an already disclosed candidate, not an unseen
topic. Both Lionsgate derivative and distribution agreements are now assigned
to development. Ilshin remains provisional pending an independent evaluator's
family/exposure review; substitute a different family if detailed exposure
compromises the intended claim. A separate evaluator and access-controlled
custody are still missing. Evaluator, access owner, participant exposure records,
restricted package identity and readiness confirmation are all pending. A prepared
protocol does not establish any of these appointments or artifacts. Keep detailed interpretation, alternatives, fixture
and oracle outside shared development/research directories, repositories and
agent prompts. Participant-specific exposure attestations remain open. This
design update used status/custody information, not withheld answers.

Freeze surface/core/schema versions, semantics, toolchain, compiler/reference
builds, baseline expectations, and compatibility promises. Record the attempted
encoding, diagnostics and any workaround. Classify each change as parameter,
new method using existing operators, surface abstraction, or new core capability.
Measure reviewer effort and implementation changes. Compare the extension with
the independently prepared oracle and rerun the frozen corpus. A new core feature
needs explicit semantics and targeted tests; an intentional behavior change
needs a version boundary. A mixed-Lionsgate exercise is a capability check,
not family-disjoint held-out evidence.
Release only the interpretation and encoding inputs after the freeze and recorded
custodial approval. Log the first encoding/diagnostics before the evaluator
reveals expected results. A proposed protocol without a prepared restricted
package and qualified custodian is not completed held-out evaluation.
