# Language design answers for the compiler agent

For the 21 November feature-coverage question LD-02, read the separate
[next-release answer](release-scope-ld02.md),
[conformance ledger](conformance-ledger.md),
[proposed core semantics](next-core-semantics.md) and
[module boundary](policy-modules.md). The LD-01 response below remains the
authoring-boundary decision. RR-01/RR-02 were subsequently answered for their
named synthetic cases in [the adopted research record](research-answers-2026-11-20.md);
the forwarding message below is historical, not a request to repeat them.

20 November 2026. Response to LD-01 in
[implementation-questions.md](implementation-questions.md), after reviewing the
current readable SV, RQ-07 and LG sources and
[readable language specification](readable-language.md). This records a language
design direction and its review conditions. It is not accountant approval,
contract interpretation approval or a claim of complete compiler verification.

## LD-01 Answer and decision

**Yes: retain the financial-rules-first schedule and explicit supporting
declarations.** This preserves the intended contract-authoring boundary, subject
to the visibility rules below. It also follows the user's instruction to keep
this readable direction and refine it. There is no requirement to put raw type
declarations, schema field paths or opaque IDs into the financial narrative.

However, supporting declarations are not necessarily economically neutral.
Their current `Bind`, `Iterate`, `opening`, `require` and `define` forms can
change a result, its applicability or whether a payable is finalized. A footer
must not become an unreviewed way to replace a financial method while retaining
the same readable words. The executable agreement is the main schedule together
with its incorporated definitions, bindings, interpretation and pinned policies.

Adopt decision **LD-01-D1**: distinguish the economic meaning that a reviewer
must see from the technical expression that implements it. Economic meaning
belongs in the main schedule or a named, explicitly incorporated readable
definition/policy section. The corresponding typed implementation may remain
in the footer. An incorporated section is part of the contract review package;
it cannot be discoverable only by reading generated Lean or an internal runtime.

## What must be visible and what may remain in support

| Subject | Visible financial schedule or incorporated readable section | Supporting declarations may contain |
| --- | --- | --- |
| Parties, work and pool scope | Participant role, eligible pictures, agreement scope, pool purpose, authorized crossing and membership policy | Exact `Settle`/`Iterate` registrations, stable IDs, typed collections, reference lookups and effective membership records |
| Receipts and time | Receipt measure, inclusions/exclusions, controlling date, period/calendar, cutoff policy if material, amendment/as-of treatment | Field paths, source normalization, period object and explicit timestamp/date conversion implementation |
| Deductions and supplied subtotals | Branch-specific deduction definition, eligibility authority, cost recognition date, scope and limits; identify a supplied worksheet rather than claiming its derivation | Typed eligible-cost projections, worksheet IDs, source joins and evidence links implementing that definition |
| Rates and proportions | Rate, funding-share definition or named parameter schedule, qualifying contributors, denominator and valuation policy | Exact parameter values bound from the pinned terms, approved funding evidence and arithmetic implementation; values must be accessible in the review package |
| State and ordering | Distinct advance/reserve/obligation purposes, opening-balance authority, recovery priority, movement equations, rounding points and residual allocation | State aliases and full key dimensions, snapshot identities, diagnostics and typed output ports |
| Gates and applicability | Independent hurdle/gate requirements, comparisons including equality, timing, evidence assumptions, lazy alternatives and tie policy | Typed attestation fields, reference resolution and defensive validation implementing the stated conditions |
| Reports and settlement | Meaning of earned/payable/actual payment, reporting scope, closing balances and blocked-result behavior | Record field/port names, JSON layout, display formatting that does not change calculation |
| Source mechanics | Identify the economic profile and incorporated version; no requirement for physical file paths in legal prose | Language/schema/runtime versions, file bindings, adapter versions, content hashes, source locators and transport details |

Every amount-changing rule need not be repeated in two places. A clear named
incorporation is sufficient when its definition, actual applicable parameters,
scope, assumptions and version are available to the reader. A bare phrase such
as “allowed costs” or a citation ID alone does not disclose an otherwise hidden
eligibility method. A source fact may supply a monetary value without printing
every transaction in the schedule; the schedule still declares which facts and
measure it uses.

Missing required data, ambiguous mappings and unresolved policies remain blocking
conditions as specified by the existing data/run contract. Routine codec checks
may stay technical. A new precondition that excludes economic cases or changes
payable status must be disclosed as part of the case's scope or policy.

## Refinements identified in the current examples

1. **SV versus RQ-07 cost dates.** The main readable sections are currently the
   same, but `sv01-readable.spl` selects `incurred_date`, whereas
   `rq07-readable.spl` selects `recognition_date` under the GL-posting profile.
   Make the distinction visible in a named cost-recognition policy referenced
   by each schedule. Preserve missing incurred dates. The existing equal 18,000
   result does not make the policies equivalent.
2. **SV deduction schedules.** Keep Net Profits and Adjusted Gross Receipts
   definitions distinct. State that the bounded case consumes separately
   authorized branch-eligible costs; the current identical aggregation shape
   does not establish identical contractual eligibility. Keep the funding-share
   evidence/completeness and supplied remaining prepayment assumptions readable.
3. **Collection and settlement scope.** The explicit `Iterate` and `Settle`
   registrations are the right mechanism. Validate that the registered picture
   collection actually satisfies the stated relationship and authorized pool
   membership. Registration binds the words; it does not prove their factual
   truth. Headings, display titles and proper names must never infer party IDs,
   roles, membership or legal priority.
