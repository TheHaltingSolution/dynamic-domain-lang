# General SPL verification design

Every delivered runnable artifact requires a checked certificate. Broad
certificate availability across the [implemented feature inventory](release-feature-inventory.md)
is a coverage goal. The certificate
connects authored SPL and pinned linked modules to the actual emitted Lean
calculation. Its meaning ranges over admitted inputs and opening state. The
same artifact can settle an ordered series of periods and carry its own state
between periods. The pinned Lean-to-native toolchain is a trusted dependency.

The current [rounding pilot](certification-pilot.md) demonstrates the claim for
two exact documents. It remains a witness while reusable proofs replace the
fixed-source characterization. This design names the obligations for the
general claim and the checks that remain at runtime.

## Claim and observations

The [language reference](language-reference.md) and [Readable grammar](readable-language.md)
specify authored SPL. The compiler implements those rules. For verification,
use a reference interpretation independent of the native translation under
test, and make its assumptions explicit. The source side
includes the original text, explicit footer bindings and exact linked module
closure. Its financial interpretation is a function from typed inputs and
opening state to a success or failure. The kernel must check that for every
admitted input and opening state, the emitted Lean calculation has the same
observations as this independently specified source meaning.

The observation relation names the versioned promises being certified. Include
acceptance and rejection by contract validation, exact typed amounts, rounding,
selected recipient and policy decisions, the first promised error, emitted
reports, and closing inputs to a successor. Trace and source locations deserve
explicit observation definitions where returned to participants. A certificate
that compares settlement values and errors covers that projection. The public
trace and physical artifact format then need their own checked relationships.

The proof relates semantics for the particular contract. Grow certificate
availability through small feature combinations, larger representative
contracts, and regressions from field failures. A theorem that every
well-formed combination obtains a certificate would strengthen the coverage
claim. The release gate applies to each delivered artifact. An uncertifiable
case remains blocked and can enter the future
[packaged repair workflow](skill-packaging-plan.md).

## Translation checkpoints

| Stage | Required connection |
| --- | --- |
| Authored source and linked modules | Establish the independent interpretation of the exact UTF-8 text. Check the Readable title, bindings, phrase scope, control flow, report fields and policy provenance against that interpretation. Bind the exact transitive link closure and the owning language, schema, dimensions and conversion versions. For core-authored modules, check the original core text and typed export interface. |
| Resolved, typed program | Show that parsing, Readable expansion, name resolution, linking and elaboration preserve meaning. Cover dependency order, fresh role bindings, scopes, false branches, typed collection binders, module calls, and generated provenance where promised. Structural IR validation establishes well-formed IR and its checked annotations. A source-to-IR meaning check is also required. |
| Emitted Lean settlement | Check the actual generated Lean definition against the source meaning or a separately justified IR meaning. Prove reusable equivalence lemmas for runtime operations and composition, including evaluation order, typed zero, duplicates, ordered rules, failures, and state/output wiring. Check that the executable entry invokes the definition that was proved. |
| Checked build and invocation | Bind the source, dependency closure, declared interfaces, supported versions, Lean calculation, proof, and invocation profile to the receipt. Verify artifact identity at execution and pass the actual admitted inputs through the checked entry. Bind the approved build to the executed native bytes when using native compilation. |

An incremental path can compare the normal generated Lean settlement with a
separately produced reference formulation and ask the kernel to check their
equality on every input. This helps isolate lowering and exposes behavior
differences between implementations. A reference implementation is executable
evidence. It serves as the mathematical source meaning only to the extent
that its relationship to a reviewed independent source specification is proved.
Likewise, comparing two translations that both start after Readable expansion
cannot detect a shared change in the meaning of an authored clause.

Prefer compositional kernel proofs organized by feature family. Start from
the existing scalar arithmetic lemmas, then extend to records and ports,
control flow and observable failures, options, collection processing,
indexed operations, folds, linking, explicit versions and units, and the
Readable surface and authored origins. Exercise expected failures as soon as
each family is added. Shared optimization and runtime primitives can be used
once their correctness statements name the intended meaning. Preserve the
normal native code path and use the proof as a separate checked deliverable.

The comparative certificate implemented in this phase stages authored text
and its link manifest, independently parses and checks them with the Python
frontend, and compares their semantic projection with the native typed IR.
The structural comparison includes authored citations, policy provenance,
types and the linked program. It omits exact source spans and trace node IDs.
The Lean kernel then checks equality of the freshly emitted settlement and
the Python emitter's reference settlement, including the generated entry
point's connection to that settlement. This works over general source inputs
where the two paths agree. The Python source semantics and shared SPL
runtime meanings remain assumptions of the comparative claim. Additional
kernel proofs can reduce those assumptions and extend coverage. [Source correspondence](../../spl_compiler/source_verification.py) ·
[Kernel target check](../../spl_compiler/target_verification.py) ·
[Certificate and execution CLI](../../spl_compiler/verification.py)

The [verification census](../../scripts/spl_verification_census.py) checks
registered contract closures and unregistered authored fixtures through that
CLI. It records finite availability evidence for the repository corpus. Use
the command below after a pinned build and put the report in the external
artifacts folder.

```powershell
python -m scripts.spl_verification_census --output REPORT.json --jobs 4
```

## Linkable input validation

The input format determines what data reaches an SPL validation module. The
runtime decodes bytes into typed port values and reports transport errors such
as malformed JSON or an unsupported decimal encoding. A versioned SPL module
then implements the contract's rules over those typed values. For example, a
receipt format can expose original IDs, accounting dates and exact USD amounts.
A validator can check distinct IDs, membership in a half-open period, batch
scope or agreement with a supplied roster. Use an imported SPL function from a
top-level assertion, or use its validated output as a demanded calculation
input. A check in an unused definition does not guard a settlement.

