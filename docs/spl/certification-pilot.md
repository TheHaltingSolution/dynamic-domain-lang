# Readable SPL certification pilot

The royalties participation skill leads a participant from terms and worked
examples to a reviewed Readable SPL draft, approval, compilation, and later
settlement runs. In a project conversation, invoke `$royalties-participation`.
The repository includes the [skill](../../.agents/skills/royalties-participation/SKILL.md)
and the [command walkthrough](../../.agents/skills/royalties-participation/references/commands.md).

## Certified schedules and observations

The pilot recognizes exact authored UTF-8 bytes for two schedules in
`spl/0.1-draft`. Both apply a fixed 50% share to two eligible USD receipt
amounts and use `money-rounding@1` at a cent quantum with half-even rounding.
The [aggregate schedule](../../cases/certification/aggregate-readable.spl)
rounds the combined share. The
[per-receipt schedule](../../cases/certification/row-readable.spl) rounds each
share before adding them. The [prior numeric precision cohort](../../cases/numeric-precision/README.md)
supplies an independent original-fact discriminator. Two USD 0.01 receipts
produce USD 0.01 and USD 0.00, respectively. The schedules are synthetic.

The kernel claim ranges over every pair of exact rational amounts with empty
opening state. It observes the `participation` emission, the complete success
or financial-error outcome, and empty closing state. At this scope eligible
receipt selection, period, and recipient come from the participant's supplied
facts. The artifact delivers one calculated, unissued amount. Audit trace
equivalence and stateful settlement remain outside the claim.

## Source-to-artifact check

The normal native frontend parses the draft, expands its readable rules, links
the money rounding policy, checks bindings and types, and emits Lean. The
[kernel proof](../../cases/certification/KernelProof.lean) defines source
meaning by the two approved documents and the linked policy source. Its
rounding definition works from the two neighboring cents and the even-tie
rule. The checker controls that definition and the theorem statement. The
proof imports the emitted module, checks its actual `settle` against the
independent observation, and checks the standalone entry point's connection
to the same `settle` and declared Money bindings. It checks the assumptions of
the named theorems. A proof beginning after readable expansion would miss a
wrong source interpretation.

Approval records bind a reviewed draft, linked policy manifest and worked
examples through a digest. The participant conversation records the authority
for approval. A subsequent compilation or run checks that the review still
corresponds to the supplied draft and policy. Further previews of those same
terms leave the approved review available for later runs. Each run stages the
approved source and linked policy, regenerates the emitted Lean module,
compares it with the certified artifact, rechecks the proof, and runs the
checked module with the admitted inputs. The published result includes the
checked receipt with source, link, proof, toolchain, and artifact identities.
The check assumes a trusted checkout and pinned toolchain. It establishes
Lean-level semantics. OS process execution, compiled Lean runtime code,
local filesystem behavior, and the authority of the approver remain
operational dependencies.

## Admission and publication

The [native receipt admission](../../SPL/RoyaltiesAdmission.lean) reads the
staged input bytes, requires exactly two receipt records, decodes each supplied
nonempty ASCII ID and exact USD amount, and checks original IDs for uniqueness. Its theorem
establishes distinct supplied IDs when admission succeeds. The returned pair
is projected in order to the two declared Money bindings. Admission is relative
to the supplied batch. Eligibility, completeness of the real receipts and
receipt identity across batches are participant-supplied assumptions.

The tool bounds each receipt input file at 64 KiB. Lean subprocess timeouts
and Python's exact-integer transport limits also apply. The deployed path
reuses the v1 publication writer and public reader for a single writer per
output directory. Preview results live in the review workspace. The deployed
run publishes a completed blocked envelope with
empty financial output for failed admission or certification. A successful
run is public once the completion marker commits. Each invocation in this
profile has empty closing state. An interrupted final marker write leaves its
compatibility files on disk and the public reader refuses that invocation.
The tool assumes a trusted local operator with control of the workspace and
artifacts. The existing [publication contract](artifact-publication-design.md)
specifies what its file identity and completion checks establish.

## Assertion coverage

The existing regression suite still runs. These are the boundaries to use
when deciding whether a later certificate can replace a particular assertion.

| Existing promise and control | Coverage in this pilot |
| --- | --- |
| Exact money and row versus aggregate placement in `test_reference_all_signed_money_modes_and_points` and `test_native_signed_money_modes_and_points` | The proof covers fixed half-even, a cent quantum, a half share, and two receipts over all exact rationals. The original-fact scenarios still establish which rounding rule the participants intend. The larger numeric precision program and other modes and quanta still use their own tests. |
| Readable-to-original parity in `test_three_profiles_match_original_calculations` | The proof covers only the two exact authored schedules. Skouras, RQ-07, Lionsgate, source locations, and generic parser acceptance retain their checks. |
| Original population and custody in `test_native_original_population_source_checks_and_trusted_boundary` | Successful pilot admission establishes distinct IDs for the returned pair. Supplied population membership and completeness in the numeric precision program still use their respective controls. Removing a receipt and duplicating an ID are deployed-input rejection tests. |
| Published finance and actual predecessor carry in `test_generic_native_compare_commits_real_state_and_serialized_successor` | Stateless success, blocked runs, and interruption followed by public reload are exercised in the pilot. The stateful contracts still rely on the original carry and compatibility tests. |
| Approval and identity across a run | A changed review, changed source or linked policy, and a mismatched artifact or certificate need explicit gate tests. Kernel preservation covers the semantics of the artifact admitted by those gates. |

The [certificate tests](../../Tests/test_certification.py) exercise both
rounding choices, a missing receipt for the proof, changed authored and
linked policy bytes, and replaced Lean artifacts with original and edited
certificate hashes. A separate mutation makes the native emitter produce a
well-typed 40% calculation while the approved source still says 50%. The
kernel rejects the translation and the compiler publishes neither artifact
nor certificate. The [tool tests](../../Tests/test_royalties_tool.py) also
exercise rejected input after a successful invocation and verify that the
public reader returns only the new blocked result.

The [conversation acceptance checks](../../.agents/skills/royalties-participation/references/rounding-review.md)
exercise the authoring workflow and participant decisions. Deployed CLI tests
exercise preview, approval, both compiled rounding choices, a later batch,
admission failures, and an interrupted publication followed by public reload.
The test suite also applies a reduced execution budget to the actual Lean
settlement process and checks its blocked publication.
Run them with the pinned project environment and Lake build.

```powershell
lake build
lake exe smoke
lake env lean --run Tests/SPLBindings.lean
python -m unittest Tests.test_certification Tests.test_royalties_tool
```