4. **LG payout base and supplied evidence.** “Adjusted by the supplied video
   proxy” should incorporate the actual definition: full eligible non-video
   receipts plus eligible home-video receipts times the named proxy rate. Keep
   the two gate prerequisites, strict prior-period hurdle date, distinct work
   and net-group scopes, supplied crossed-net subtotal, gross-only offset and
   synthetic zero floor explicit. Calendar-quarter use is a synthetic profile,
   not a claim that the sourced fiscal reporting calendar was implemented.
5. **Synthetic payment holdback.** Keep its synthetic character visible in the
   readable settlement or an incorporated case-policy section. Baseline LG-01
   uses zero movements; nonzero holdback behavior does not implement the
   agreement's basis-stage video-return reserve.

Illustrative policy wording for the next authoring iteration:

> This schedule uses the SV incurred-date cost policy. Deduct only costs with
> reviewed eligibility for this Picture's applicable deduction schedule whose
> incurred date falls within the accounting period.
>
> The separate RQ-07 reconstruction uses GL posting dates for cost recognition;
> incurred dates are unavailable and are not inferred. Receipts use bank value
> date under the named intake policy, with the separately stated observation
> cutoff.

These are drafting examples, **not newly supported parser syntax**. Engineering
may first expose them as an explicitly linked, versioned policy section in the
review package, then add controlled syntax when justified. Do not accept
arbitrary prose or silently ignore purported executable statements.

## Compiler behavior and acceptance implications

Continue deterministic readable-source expansion into checked syntax and the
same typed core. Preserve the original source as a regression input. No runtime
language-model interpretation, case-name dispatch or implicit clause inference
is introduced by this answer.

The next refinement should demonstrate these properties with focused checks:

- Unsupported/unbound phrases, duplicate registrations, wrongly typed identities
  and ambiguous scope fail with authored-source diagnostics. Different labels
  that intentionally name one core binding are permitted only where explicitly
  registered and consistent with branch/scoping checks.
- Changing a date selector, economic population, weighting, eligibility policy,
  rounding point or evidence precondition changes the identified review package
  and receives an economic-policy review delta. Include a discriminator where
  incurred and posted dates lie in different periods; equal baseline totals
  are insufficient evidence that this distinction is visible.
- Purely mechanical renaming, field wiring or relocation preserves business
  values, typed scope and state when it is actually equivalent. Source/trace IDs
  or artifact digests may change; do not require byte-identical trace IDs after
  an authored-source edit.
- Review artifacts link each material readable rule to its supporting expression,
  source span, interpretation/evidence and parameter values. The existing expanded
  source and map are useful; when a footer expression determines the economics,
  retain its location as well as the main statement's location rather than
  attributing the entire choice to a generic financial phrase.
- Pin all executable supporting expressions and incorporated policy identities
  in the source/run dependency closure. Untracked mutable aliases or policy
  registries cannot change an issued result. Text saying that a policy applies
  must agree with the actual bound implementation; reject machine-checkable
  disagreements and record unresolved human interpretation differences.

Existing SV/RQ-07 18,000 and LG 35 results remain baseline expectations. The
original arithmetic and typed-core semantics do not change with this decision.
This document authorizes the authoring architecture and requests visibility
refinements; it does not assert that every check above is already implemented.
Follow repository build/smoke and relevant regression requirements for subsequent
code changes. This answer itself changes documentation only.

## Research and clarification handoff

**No new contract research is required to decide LD-01.** The authoring boundary
is a language-design decision. Full contract-reader/accountant review of the
revised readable package remains separate from the user's author-direction
feedback and the earlier arithmetic review.

RR-01 and RR-02 in the question log remain research requests. Engineering already
records separate synthetic mechanism cases; they must not become automatic
SV/LG policies. The following message can accompany the existing questions:

> Please answer RR-01 and RR-02 in `implementation-questions.md` for the next
> named synthetic cases. For RR-01, state which event makes an advance available
> (issue/approval, due or actual funding), its effective and observed dates,
> cutoff, scope, reversals/duplicates and any same-period priority. The proposed
> discriminator is opening 0, new advance 15,000, earnings 10,000: recover 10,000
> and carry 5,000 under the selected simple policy. For RR-02, confirm the
> supplied revised-entitlement/payment reconciliation (90 - 80 = 10) and distinct
> reserve rollforward (12 + 20 - 7 - 5 = 20), with required authority, event dates
> and state purpose. Separate arithmetic mechanism acceptance from authority to
> restate, carry, offset or change a contractual basis. Preserve unresolved
> alternatives rather than choosing a general historical default.

No external message or reviewer contact has been made. The research replies
need not delay refinement of readable bindings or the existing synthetic cases.

## Snapshot and integration note

The current [implementation report](implementation.md) now describes native
readable execution, mapped RQ-07 artifacts and separate accounting mechanisms.
That is newer engineering evidence than the earlier design handoff's
“mapping specification only” status. Accountant review and historical approval
remain pending. This response inspected the sources and reports; it did not
rerun or independently certify the implementation report's test claims.

Keep the original question text and pinned implementation baseline as historical
records. Documentation changed by this answer has new bytes; deliberately
regenerate a future review baseline when adopting it, rather than silently
rewriting old fingerprints or treating the same draft label as an unchanged
snapshot.