The review appendix can show the exact SPL validation module, its input schema,
configuration and assertions. Certificates bind the selected revision, source
and link closure. New formats or revisions can provide different validators.
Document which rules are enforced by typed transport, which are authored in
linked or local SPL, and which depend on external agreement evidence. A
successful roster check can establish coverage relative to the supplied roster.

There are two separate proof obligations. **Preservation** says that the
emitted validator accepts and rejects as the authored validator specifies,
including promised diagnostics. **Soundness of admission** says that every
successful validation establishes the premises needed by settlement, such as
uniqueness of receipt IDs in the checked collection. Put these premises in the
calculation theorem or quantify over a typed admitted input domain whose
construction has been justified. Apply the same distinction to opening state
and to each period's input in a series. External completeness, evidence
authority and policy interpretation remain participant and integration checks.

The example validators link versioned receipt and posted-cost formats into one
Readable schedule and enforce uniqueness and half-open period membership.
The tests run the guards through normal emission and a certified series with a
failed later period. The kernel-checked admission lemma connects successful
execution of the actual runtime assertion, scalar summation and `inPeriod`
operations to half-open membership for every supplied typed row. Grouped
uniqueness and raw decoding retain separate proof obligations. [Validation appendices](../../cases/validation/README.md) ·
[Admission soundness proof](../../SPL/ValidationProofs.lean)

## Period series

A single-period settlement is a pure transition from typed input and opening
values to emissions and closing values, or a diagnostic. The reusable artifact
driver takes an ordered series of typed period inputs and initial openings,
runs the same transition for every period, and passes each successful closing
value to the next transition. Preserve declared opening and closing ports and
their scope. The caller supplies the series order. Calendar continuity and
scope rules, when required by the agreement, belong in the relevant input or
state validation.

For the opt-in `compile-series` path, the runtime envelope contains `periods`
and `openings`. A nonempty successful series returns its period results and
final closing state. A failing series reports the first failing zero-based
period and exposes no partial finance or successor state from that invocation.
The pure loop proof should establish ordered repeated application, exact carry,
and the first failure property. Compose this loop theorem with each contract's
period translation theorem. A loop theorem parameterized by an arbitrary
step is reusable across contracts. It establishes source-to-artifact
preservation only after the actual emitted step has been certified.

Typed series execution and saved state custody meet at the runtime boundary.
At the start of a later invocation, validate the initial opening against the
contract's state requirements and the consumed completed predecessor. The
physical publication writer and public reader handle committed successor state.
Test interruption, restart, incompatible predecessor scope and failed
validation at that boundary. [Run contract](data-and-run-contract.md) ·
[Publication contract](artifact-publication-design.md)

## Trusted deployment boundary and remaining evidence

Trust the pinned Lean kernel, elaboration/compilation pipeline below the
checked Lean artifact, native runtime and ordinary process and filesystem
behavior. Identify the pinned toolchain and trusted runtime dependencies,
check the build recipe and artifact identities, and bind the invoked executable
to the approved build. Verify certificate assumptions with the kernel, without
permitting custom axioms or admitted proofs. A digest establishes identity
within the deployment's custody model. It does not establish that a file was
authorized, that facts are accurate, or that an arbitrary executable is safe
to run.

Retain the release regression and report the proof, checked assumption or
residual test that protects each promise. Check compatibility for old source,
linked policy and successor state. Test source mutations, changed links, wrong
runtime tools and replaced artifacts, including differences that remain well
typed. Test resource exhaustion and restart through the deployed path. The
independent financial controls remain useful for contract interpretation.
Skill packaging and expanded participant conversation tests are a later phase.
[Testing strategy](testing-strategy.md) · [Frozen regression reproduction](release-reproduction.md)

## Run the implemented checks

From the repository root with the pinned Lean setup, build the compiler and
certify an artifact into a new directory. The verifier stores the exact source,
typed IR, emitted Lean and certificate. Supply `--link` with the resolved native
link manifest for a contract that incorporates external modules.

```powershell
lake build
python -m spl_compiler.verification certify cases/sv/rq07-readable.spl work/rq07 --mode series
python -m spl_compiler.verification verify work/rq07
python -m spl_compiler.verification run work/rq07 series.json --output work/result
```

The series binding file contains `periods`, an ordered array of the schedule's
input objects, and `openings`, the first period's opening bindings. A success
returns each period and the final `closing` values. With `--output`, the v1
public artifact reader can reload committed results. Resuming a series still
requires preparing typed opening bindings from the approved predecessor.
The Windows `--native` path uses the pinned Lake build inputs and records the
checked executable and build digests. The Lean execution path is the default.

```powershell
lake exe smoke
python -m unittest Tests.test_source_verification Tests.test_target_verification `
  Tests.test_linkable_validation Tests.test_series_verification
python -m scripts.spl_verification_census --output work/census.json --jobs 4
```

The census records the outcome for each tracked case registration and standalone
case source, including any source, signature or proof mismatch. Each successful
result checks one emitted artifact for all decoded inputs. Corpus results are
finite evidence about availability of certificates.

The [context lemmas](../../SPL/ContextProofs.lean) additionally prove that a
successful checker binding extends the lexical context with the declared type
at a fresh name and preserves existing resolutions. Successful typed decoding
preserves the declared port order and aligns the returned values with the
parsed context. The theorem calls the existing type parser and value decoder.
