# SPL questions for the research agent

**Status update, 20 November 2026:** the ten original questions below have now
received responses in external `ResearchAgent/documents/SPL_Research_Responses.md`.
Retain this file as the original request, not a new unanswered questionnaire.
Use the [compiler handoff](compiler-handoff.md) for incorporated decisions and
[remaining follow-ups](research-followups.md) for the narrower open work. Original
context and request wording below are preserved for provenance.

Status: initial request brief, 15 November 2026. These questions identify the
evidence needed to approve or extend the first draft. They do not delay writing
bounded synthetic schedules. Until answered, use named scenario assumptions or
withhold an authoritative payable for the affected scope. No outreach has been
sent by the design team.

## Response format and priority

For each question, provide: an answer or explicit unresolved status; primary
document and version; exact clause/page/exhibit locator and a short permitted
quotation or accurate paraphrase; incorporated dependencies; evidence class;
adopted reading and material alternatives; scope and effective dates; reviewer
status; and a small discriminating numeric example. Preserve redactions. Mark
substitute parameters as synthetic. Separate contractual requirements, observed
practice and research assumptions. If operational artifacts are private, identify
what may be retained or published; a synthetic reconstruction is acceptable when
historical records are unavailable.

P0 questions affect approval of the initial compiler slice. P1 questions affect
the contrasting development case and revision machinery. P2 questions support
later interoperability or evaluation; vendor access is not a prerequisite.

## RQ-01 Skouras receipt and deduction schedules P0

Context: the pilot uses cash actually received, 25% versus 7.5% distribution fees,
distinct §8 bases and preclassified eligible costs. A general `costs` total could
erase differences in the two deduction schedules.

Question: for each selected branch of Skouras–Ventura §§7–9, what exactly is the
receipt/fee base, which acquisitions or advances are included, which deductions
are allowed, and in what order? Identify incorporated definitions or missing
attachments, in-house service surcharges, interest, returns, taxes and related
party treatment only to the extent evidenced. What differentiates an acquisition
advance entering a basis from the §7 participation prepayment?

Requested evidence: a clause-to-operator abstraction sheet for both branches,
with a sample ledger classification for each deduction family and one amount
whose classification changes the result. Explicitly state which portions the
100,000/60,000 pilot can legitimately represent.

Decision affected: approved SV schedule, required fact kinds, eligibility policy,
deduction identities and double-count prevention. Without a fuller answer, the
draft remains limited to supplied, approved eligible-cost subtotals.

## RQ-02 Skouras recovery history and contribution share P0

Context: the pilot begins with a supplied remaining pool of 15,000; the carry
fixture applies positive earnings against a bounded opening balance. Neither
fixture establishes historical backward/forward offset mechanics.

Question: which titles, advances, dates and parties belong to the §7 recovery
pool, and how are earlier losses, negative earnings, new advances and prior
payments treated? Does the agreement mandate allocation of a pooled offset to
titles, or is pool-level reporting sufficient? What is the denominator and
valuation date for the contribution-based share; how are zero, later or unequal
contributions handled?

Requested evidence: opening-state rollforward and two-period discriminating
example with a new advance or negative title result; exact clauses for crossing,
priorities and funding share. If historical data is unavailable, recommend an
explicit narrow research policy and competing scenario.

Decision affected: state keys, negative-value policy, event order, contribution
schema and permissible coverage claims. Current synthetic carry stays distinct
from any historical reconstruction.

## RQ-03 Lionsgate gate, branch and fee offset P1

Context: §2.4(a)(ii) uses full home-video receipts in True-Cash Breakeven while
the gross payout branch can use a proxy. The seed gate is already clear and the
producer-fee offset of 12 is synthetic and applied only to the gross branch.

Question: what costs/receipts and title scope update the rolling gate? Does
equality satisfy it? When a receipt crosses breakeven, is the crossing receipt,
only its excess, the next receipt, the current whole period or retrospective
receipts used for the gross candidate? How do chronology and amended terms
affect that answer? At what stage and scope is the producer fee offset applied,
does it carry, can a candidate become negative, and how does it interact with
the net candidate and greater-of operation? How are net-profit titles crossed?

Requested evidence: separate formula sheets for gate, gross candidate and net
candidate, with exact provision locators and available incorporated definitions.
Provide below/equal/above and crossing-row examples, a branch tie, and a case
where alternative fee-offset readings produce different amounts. Redacted
rates/caps remain fixture parameters.

Decision affected: gate timing, ordered fold requirements, branch laziness,
offset state, comparison trace and source-derived versus supplied net subtotals.

## RQ-04 Reserve meaning and release evidence P1

Context: a reserve before base formation and a reserve after earnings are
economically different; a release is not automatically new earned participation.

Question: for the selected Lionsgate subset, what event permits each reserve,
which base and cap apply, how are vintages established, what releases a reserve,
and does release feed a basis, earnings or only payment? Are approval or actual
cash events needed? Is there a prescribed order among advance recovery,
producer-fee offset, reserve creation/release and payment?

Requested evidence: selected provision and one complete reserve rollforward
with opening, additions, applications/releases and closing by scope/vintage;
show a case where moving the reserve to another stage changes payable.

Decision affected: reserve state representation, staged settlement order and
whether the arithmetic RES-01 mechanism can be promoted into a sourced case.

## RQ-05 Rounding, dates and negative economics P0

