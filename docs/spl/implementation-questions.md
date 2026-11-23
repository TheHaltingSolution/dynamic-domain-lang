# Implementation questions for language design and royalties research

20 November 2026. Original questions are retained below as historical records.
LD-01 and the named RR-01/RR-02 cases now have responses. Broader policies are
still outside those responses.

21 November design response: [release-scope-ld02.md](release-scope-ld02.md)
answers LD-02 with the linked conformance ledger, proposed operator semantics,
module boundary and finite release target. The supporting
[RR-03 research brief](research-request-rr03.md) has now received the user-supplied
response; see [its integration](rr03-response-integration.md). The user's explicit
dynamicity goal is recorded in the [extension experiment](extensibility-experiment.md).
New capabilities remain proposed until implemented and checked through their
canonical interfaces.

Language-design response: [implementation-answers.md](implementation-answers.md)
answers LD-01 and records its visibility/refinement conditions. The user supplied
the research replies, recorded in [research-answers-2026-11-20.md](research-answers-2026-11-20.md).
RR-01 selects actual funding and separate observed timestamps. RR-02 confirms
the correction arithmetic and requires separate V1/V2 reserve balances. These
answers apply to the named synthetic cases; wider alternatives remain open.

## LD-01: readable schedule versus supporting bindings

For the language-design agent: we are adding a controlled readable authoring
surface that lowers to the same typed core as the original programmatic source.
The main schedule uses multiword financial names, percentages, conditional
methods, settlement and reports. Typed input/state/evidence mappings can appear
as clearly separated supporting declarations. Does this preserve the intended
contract-authoring boundary, and which technical declarations must appear in
the contract-facing schedule rather than its supporting package?

Engineering working choice: keep calculation definitions and all choices that
change amounts visible in the schedule; keep schema/file bindings and stable
identity mappings in inspectable support. No runtime prose interpretation.
This choice supports implementation and does not record language-design approval.

Iteration result: the user reviewed the executable SV main section and confirmed
"keep this direction and refine it". The current source therefore keeps financial
rules first and bindings in a footer. This is author-direction feedback, not
contract-reader or accountant approval. Exact iteration/settlement labels must
have explicit supporting registrations; heading names do not infer party IDs.

## RR-01: next advance scenario and evidence timing

For the royalties-research agent: the handoff permits a named prospective
new-advance scenario, but not a universal historical policy. For the next bounded
case, may an explicitly synthetic policy add evidenced current-period participant
advance issues to the opening recoverable pool before pooled current earnings
are recouped? Please specify effective versus funded/observed dates, cutoff,
scope and whether any same-period priority is intended. A discriminator is
opening 0, newly issued advance 15,000, earnings 10,000: recover 10,000 and carry
5,000 under the proposed simple policy. Acquisition costs/funding are separate.

Engineering can implement this as a named synthetic mechanism test; it will not
be enabled in SV-01 or presented as the default agreement interpretation.

## RR-02: correction and reserve boundaries

For the royalties-research agent: confirm that the existing synthetic CORR-01
and RES-01 controls are suitable for separate mechanism cases: revised entitlement
90 less actual payment 80 leaves 10 outstanding; a distinct reserve vintage
12 + 20 additions - 7 applications - 5 unused releases closes 20. These do not
choose restatement versus prospective correction, authorize a new payment or
identify the stage at which a contractual video reserve changes earnings.
Please return any changed scope, event authority or date-selection requirements.

Dynamic gate crossings, reserve caps/recognition and negative earnings remain
separate unresolved economic policies; no implementation default is proposed.

## LD-02: design conformance and next release scope

