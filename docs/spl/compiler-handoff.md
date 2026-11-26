# SPL compiler implementation handoff

**Latest continuation:** start with the
[25 November handoff](session-handoff-2026-11-25.md) for the owner's revised
finish line, saved integration and next steps. Work is paused for handoff.
The earlier documents below retain historical design and implementation context.

For a new implementation session, start with the
[23 November session handoff](session-handoff.md). It records the implemented
kernel and Quest checkpoint, agent responsibilities, resources, verification
evidence, Windows lessons and the proposed next validation milestone. The earlier
initial-compiler handoff below remains historical design/policy provenance.

Next-stage handoff, 21 November 2026: the bounded demo now exists. For broad
calculation coverage, start with the [LD-02 release decision](release-scope-ld02.md),
[conformance ledger](conformance-ledger.md),
[next core semantics](next-core-semantics.md) and
[reusable module boundary](policy-modules.md). These extend the plan without
changing the accepted readable direction or silently adding unimplemented
operators. RR-03 has now been answered; use the
[response integration](rr03-response-integration.md) for R1 case promotion and
workload decisions, and the [extensibility experiment](extensibility-experiment.md)
for the deliberate future language/compiler gap. Adopted RR-01/RR-02 policies
stay in force for their named cases. Earlier mapping-specification-only statuses
below are historical: current mapped artifacts are in the implementation report.
The earlier handoff below remains the bounded-case rationale and provenance.

Research-integrated draft, 20 November 2026. Start compiler development with the
bounded synthetic cases below. The research answers resolve enough to proceed;
they do not establish full agreement coverage, historical replay, complete
readability review or a production-ready schema. The incoming research handoff
contained no implementation. Later on 20 November the bounded native Lean
compiler and actual mapped RQ-07 run were added; see [implementation.md](implementation.md)
and [the content-pinned baseline](implementation-baseline.json). Accountant review
is pending, and full compiler verification is deferred until after the demo.

Follow-up reconciliation, 20 November 2026: compiler development remains
authorized for the bounded synthetic slice. The latest supplied answers confirm
the source-package reconciliation, but not a mapped canonical run, completed
DOC-01 review or established evaluation custody. The LG-01 start-date mismatch
is resolved below as a selected synthetic restriction, not a new clause finding.

## What governs this implementation

Read the [design index](README.md), [language reference](language-reference.md),
[core specification](core-and-compilation.md),
[data contract](data-and-run-contract.md), and
[validation plan](requirements-and-validation.md). This handoff records the
current case policies and implementation order. It supersedes the initial
index's unanswered-research status; it does not override primitive semantics.
Resolve any remaining contradiction as a documented draft change before coding
the affected behavior. Preserve original fixture assumptions as named profiles.

The new controlling research index is
`ResearchAgent/documents/SPL_Research_Responses.md` (16 November response with
19 November verification), SHA-256
`CD0080CA24251870CB95B165BA5076F5F38348F68CEAE9B9703AD4FD218F0F0E`.
Its paths are relative to the external project root
`C:\Projects\Film_TV_participation_dynamic_DSL`. Follow its detailed development
documents when necessary; do not import private Curve inputs or open detailed
held-out materials into the implementation context. The source digest identifies
the reviewed bytes, not professional approval.

## Decisions for the initial implementation

| ID | Implementation instruction | Evidence and limit |
| --- | --- | --- |
| DI-01 | Implement source adapters, typed core interpretation, surface elaboration and Lean emission as distinct stages; pure settlement receives explicit facts/state/configuration | Existing architecture remains suitable; current toy theorem establishes none of the new stages |
| DI-02 | Select the SV receipt basis by cash actually received, not invoice/sale/GL date | RQ-01/05; RQ-07 names bank value date as its synthetic cash-date source |
| DI-03 | Keep separate cost definitions for the two funding branches and record eligibility decisions before aggregation | RQ-01 confirms the schedules differ; full interest/surcharge/expense eligibility is outside the first slice |
| DI-04 | Distinguish acquisition advances/costs from participant prepayments; funding evidence is not automatically a deductible cost | RQ-01/02/07; do not deduct one economic item twice merely because it has two source views |
| DI-05 | Require a complete approved-in-scenario funding snapshot or explicit contribution evidence; validate same-picture funding denominator and ratio | RQ-02/07; unknown funding does not choose the no-contribution branch |
| DI-06 | Use a supplied remaining prepayment balance, nonnegative title earnings, pool-level recovery and explicit forward carry | Original SV-01/02; historical backward offsets, losses and new-advance priority remain outside this policy |
| DI-07 | Preserve exact intermediates; choose rounding only at a named boundary | RQ-05 finds no general monetary mode. Original whole-dollar fixtures need no rounding change; NUM-01 tests aggregate half-away and independent half-even/per-line variants |
| DI-08 | Treat RQ-07 as a separate posting-date-cost intake profile, not a drop-in input to the incurred-date SV schedule | Its incurred dates are absent. Do not fabricate them or change the original schedule silently |
| DI-09 | LG needs separate broader hurdle evidence, per-work continuous cleared-gate evidence, gross video-proxy basis and crossed-net worksheet | RQ-03; endpoint balances alone cannot detect a temporary dip. Attestations are explicit synthetic inputs in this bounded case |
| DI-10 | Keep LG producer-fee offset on the gross candidate and zero floor as named synthetic policies | Positive LG-01 values unchanged; historical fee-offset basis, persistence, negative behavior and crossing timing are unresolved |
| DI-11 | Separate contractual video-return reserve bases from synthetic post-earnings payment holdback | RQ-04 places the reserve in named calculations, conditional on distributor status, with a redacted cap and twelve-month liquidation term. Do not treat RES-01 as that clause's implementation |
| DI-12 | Preserve actual payment evidence, issued obligation, correction authority and original opening snapshot separately | RQ-06; restatement and prospective correction are distinct policies, not a universal default |
| DI-13 | Require LG-01 outside-hurdle `effective_date < period.start`, in addition to attained/scope/evidence checks | Corrects prose/guard mismatch conservatively; equality and later dates block this seed with `LG_HURDLE_TIMING_POLICY_REQUIRED`. Same-boundary historical ordering remains unresolved |