Context: exact arithmetic and explicit rounding/calendar conventions are design
choices, but contract-specific choices can override research defaults. Trial
screens showed a one-day date discrepancy whose cause is unknown.

Question: do either selected agreement's incorporated terms or reliable
accounting records prescribe rounding unit, mode, point, negative-value handling,
currency precision, reporting cutoffs or time basis? Which date controls receipt,
cost, contribution, advance and approval eligibility? How do amendments apply
to facts received or posted after an earlier effective date?

Requested evidence: affirmative clause/practice citations or an explicit finding
that no rule was established. Recommend a labeled research convention where
silent; provide cent ties, a negative amount and facts exactly on cutoff dates.
Do not infer a timezone conversion bug from the Curve display alone.

Decision affected: first-slice arithmetic/date profile and required event dates;
negative bases or earnings stay bounded until an interpretation is approved.

## RQ-06 Corrections, approval and actual-payment events P1

Context: payable, issued statement, accrued amount and actual cash payment must
remain distinct. A correction may restate a prior period or be recognized later;
these policies have different state consequences.

Question: what evidence authorizes a correction, which accounting period should
recognize it, how are already paid amounts handled, and what limits apply to
carrying a shortfall or negative adjustment? For the development provisions,
which approvals, disputes or external payment events actually affect money?
Are original invoice, cash application, reversal and replacement identities
available, and how is double-counting prevented in practice?

Requested evidence: a de-identified or synthetic original run, payment, correction
and subsequent run showing exact amounts, dates, linkage and authorization.
Separate contractual authority from a vendor's preferred workflow.

Decision affected: event schemas, restatement/prospective policies, correction
identity, unpaid obligation reconciliation and scope of the first runtime.

## RQ-07 Representative screen accounting package P1

Context: no universal portable negotiated-participation schema was established.
The canonical records are a project proposal; vendor terms alone cannot validate
their completeness.

Question: can the research agent obtain a redacted or synthetic package connecting
one deal abstract and approved interpretation to receipt/cost inputs, title/bundle
allocation, opening balances, statement detail and closing balances? Which raw
columns are actually supplied, and at what granularity? Identify absent dates,
parent invoice/cash relationships, aliases, currencies and independent controls.

Requested evidence: a field dictionary with units/nullability/keys, a few linked
rows, source totals and one reconciled statement. State sharing rights and any
invented fields. A documented inability to obtain it is an acceptable finding.

Decision affected: schema freeze, conditional required fields, adapter boundaries,
source control totals and reviewable output structure. No commercial access is
needed to implement the synthetic first slice.

## RQ-08 Contract-reader and accountant review P0

Context: controlled legalese can be compilable yet hard for its intended reader
to assess. The draft has not been approved as legal or accounting practice.

Question: can a contract reader and participation accountant review the two
draft schedules and identify each basis, priority, share, recovery scope and
payable without reading the core language? Which phrase or ordering creates
ambiguity? Can they distinguish a parameter change from a method change and
explain why two factually similar titles differ?

Requested evidence: structured review notes tied to source lines, answers to
the named tasks, proposed wording and reviewer role/date; identify unresolved
disagreement rather than silently choosing a reading.

Decision affected: surface notation, evidence presentation and readability
acceptance. Record a review gap if a suitable reviewer is unavailable.

## RQ-09 Family-disjoint held-out preparation P2

Context: Lionsgate derivative is a development case, so Lionsgate distribution
cannot also count as a family-disjoint holdout. Ilshin is already a disclosed
candidate, although its detailed evaluation can still be withheld.

Question: can a separate reviewer select an independent family and prepare a
clause-level approved interpretation, detailed synthetic fixture and independent
expected outputs after recording current exposure? For an Ilshin-based case,
which costs count toward the consent threshold, what consent evidence matters,
and what are the below/equal/above and no-consent outcomes?

Requested evidence: initially return only the family allocation, access protocol
and high-level capability target. Keep detailed interpretation, rows and expected
outputs out of the implementation context until the language/core/schema freeze.
Keep damages findings distinct from a computational reconstruction.

Decision affected: validity of the extension experiment, scope of withheld
information and whether a later change is a parameter, method, surface feature
or new core capability. Mixed-family exposure must be disclosed.

## RQ-10 Optional commercial interoperability P2

Context: Rightsline/Alliant documentation and Curve observations inform workflow,
but do not establish economic equivalence or a portable configuration schema.

Question: if a specific consumer integration becomes necessary, what exact
versioned transaction layout, deal configuration and output schema does it
require? Which selected SPL operators can be configured faithfully, which need
services/code, and what survives export/reimport? How are unmatched rows,
rule-precedence explanations, reruns and corrections represented?

Requested evidence: precise blank layouts or permitted examples, version and
tenant/plan limitations, one independently reconciled common subset and rights
to retain/share artifacts. Report unavailable internals explicitly. Do not open
new subscriptions or conduct further vendor trials merely to answer the initial
language-design brief.

Decision affected: a future adapter and supported-subset declaration only; this
question does not govern the public core or block the portable benchmark.

## Engineering decisions the research agent need not settle

Parser construction, core representation, Lean emission strategy, deterministic
serialization, immutable revisions and stable diagnostic identifiers belong to
the implementation team. Research is needed when those choices would select
an economic interpretation, conceal missing evidence or erase a distinction
that affects reconciliation. The first compiler can proceed on explicitly
bounded synthetic policies while domain review continues.