Prepared 21 November 2026 for the language-design agent; answered by the linked
21 November design response above. The new request concerns feature coverage after the
readability direction was accepted. See the preliminary coverage table and
[next-stage plan](development-plan.md#next-stages-21-november-2026).

Please review the current compiler against the full reference/core/data/validation
design. For every requested construct, primitive, setting and supported variation,
return implemented, partial, absent or deliberately deferred, with a requirement
locator and a minimal source/data witness. Distinguish syntax sugar, reusable
ordinary expressions, new semantic primitives, wrapper/schema integration and
unresolved economic policy. Do not count a compiler expression as complete
canonical support when the physical package profile cannot supply it.

In particular, confirm the release priority and intended semantics of RULE-01
priority selection, typed keyed lookup/maps, grouping/joins and deterministic
ordered folds. For priority, specify no-match, unique winner, equal-priority
tie and explicit zero outcomes; for ordered state, specify event ordering and
tie keys. Identify which capabilities are genuinely required now and which
belong to a later extension rather than implementing the entire draft at once.

The current registered readable profiles use whole-expanded-core signatures.
Supported new methods can run through the compiler with experimental typed
bindings, but canonical finalization requires an explicit policy/profile revision.
Please recommend a reusable policy/module registration boundary for additional
contracts while preserving LD-01 visibility and evidence pinning. Core identifier
renaming or equivalent algebraic rewrites are not currently recognized by the
bounded signature checker; do not treat that as semantic equivalence checking.

Return a proposed finite release scope, missing acceptance cases and the smallest
extensions needed for the selected methods. Keep future Lean compiler verification
possible; full proofs remain deferred until after the demo. This request does not
reopen the accepted readability direction or require a new stylistic approval.

## RR-03: domain feature gaps, development baselines and realistic scale

Prepared 21 November 2026 and answered by the user-supplied
`SPL_RR03_Coverage_Benchmarks_and_Workload.md`; the request below is historical.
Use the feature table in
[development-plan.md](development-plan.md) and current
[implementation report](implementation.md). RR-01/RR-02 answers remain adopted
for their named cases; no repeat confirmation is requested.

Please provide three outputs:

1. **Feature gap review.** Compare our calculation capabilities with relevant
   rights/royalty methodologies and available public or legitimately accessible
   subscription/private software evidence. Reuse existing research first. For
   each gap provide economic behavior, source locator/date and product/version
   when applicable, documented versus observed versus advertised status,
   relevance to screen participation, priority, and a minimal numeric example.
   Distinguish a language calculation from an adapter and an external workflow
   such as signing, licensing administration, portals or bank payment execution.
   Identify expressible-but-unwieldy methods separately from absent semantics.
2. **Paired development benchmarks.** Find materially different contract
   provisions with independently supported expected calculations, ideally with
   facts, opening balances, period, intermediate bases/fees, payout and closing
   state. Identify missing inputs and synthetic substitutions explicitly. Rank
   complete contract/accounting pairs, partial worked mechanisms and vendor
   workflow observations separately. Target the original three-to-five public
   cases overall and at least two different calculation methods. A duplicate
   spelling or another reconstruction of the same method is not a new method.
   Request a case-specific decision/discriminator for disputed reserve stages,
   gate timing, losses or correction routes, rather than a universal default.
3. **Workload evidence.** Estimate realistic receipt/cost/event counts per
   settlement, pictures/pools/participants, allocation fan-out, reporting periods,
   hot-pool skew, audit volume and desired turnaround. Distinguish observed
   workloads from synthetic stress targets, and state whether parallel work is
   across independent agreements or within an economically shared pool. We have
   not established throughput; the current 100,000-fact/event guard is not a
   performance claim.

For private/paywalled findings, return permitted evidence summaries/locators and
the reuse/publication status. Portable test cases must remain reproducible without
subscriptions or vendor credentials; vendor output by itself does not determine
the meaning of a film agreement. Do not acquire new paid access for a general
survey; identify a concrete evidence gap if existing access is insufficient.

Keep held-out detailed provisions, interpretations, fixtures and expected outputs
outside shared developer/research prompts and directories. Research only the
development corpus here; the independently custodied evaluation is separate.

Primary ownership: LD-02 is design conformance and language/core decisions;
RR-03 is domain coverage, evidence, baselines and workloads. Both agents may
comment on the combined plan, with decisions attributed to the relevant role.

## DYN-02: required contract extension before FX

Prepared 22 November 2026 following the user's stronger requirement. The user
supplied the research recommendation; the language-design assessment is now
[dyn02-design-answer.md](dyn02-design-answer.md), with
[targeted follow-ups](dyn02-research-followups.md). No necessary core capability
has been selected. Compiler review also replayed four positive and three negative
Quest cases in both native and emitted execution, preserving the compiler and
original artifacts. The user has now supplied the targeted research reply,
reconciled in [the Quest neutral fixture specification](quest-two-flow-fixture.md).
The original-date/calendar/canonical witness and half-even tie refinement now
execute under that proposed synthetic policy; see the
[23 November method guide](../../cases/quest/README.md). All 34 supplemental
checks and nine review scenarios pass. The original three-candidate survey and
resolved fixture questions need not be repeated. The monthly
component/combined liability and project scope remain outside the selected
fixture's approval boundary.
The original request below is retained with distinct
responsibilities. The unchanged implementation baseline is `0.4.3-dev`, commit
`38f00a2`; native EUR/FX support has not been implemented. Read the current
[selection gate](extensibility-experiment.md#22-november-2026-stronger-requirement-before-the-fx-milestone).

**Royalties-research agent:** propose two or three actual screen/rights contract
clauses whose required calculations may need an extension beyond our current
kernel. Supply the source locator and clause, why the behavior is mandatory,
original inputs, required outputs/state, policy ambiguities and an independently
supported worked checkpoint. Distinguish sourced obligations from synthetic
test numbers. Prioritize realistic contract needs; do not select a feature only
because a vendor advertises it. The receipt-date FX clause linked in the gate is
a lead, not a selected candidate or complete worked baseline. Keep independently
custodied holdout material outside this disclosed development discussion.

**Language-design agent:** for each candidate, attempt a faithful reusable
encoding using existing arithmetic, records, maps, selection, first-order modules
and folds. Include currency-tagged records and unit-cancellation/reconstruction
paths when assessing FX; hiding only a proposed `convert` builtin is insufficient.
Current same-currency Money/Money division already yields Ratio. If that rule is
generalized to EUR in the foundation, explicitly assess whether it defeats the
proposed reserved FX gap. Classify missing behavior versus stronger static
guarantees, syntax/library work, canonical schema constraints or supplied-evidence
requirements. A compiler rejection of new type syntax alone is not an encoding
analysis.

**Joint decision:** return one recommended reserved capability, the smallest
required extension and a concrete before/after acceptance case, or explain that
none qualifies yet. Define the original fact/output/trust boundary in advance.
Reject precomputed answers, external financial preprocessing, currency
misrepresentation and fixture-specific payout constants as substitutes; accept
legitimate old-language encodings that meet the agreed requirement. Do not claim
that no encoding exists without supporting the claim. The earlier calendar
experiment had a legitimate supplied-date alternative and must retain that
qualification under the stronger criterion.