For a synthetic period starting `2026-01-01`, a supplied attained attestation
effective `2025-12-31` passes the date check; `2026-01-01` and `2026-01-02` fail.
Passing this date check does not discharge the other evidence/scope checks.
The equality case must produce no finalized payable or consumable closing state.
The baseline remains 35 when a strictly earlier attestation and all other
preconditions are supplied. The earlier `<=` draft accepted more inputs; pin
the corrected schedule digest and disclose this delta to reviewers rather than
treating the unchanged `0.1-draft` label as an identical artifact.

The cited Lionsgate financial-ratio precision provision must not become a
global monetary rounding rule. The positive synthetic check is 12.345% to
12.35% (Ratio quantum `0.0001`), yielding 1,235 rather than 1,234.50 on 10,000.
Use it only in a named ratio-policy scenario; applicability to the development
rates and negative ratios is not established.

## First executable cases and independent checkpoints

Start with original SV-01: A cash 100,000, fee 25,000, eligible costs 10,000,
basis 65,000, earned 13,000; B cash 60,000, fee 4,500, eligible costs 5,500,
basis 50,000, share 40%, earned 20,000. Pool earned 33,000, opening prepayment
15,000, recovered 15,000, payable 18,000, closing zero. Preserve pool recovery
at pool scope. No actual cash payment follows from this calculation.

Then adapt the shareable project-generated RQ-07 package, version 1.0.0,
fixture `SPL-RQ07-SV-BUNDLE-01`, under
`ResearchAgent/fixtures/screen-accounting-package/`. Read the adjacent detailed
RQ-07 dictionary. Its JSON/CSV shapes need an explicit versioned adapter and
canonical schema validation. Synthetic approvals are not practitioner approval.

Incoming handoff status was **mapping specification only**. Engineering has now
produced an [actual canonical package and mapped run](../../cases/rq07/README.md)
under the bounded physical profile. It has not been reviewed by an accountant. The
source/demonstration reconciliation is established separately from that pending
deliverable. Before schema freeze, engineering must produce mapped facts, pinned
manifest, generated statement/trace/state, source-to-target lineage and a control
comparison preserving the documented missing dates. Then send that concrete
package for accountant review; writing the mapping instructions does not close
this gate. No payment event supplied means unknown/absent payment evidence,
not an inferred numeric zero paid.

| RQ-07 checkpoint | Expected result |
| --- | --- |
| Invoice face amounts less uncollected | 210,000 - 50,000 = 160,000 |
| Bank cash / applications / allocated title receipts | 160,000 in each separate amount space; never sum the three |
| A direct application plus allocated bundle cash | 60,000 + 40,000 = 100,000 |
| B bundle cash | 60,000; bundle parent 100,000 split 2/5 and 3/5 |
| Raw GL costs | 17,500 = 15,500 eligible + 2,000 excluded |
| Separate funding evidence | 150,000; branch/share evidence, not current receipt or duplicate deduction |
| Cash-date selection | March 31 bank value date; both applications posted April 2, available under April 4 midnight UTC cutoff |
| Cost-date selection | GL posting; missing incurred/paid dates remain absent |
| Statement | Same 33,000 earned, 15,000 recovered, 18,000 calculated unissued payable, zero closing prepayment |
| Deliberately wrong billed-cash method | 25,500 payable: test must detect the difference |
| Deliberately deduct unsupported B cost | 17,200 payable: conservation alone cannot validate eligibility |
| Deliberately substitute 50:50 bundle weights | 15,800 payable: conservation alone cannot validate allocation authority |
| Use application posting for cash period | No Q1 receipts; negative bases outside policy, so no approved alternative payable |

The five raw batch hashes and row counts in `scenario.json` were checked
against local bytes on 20 November and matched. This is not a claim that the
package passes the proposed canonical schema or a new executable compiler.
Archive original bytes/digests before adapting. Small shareable synthetic copies
may be added to future `cases/` with provenance; large/private evidence stays
external. Keep expected calculations separate from compiler output generation.

