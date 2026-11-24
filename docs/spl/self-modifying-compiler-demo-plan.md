# Later self-modifying compiler demonstration

23 November 2026. This records the owner's intended later tool/skill. It is a
future work plan, not an implemented skill, and does not start currency work.
Read [the owner decision](ld03-owner-decision.md) for the current boundary.

## Sequence selected by the owner

Complete the other authorized finite SPL feature, performance and testing goals
first. Keep native mixed-currency/FX support out during that work. When those
goals are verified complete, or the owner explicitly begins this later phase,
build the tool/skill and use mixed-currency contracts as a demonstration case.
The existing deferred/outside-scope proof, professional and external-custody
obligations do not silently become compiler engineering tasks through this plan.

## Intended workflow

1. Retain the original contract, original facts, evidence, interpretation
   choices and required outputs. Report ambiguity or missing evidence separately
   from limitations of SPL; do not silently invent contractual policy.
2. Attempt the strongest faithful existing-SPL encoding, using available
   records, exact arithmetic, libraries, folds and approved interfaces. Keep
   successful encodings. A missing builtin name alone is not a failed encoding.
3. For a remaining unsupported requirement, retain the attempted source,
   diagnostics, independent original-fact controls and a precise capability
   description. The selected compiler-extensibility claim also permits an
   explicitly named stronger checked interface; label that distinction honestly.
4. Let the tool create a candidate compiler extension in an isolated checkout,
   with versioned syntax/types/IR/runtime/codecs/module/state changes as needed.
   Extend the reusable mechanism rather than inserting contract-name dispatch.
5. Check the new capability against independent controls, boundaries, invalid
   input/IR, error behavior and actual state carry. Replay the frozen old
   source/fact/state corpus. Measure implementation effort and performance;
   retain failures and old issued artifacts with their original pins.
6. Report whether the original contract was expressible already, the extension
   is verified, or a precise ambiguity/unsupported requirement remains. No
   claim of translating every possible contract follows from a finite demo.

These steps describe tool behavior to implement later. No automatic publication,
release or claim of whole-compiler correctness is provided by this document.

## Reserved mixed-currency case

The finite native target remains USD/EUR, exact directed quotes and evidence/date
selection, source/contract/payment currencies kept separate, explicit rounding,
wrong-currency/direction failures and unchanged prior-contract/state replay.
The first numeric discriminator is EUR100 at USD1.10/EUR giving USD110; a reverse
quote cannot be silently substituted.

RR04/LD03 already found faithful record-backed FX possible. Preserve that method
as a real comparison. The future tool must not delete its arithmetic or assert
financial impossibility merely because `Money<EUR>` is rejected today. New
native currency checks are a stronger checked-domain interface. The demonstration
must disclose which requirement caused the compiler extension.

The current non-FX usage-unit mechanism remains supporting engineering. It may
supply reusable admission/provenance infrastructure; no currency entry, FX
builtin or native EUR acceptance is implemented in preparation for the demo.

## Evidence required before calling the demonstration complete

Retain tool instructions/implementation, original contract and interpretation
record, old-language attempt, capability decision, isolated compiler change,
independent oracle, exact new-case/backend evidence, old-corpus/state replay,
version/definition pins, measured performance and an honest result report.
Do not mark the tool or native FX complete from this plan or from a test count.
