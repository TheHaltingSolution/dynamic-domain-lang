# Royalties participation skill packaging plan

26 November 2026. This plan defines the eventual package and its release
behavior. Packaging, compiler repair automation, and expanded conversation
testing are later implementation tasks.

## Functionality in the final package

| Capability | Expected behavior |
| --- | --- |
| Intake and drafting | Explain the workflow, gather agreement terms and relevant evidence, and draft Readable SPL. Identify ambiguities and tie financial choices to the agreement or participant instructions. |
| Input and validation review | Describe required input formats, periods, and opening state. Link exact revisions of SPL validation modules and show their rules in a readable appendix. Identify facts the participant supplies, such as batch completeness. |
| Sample review | Include representative sample inputs and accept user-supplied or generated samples. Show independent expected outcomes alongside previews, including alternatives that change money, recipients, timing, or carried balances. |
| Approval | Record explicit approval of the exact authored source and linked policies. Reopen review when the contract's meaning changes. A preview has no settlement authority. |
| Compilation and certification | Bundle or pin a compatible compiler, verifier, runtime, and Lean toolchain. Check source, links, types, and supported features early. Deliver a runnable settlement artifact after its certificate passes. Bind the artifact to the approved source and linked policies. |
| Settlement | Recheck the certificate and artifact identity. Validate actual inputs and opening state. Support single-period and ordered series runs, public reload of completed results, and resumption from verified predecessor state when the contract requires it. |
| Repair and extension | When well-formed source cannot be certified, diagnose the stage and let the agent attempt repairs using an isolated compiler candidate. Keep the approved contract meaning fixed during a compiler repair. Treat a genuinely new language feature as a versioned extension. |
| Distribution and evidence | Include setup and invocation instructions, example source and inputs, and compatible version pins. Retain diagnostics, certificate identity, sample results, and enough build evidence to reproduce a run. |

## Compile-time decisions

1. Diagnose malformed source, unresolved names or links, and type or binding
   errors before building an executable. Point to the authored clause or
   binding where possible. Return to drafting if the source needs revision.
2. Identify an unavailable feature or known unsupported combination as early
   as the compiler can establish it. Use a distinct diagnostic when source
   passes the frontend but translation, proof generation, or certificate
   checking fails. Report resource limits separately.
3. Allow generated Lean and other intermediates in private diagnostic work.
   A failed or missing certificate blocks delivery and execution of a
   settlement artifact. Every delivered artifact must pass, including one
   obtained after repair. Broad success for well-formed SPL is a coverage goal.

## Compiler repair

Use the original source, links, observed failure, and independent controls to
reproduce the problem. Decide whether it comes from a compiler defect, a proof
or resource limitation, a contract issue, or a genuine language gap. Keep
changes in an isolated candidate and rerun the failing contract, a focused
regression, and the existing release suite before promotion. Check the new
artifact against the approved meaning with the independent certificate checker.
Preserve earlier artifacts and their version pins. A change to the contract's
meaning goes through participant review. If repair does not produce a checked
certificate within its operating budget, retain the blocked diagnostic and
candidate evidence. Release authority follows the configured approval policy.

The [self-modifying compiler demonstration](self-modifying-compiler-demo-plan.md)
describes a later extension example. Mixed currency remains under its
[existing scope decision](ld03-owner-decision.md).

## Test progression

Keep the tracked certificate census and the full release regression. Add
small contracts that isolate individual features and pairs of features, then
representative contracts combining linked policies and validators, rule
selection, folds, rounding, and ordered state carry. Include malformed and
unsupported combinations and well-typed mistranslations that fail the proof.
Turn reproducible field failures into regressions and check repairs against
independent expected results.

Expanded participant testing comes later. It will exercise intake, ambiguous
terms, worked examples, revisions, and explicit approval through the packaged
skill. [Testing strategy](testing-strategy.md) · [Verification design](general-verification-design.md)