After SV and carry, LG-01 requires the new attestations and a declared work ID.
With both hurdle/gate preconditions supplied, full current receipts 300 close
the work gate from 100/100 to 400/100; proxy basis is 210; gross candidate is
30; supplied crossed-net subtotal 175 yields 35 and wins. Subtotals 100 and
150 yield the gross winner 30 and tie 30 respectively. No reserve activity is
needed. This demonstrates selected mechanisms, not derivation of crossed net
profit from source rows or the broader hurdle calculation.

SV-01 and SV-02 retain supplied opening balances and nonnegative earnings.
Keep both contractual reserve movements and synthetic holdback movements at
zero for baseline LG-01. Broader policies are deferred until a selected case
needs them. If LG-02 is chosen, the worked 6 excess-only versus 7 full-crossing-
receipt outcomes remain competing policies; neither is the compiler's default.

## Build order and acceptance

1. Record an implementation baseline: source/specification digests, supported
   operators and case profiles, interpretation IDs, and explicit unsupported
   features. The `0.1-draft` labels remain unfrozen; do not imply compatibility
   between pre-response and research-integrated examples solely from the label.
2. Implement exact arithmetic, typed finite collections, diagnostics and core
   evaluation for the supported SV subset. Author independent expected amounts
   from case policies; follow the validation plan's independent oracle boundary.
3. Implement the closed surface grammar and name/type/scope checks for that
   subset, then lower to validated core. Add positive/negative syntax and
   diagnostic cases. Unsupported operations fail explicitly.
4. Emit hygienic pure Lean modules using the pinned 4.35.0 toolchain. Compare
   independent expectations, core evaluation and generated execution. Preserve
   trace source/rule IDs and arithmetic observations, including zero results.
5. Add the wrapper and canonical codecs, then the RQ-07 adapter. Complete the
   data-contract bridge rather than accepting demonstration JSON as canonical.
   Produce statement/detail/diagnostics/reconciliation and linked closing state.
6. Pass serialized SV-02 carry, failed mapping/required-policy atomicity,
   reruns, date boundaries, exact rounding and pool-isolation checks. Run
   `lake build`, `lake exe smoke` and the new relevant checks after code changes.
7. Add the LG selected provision with independent gates/scopes and explicit
   assumptions; then separately add correction and reserve mechanisms with
   sourced or named synthetic policies. Do not silently broaden coverage.

The first milestone ends with a reproducible SV receipt-to-result run and
independent comparison, not just Lean compilation or hardcoded expected values.
Preview cannot finalize a partial shared pool or supply consumable next state.
No `sorry` or custom axioms may satisfy correctness obligations. Proof work may
cover an explicitly smaller supported subset and must identify trusted stages.

## Remaining gates and research work

The responses answer all ten original topics sufficiently for this bounded
start. [Follow-up questions](research-followups.md) narrow the remaining work.
Numerical schedule review is reported complete for selected examples; DOC-01
still lacks full ratings, clause/line trails, wording feedback and some exposure
records. RQ-07 lacks independent reader/accountant approval. Do not describe
either as fully expert-validated.

The existing specialists checked the November 15 arithmetic. A targeted
November 20 reviewer follow-up is prepared in external
`SPL_RQ08_RQ09_Review_Protocol.md`, under its matching DOC-01 heading; no reviewer
was contacted by this update or the supplied follow-up response. Outstanding
items include ratings, clause/line references, wording, separate readability and
economic dispositions, and accountant exposure. That prepared request references
the earlier November 20 digest; attach the corrected schedule's fresh digest
and the strict-date delta when forwarding it. Do not mark the date-policy
correction or the revised draft as reviewer-approved.

The corrected `language-reference.md` reviewed by this handoff has SHA-256
`86F0B12D816BD9AED44EA07DEE58EFAD20D21F3A61755636088BE58D59737FFC`.
The prepared external request identifies its earlier November 20 snapshot as
`964BCC50EAC46FA91DD1FBEBAFFECCE7804EBBAA9725B206B27BDE2552F72415`;
that digest does not identify the corrected file. Forward the current artifact
and this delta, using its current line numbers rather than stale source links.
If the language reference changes again, recompute the digest before forwarding.

Historical coverage needs missing title/acquisition records and approved rules
for loss, new funding, cost timing, fee-offset persistence and reserve recognition.
Those are feature/claim gates; they do not block an explicitly synthetic first
slice. Vendor integration waits for a named consumer and exact permitted layouts.

Skouras and both Lionsgate agreements remain development-side material. Ilshin
is only a provisional independent-family candidate, with its topic already
disclosed. Before a held-out experiment appoint a separate evaluator/custodian,
confirm family/exposure and freeze surface/core/schema, policies, manifests and
compiler/runtime identities. Retain detailed interpretation, fixture and expected
outputs outside the shared implementation context; after freeze release inputs
and interpretation for the first attempt while the evaluator keeps expected
outputs until the attempt is recorded. Do not claim a blind experiment or a
completed language extension based on the present material.

Current custody status: evaluator and access owner unassigned; participant
exposure attestations pending; no restricted package identity or readiness
confirmed. These prevent an evaluation-ready or freeze-ready claim, while
development of the disclosed synthetic cases continues.
