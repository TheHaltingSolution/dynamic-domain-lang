# SPL session handoff for Readable SPL certification

26 November 2026. The next compiler research phase is to reduce the testing
surface by certifying translations **from authored Readable SPL**, proving
the boundary properties we can specify, and keeping targeted tests for
contract review and the deployed tool. The owner decided where the proof
starts and what the remaining tests should accomplish. The companion
[testing and verification strategy](testing-strategy.md) records those
decisions and the proposed proof obligations. This session established the
direction and prepared the handoff.

The [certification pilot](certification-pilot.md) records the implementation
and evidence from the follow-up work on this branch.

## Mission and intent

Screen Participation Language expresses film and television participation
and royalty calculations as readable contract rules. The project connects
those rules to checked internal representations and pure Lean calculations.
Exact quantities, explicit economic policy, versioned inputs, saved state
and inspectable audit information are central to the research.

The future tool takes an existing agreement or instructions from the
participants, proposes Readable SPL, and shows the consequences for human
review. For a contract the language can express, the tool uses the approved
compiler and checks a certificate for the translation. If an actual
expressiveness gap calls for a compiler change, the later tool may propose
a versioned extension and certify the new output. The tool should make
economic choices visible and give people discriminating examples. Proofs
can establish implications of the agreed formal rules. The participants and
their evidence establish which rules and facts should govern the deal.

The owner selected per-artifact translation certification, covering authored
Readable SPL, linked policies and the emitted Lean calculation. Certify the
compiled contract over its admissible inputs and opening states and check
artifact identity and assumptions at each run. Typed core can be an
intermediate in that proof. The authoring tool should help state explicit
input validation requirements. An independently checked admission result
should establish the declared assumptions required for settlement.

## History and current checkpoint

1. The project began with a toy lowering and kernel-checked proof. The
   SPL research implementation then added a native Lean parser, checker,
   interpreter and emitter, alongside a Python comparison implementation
   and independent financial controls. Read the [compiler handoff](compiler-handoff.md)
   and [earlier session handoff](session-handoff.md) for the design and
   case development history.
2. Contract fixtures and conformance campaigns exposed choices about
   rounding, scope, dates, policy and state, as well as compiler defects.
   The [conformance ledger](conformance-ledger.md),
   [atomic coverage inventory](c1-coverage.md) and
   [validation guide](conformance-validation.md) distinguish execution
   evidence, semantic variants and outstanding questions.
3. On 25 November the bounded release integrated the qualified cases,
   physical relationship safeguards, reports and audit, and the measured
   RR03 workflow. The exact source `87d140d` is tagged
   `spl-bounded-research-20261125`. All 1,558 methods passed across 12
   isolated worktrees with unchanged pins. Both audited four-quarter
   chains used actual public-reader state. The promoted evidence commit
   is `c27ff01`. The older handoff describes the starting snapshot and
   includes dated candidate receipts. [Release checkpoint](release-checkpoint-2026-11-25.md) ·
   [Evidence index](release-evidence-2026-11-25.json) ·
   [25 November handoff](session-handoff-2026-11-25.md)
4. At the start of this documentation work the clean shared branch
   `feature/spl-typed-quantities` was at `b0b57a5`. That commit configures a
   12-shard Windows regression in GitHub Actions in addition to the
   existing Linux job. The 1,558-method receipt belongs to the tagged
   source and its local campaign. [CI workflow](../../.github/workflows/lean.yml)

The current proof evidence includes the toy lowering and scoped SPL
lemmas. The Readable SPL certificate and independently specified
source-to-artifact claim are work for the next phase. Preserve the existing
suite as a development baseline while collecting evidence for replacing
individual assertions. The broader contract inventory, native FX and the
tool-driven extension demonstration retain their documented sequence.
[Current requirement inventory](completion-backlog.json) ·
[Owner decision on FX](ld03-owner-decision.md) ·
[Later compiler tool plan](self-modifying-compiler-demo-plan.md)

## Failure history and lessons

| What happened | What the next phase should carry forward |
| --- | --- |
| Embedded Python's `._pth` can prefer the shared checkout even when launched from a candidate checkout. Direct Lean compilation into Lake's output directories also caused incoherent native linkage. | Pin actual import origins, source, toolchain and generated artifacts. Use the coherent Lake build and keep executable identity distinct from the source-level theorem. |
| Readable multi-settlement expansion required hygienic bindings. Its separate combined compile-and-run attempt exceeded budget before the separated AOT stages passed. | Include role scope and authored source locations in source-level witnesses. Record build and runtime stages separately. |
| Earlier ordered-gate and dependent-replay runs retained custody or harness failures. Windows path length also broke some evidence retention even though shorter-path execution succeeded. | Keep fixtures immutable, verify raw facts, typed projections and returned state independently, and keep failed receipts with their original status. Use short physical worktrees and separate output directories. |
| Array-v1 output normalization misread valid records with fields named `numerator` and `denominator`. A declarative scope rejection also lacked the specific input pointer. | Include types, output projections and promised diagnostics in the relevant observations. Use small cases that distinguish a user record from a numeric representation and a pre-source rejection from a source assertion. |
| A dated 1,000-record array-v1 reconstruction hit the 64 MiB guard. The measured compact-v2 cohort later completed with separate public reload and actual state carry. | Test failures and resource behavior on the actual deployment path. Keep capacity claims tied to the measured workload and exact profile. |
| An early mutation campaign classified invalid source from reference rejection alone. The later negative campaign required a native frontend rejection. | Keep observed frontend, input admission, financial execution and publication outcomes distinct. Preserve the actual backend, stage and reason for each rejection. |
| A proof beginning at typed core can inherit a wrong Readable SPL expansion. | Define the author-facing meaning independently. Include the authored text and linked policy definitions in the certificate claim so that a changed source rule cannot be accepted simply because the emitter matches its internal translation. |

