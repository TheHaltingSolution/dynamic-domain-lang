# Test quality and finite coverage

23 November 2026. Working strategy for the project's completion track. The
[current harness](conformance-validation.md) supplies retained inputs and bounded
witness execution; it does not yet implement this entire strategy. Whole-compiler
proofs remain deferred under the existing user direction.

The [rounding interaction increment](rounding-interaction-design.md) now executes
a declared finite cover: 47 configurations over a 160-cell domain, covering all
86 pairs and all 40 safe mode/stage/sign triples through three backends. Its
policy-conditional metamorphic controls preserve the row/aggregate distinction.
This bounded evidence does not close the other interaction or mutation work.

## What a completion claim needs

Use the release's finite requirement/variant inventory as the denominator, with
separate compiler, canonical-interface and domain witnesses. Give every required
variant a positive example, a discriminating boundary and the relevant failure
case. Track source templates, neutral scenarios, unittest methods and backend
executions separately. A test method containing many scenarios is not one
financial case; thousands of random amounts in one template do not cover
thousands of language constructs.

For each claimed variant retain original neutral inputs, selected policy and
assumptions, all material expected intermediates, original source/binding bytes,
versions, backend outcomes, diagnostics and state. Classify rejection at the
frontend, IR, data boundary or calculation stage. A wrapper rejection does not
show execution of a native financial error path. Missing or skipped paths receive
no execution credit.

## Independent controls and adversarial examples

Have an oracle author work from the neutral requirement before reading the SPL
method. Review a small hand calculation first. Oracle calculations must own date
selection, grouping, rounding and state logic and consume original facts. Sharing
a neutral schema is useful; feeding only compiler-projected bindings to the
oracle leaves projection errors unchecked. Compare intermediates, identities,
scope and state as well as final money. Both native evaluation and emitted Lean
share runtime components, so agreement alone cannot expose every common error.

For each method deliberately choose an alternative that changes an answer:
fee before versus after share, strict versus inclusive equality, marginal versus
whole-base tiers, original versus current reversal rate, threshold versus already
issued debt, and charge versus terminal-total rounding. Preserve adopted policies
and identify each alternative as a separate synthetic method where appropriate.
These examples are disclosed development tests; independent held-out evaluation
requires separate custody and an exposure record.

## Generated sources and combinations

Build generators around typed source templates and neutral domains, recording
which expression forms, type rules and domain choices each case actually uses.
Enumerate small finite boundaries exhaustively: empty/single/many, negative/zero/
positive where admitted, below/equal/above thresholds and cutoffs, absent/present
zero, exact ties/parities and duplicate/equal/near-miss identities. Supplement
with reproducible stratified samples; retain the seed and complete failing case.

Use constrained pairwise combinations as a baseline within supported domains,
then stronger targeted interactions where failures cluster:

- rounding, aggregation, sign and tier/cap order;
- lazy branches, missing input and forward definitions;
- period boundaries, state scope, duplicates and predecessor lineage;
- gates, event ordering, base selection and effective terms;
- allocation multiplicity, parent/child conservation and residual assignment.

Record constraints and uncovered pairs explicitly. Arbitrary language programs
and all feature combinations are unbounded. A percentage is meaningful only for
a named finite catalog. Generate malformed source, fabricated native IR and
canonical-package mutations separately from well-typed runtime failures.

## Metamorphic checks and testing the tests

Attach each relation to a policy and its preconditions. Unordered exact receipt
aggregation can permit physical permutation and split/merge invariance; per-row
rounding, caps and ordered events can invalidate those relations. Identifier
renaming requires all references to move consistently. Excluded facts may leave
money unchanged while still changing audit disposition.

Use selected semantic mutations: change a comparator, recognition date, fee base,
rate, rounding stage, scope key, duplicate count, reserve vintage or state update.
Classify each as killed, survived, invalid, equivalent or unexecuted. A survivor
needs a witness or an explanation; a failed parse is not a killed financial
mutation. Avoid a mutation score without a declared valid population. The two
existing Quest rounding mutations are selected witnesses rather than such a
population.

Minimize failures while preserving the failed property, including source and
input dependencies. Keep the original failing bytes as well as any reduced case.
Test the reporting harness with deliberately wrong controls, missing backends,
skips, fixture failures and stale completion artifacts so it cannot turn missing
evidence into a pass.

## Decision coverage and performance correctness

Native traces describe observed interpreter decisions and skipped roots. Build
a source-qualified finite decision inventory before introducing a denominator;
distinguish unreachable, not attempted and observed outcomes. Instrument emitted
target execution independently before claiming its decision coverage. Compiler
line coverage, source decisions and domain-variant coverage answer different
questions and need separate reports.

Performance cohorts must pass independent numerical/state controls at every
measured size. Preserve failures, timeouts and audit-budget limits. Measure
calculation, data preparation, native audit and publication separately, including
bytes, memory and exact workload topology. An optimization needs compatibility
witnesses for errors, ordering, laziness and lineage as well as faster timings.
Performance changes must not silently drop audit evidence or change financial
operation order.