Exact failed cohorts and recoveries are indexed by the
[25 November handoff](session-handoff-2026-11-25.md#5-what-has-actually-been-verified),
[practical lessons](session-handoff-2026-11-25.md#9-practical-lessons-and-pitfalls),
[report audit evidence](report-audit-coverage.md), [mutation campaign](semantic-mutation-campaign.md) and
[capacity envelope](capacity-envelope.md). The incomplete predecessor and
preview cases are especially useful starting points for deployed-tool tests.

## Resources and locations

| Resource | Location and use |
| --- | --- |
| Shared source and setup | `C:/TheHaltingSolution/dynamic-domain-lang`. Read [AGENTS.md](../../AGENTS.md), [README.md](../../README.md) and [the toolchain pin](../../lean-toolchain) first. |
| Readable language | [Readable SPL](readable-language.md), [language reference](language-reference.md), [native parser and expansion](../../SPL/Readable.lean), [native CLI and source maps](../../SPL/Main.lean), [Python expansion](../../spl_compiler/readable.py), [Lean readable checks](../../Tests/SPLReadable.lean) and [Python readable tests](../../Tests/test_readable.py). |
| Semantics and proofs | [Core and compilation](core-and-compilation.md), [SPL proof lemmas](../../SPL/Proofs.lean), and [toy preservation theorem](../../Participation/Proofs/CompilerCorrectness.lean). |
| Validation and publication | [Data and run contract](data-and-run-contract.md), [publication lifecycle](artifact-publication-design.md), [compact-v2](compact-publication.md), [saved v1 carry receipt](v1-carry-receipt.md) and [release reproduction](release-reproduction.md). |
| Independent examples | [Readable Skouras](../../cases/sv/sv01-readable.spl) and its [original-fact oracle](../../oracles/skouras.py), [readable multi-settlement](../../cases/readable-multi/README.md), [numeric precision](../../cases/numeric-precision/README.md), [reserve stages](../../cases/reserve-stages/README.md) and [physical relationships](physical-relationships.md). Verify that the selected pilot actually covers the Readable SPL and boundary features claimed. |
| External project root | `C:/Projects/Film_TV_participation_dynamic_DSL`. Use `reference/lean4/` for pinned Lean references, `ResearchAgent/documents/` for contract and design review, `environment/` for Python and Elan, and `artifacts/spl/` for exact receipts and large outputs. [Lean index](../lean-resources.md) · [RR04 and LD03 index](rr04-ld03-integration.md) |
| Recent release receipts | Under `artifacts/spl/`, use `release-regression-87d140d-20261125-a/combined/verification.json`, `release-c09-87d140d-20261125-a/verification.json`, `release-capacity-20261125-a/campaign.json` and `resume-untracked-drafts-a/manifest.json`. |

## Next steps when work resumes

1. **Specify the claim before writing the proof.** Select a small existing
   Readable SPL example with an independent expected outcome. Record the
   accepted syntax, exact source and policy identities, supported input
   domain, error behavior and observable outputs. State what the pilot
   proves at each boundary, including the role of the Lean kernel and the
   scope of any native-execution assumptions.
2. **Build a narrow source-to-artifact proof.** Define the meaning of the
   selected Readable SPL fragment independently of its expansion. Prove
   the connection from the authored source to the checked representation
   and from there to the emitted Lean calculation. Check a certificate for
   the actual translation using an independently controlled statement.
   Exercise a changed readable rule, changed policy and mismatched artifact.
3. **Prototype one boundary obligation.** Pick one declared validation
   requirement, such as a unique original receipt or a valid predecessor.
   Connect the checked admission result to the calculation precondition.
   Preserve useful failure diagnostics and establish which failure states
   can expose a result to downstream consumers. Record the deployment
   assumptions separately from the mathematical model.
4. **Map test assertions to the promises they protect.** Sample the
   existing tests that combine an original-fact example, differential
   execution and publication. For each assertion, record the proof,
   checked assumption or residual test that covers it. Try small mutations
   such as a wrong readable expansion, a wrong policy choice, an omitted
   original and a broken successor reference. Record what catches each.
5. **Write the future tool's acceptance checks.** Start with one
   participant-facing worked example and one deployed interruption and
   reload case. Add compatibility checks for old source, policies and
   state at the boundaries the proof still assumes. Use the pinned
   `lake build`, `lake exe smoke` and focused checks after code changes.
   Keep proof assumptions explicit and avoid `sorry` and custom axioms.

The first milestone is one reproducible certificate from authored Readable
SPL, a demonstrated proof or check at one boundary, and an evidence map
showing which assertions still need tests. Carry forward the measured and
verified release as a baseline. Expand the proved domain from evidence
gathered in that pilot.

## Prompt for the next session

> Continue the SPL compiler research in the shared repository. Read
> AGENTS.md, the Lean resource index, this handoff and the testing strategy.
> Use the bounded release as the baseline. Start with one Readable SPL
> source-to-Lean certificate and one explicit input or publication boundary
> obligation. Use independent worked examples for contract choices and
> deployed integration tests for operational assumptions. Record the exact
> proof scope and which existing test assertions it can replace.
