# Compiler extensibility and deliberate capability gaps

## Executed E0 freeze and E1 extension

K1-K3 and generic module interfaces have now been implemented. The actual frozen E0
native check of [the derived-deadline demand](../../cases/extensibility/calendar-months-demand.spl)
returns `UNSUPPORTED_BUILTIN` for `add_calendar_months`. The independently
evidenced [supplied-date workaround](../../cases/extensibility/supplied-deadline.spl)
executes canonically and agrees with the neutral reserve oracle before/on the
deadline. The external review bundle preserves the attempted source, diagnostic
and compiler pins. E0 was frozen before E1 implementation began. The supplied-date method is a legitimate solution
with a different data/evidence boundary, not a contrived failure.

Implemented E1 interface: `add_calendar_months(Date, Nat, Text) -> Date`, capability
`spl.calendar-months/1`, with explicit `clamp_day` and `reject_invalid_day`
policies. It computes directly from original creation and a natural month count.
Supported Gregorian years are 0001 through 9999. Zero months preserves a valid
date but still requires a supported policy. It does not preserve end-of-month
status implicitly or replace months with a fixed number of days.

The implementation contract uses `CALENDAR_INVALID_MONTHS` for defensive runtime
negative/fractional counts, `CALENDAR_UNSUPPORTED_POLICY`,
`CALENDAR_INVALID_TARGET_DAY` for reject-policy nonexistent dates, and
`CALENDAR_YEAR_RANGE` for a result outside the supported years. Existing Date/Nat
checker and binding errors remain the earlier boundary failures. Known invalid
literal policy names are rejected statically; a variable policy is checked when
the operation is demanded. A valid-policy operation that would reject a target
day remains lazy inside an unselected expression body.

The target and native interpreter share the admitted pure calendar primitive;
the separately authored [Python oracle](../../oracles/calendar_months.py) does not
import compiler helpers. Cases
include leap days, century rules, zero/count/range errors, direct versus iterated
clamping, and the canonical inclusive reserve release. No new correctness proof
is implied by agreement. Old-program compatibility is measured against the
frozen corpus. Adding the builtin reserves its source call name: an older custom
module alias with that exact name requires an intentional alias/source revision,
so this is not a claim that every possible old program is source compatible.

The interface and semantics above were published before implementation. The
following execution record distinguishes completed checks from the historical
protocol and candidate rationale retained below.

### Preserved baseline and packaging correction

The E0 profile is `spl-implementation/0.4.0-dev`; its immutable repository record
is [the E0 baseline](baselines/implementation-0.4.0-dev.json). Its completed
verification included 256 Python tests, `lake build` (82 targets), both smoke
executables, 14 native suites including the real trace-quota boundary, 14
registered reviews, six original/readable legacy reviews and three direct
accounting-mechanism reviews. The absent-operation probe recorded
`UNSUPPORTED_BUILTIN` for the unchanged derived-deadline source.

The first external archive, `artifacts/spl/freezes/r1-core-e0/source.zip`, omitted
`schemas/` because of an archive-inventory error. That original ZIP remains
unchanged. Replay exposed the omission; the three missing schema files were
restored only after their bytes matched the pre-extension E0 baseline hashes.
The packaging script was corrected, without changing E0 compiler sources.
The complete corrected archive is
`artifacts/spl/freezes/r1-core-e0-r2/source.zip`, with 277 files and source-tree
SHA-256 `c2756622e7edda602540282a76b68e95eb562bd17d684673112b66b815fb9d01`.
Both archives, the packaging correction and verification records remain under
the external project artifacts directory.

The extracted E0 workspace rebuilt successfully. Targeted replay confirmed the
original compiler and module identities, legacy payables 18,000/35/18,000,
Angel allocation 85, MQP fee 40, and the old calendar demand's
`UNSUPPORTED_BUILTIN` diagnostic. This targeted replay does not claim a second
complete 256-test run in the extracted workspace. The correction completes the
reproduction package; it does not retroactively make the first ZIP complete.

### Smallest implemented semantic extension

E1 adds a reusable admitted calendar operation, not a contract-name branch or a
supplied answer. [The source demand](../../cases/extensibility/calendar-months-demand.spl)
now computes its own deadline from creation, months and invalid-day policy. The
supplied-date E0 method remains executable. Both retain explicit vintage, scope,
availability, selected period, cutoff and inclusive-release rules.

The change adds [the pure Lean helper](../../SPL/Calendar.lean), the independent
reference implementation and oracle, and builtin admission through checking,
elaboration, emission, interpretation and linking. No new general parser form is
required: it uses the existing named-call syntax and typed Date/Nat/Text values.
The generic module capability scanner requires `spl.calendar-months/1` for this
call; the descriptor/package schema needs no calendar-specific economic field.
The runtime identity now pins its full local target-helper dependency closure,
including the calendar helper. This is a new supported semantic API, not a claim
that a finite lower-level program could never implement month arithmetic.

[Calendar checks](../../Tests/test_calendar_months.py) and the
[native suite](../../Tests/SPLCalendar.lean) exercise leap/century rules, explicit
policies, range and count failures, lazy branches, canonical capability admission
and inclusive reserve release. January 31 +1 +1 under clamping is March 28,
whereas January 31 +2 is March 31. A separate
[compatibility check](../../Tests/test_extension_compatibility.py) consumes actual
published E0 waterfall state under E1 and verifies 32/8 recovery, residual 35,
participant payments 49.50/25.50 and zero closing claims.

The executed E1 review bundle has 15 registered runs plus six legacy and three
direct-mechanism runs. All financial checkpoints pass. E1 `lake build` (84
targets), both smoke executables and 15 native suites pass, including the real
100,000-observation trace quota with a valid blocked prefix. The Python run
executed all 263 checks in 1091.584 seconds: 262 passed and one snapshot-invariance
check failed because policy-registry line endings were changed and restored
while tests were running, changing a pinned semantic dependency. The original
registry bytes were restored from verified E0 bytes and are now protected from
Git text conversion. All 22 affected pipeline/policy checks then passed in
81.020 seconds; the isolated invariance check also passed in 17.385 seconds.
Thus all 263 distinct checks are verified across the full run and targeted
rerun, including cross-version state and archive inventory; this is not a claim
of one clean 263-test full run. Completed logs and content pins are identified by
the current [implementation baseline](implementation-baseline.json).

Classification: **core/runtime capability**, accompanied by module admission and
identity changes. No new financial policy was inferred from vendor behavior.
This disclosed development experiment is not a held-out evaluation, a general
correctness proof, or evidence of commercial feature completeness. Adding the
builtin also reserves its source name; frozen-corpus compatibility does not
guarantee compatibility with every possible older imported alias of that name.

## Original protocol and candidate rationale

The following sections preserve the pre-extension plan. Present/future-tense
inventory statements there describe the proposed E0 experiment, not the current
E1 executable inventory. The execution record above governs actual status.

21 November 2026. The user explicitly confirmed that demonstrating a dynamically
expandable compiler is a project goal. This document makes that goal an experiment
alongside broad calculation coverage. It does not authorize runtime interpretation
of legal prose, or claim that a useful new clause must need a core change.

## What the experiment demonstrates

Show what must change when a previously unsupported contract requirement arrives:
authored terms, method module, readable syntax, type/interface, core operation,
emitter/runtime, schema, validation and tests. Preserve a runnable baseline and
the attempted encoding before changing the language. The result is evidence of
expandability, review effort and compatibility under a stated boundary. Finite
examples alone are not a general correctness proof.

Use these separate classifications:

| Change | Evidence and claim |
| --- | --- |
| Parameter | Different values under an existing supported method; demonstrates configurable terms |
| Method/library | New composition of existing operators with a typed module and case policy; demonstrates reusable methodology |
| Surface abstraction | New readable form with specified lowering into unchanged core; demonstrates frontend/language extensibility |
| Type/interface capability | New typed measure, record contract or static guarantee with compatible calculation semantics; demonstrates checked schema/type extensibility |
| Core/runtime capability | New admitted operation, result behavior or value representation, with specified semantics and implementation; demonstrates a new supported semantic API |

An ordinary method expressed by fold/lookup must not be labeled a new core
capability because its source is shorter. A new core API need not constitute a
proof of increased mathematical computability; a sufficiently rich finite
functional core may encode the algorithm at a lower abstraction level. Record
that distinction. The project is demonstrating practical language/compiler
extension, not that old arithmetic could never simulate a finite computation.

“Dynamic” here means deliberate extension to support a new requirement, including
versioned source/module/compiler changes and recompilation when needed. Runtime
plugin loading, self-modification, hot deployment and an LLM making execution-time
interpretation decisions are not required. If runtime extension later becomes a
product requirement, specify that as a separate capability and evaluation.

## Two tracks and deliberate omissions

**Open engineering demonstration:** use a disclosed synthetic requirement to
exercise the extension mechanism repeatably. Its topic and expected cases may
be known in advance. This demonstrates mechanics; it is not an unseen holdout.

**Independent extension evaluation:** after a freeze, a separate evaluator
releases a genuinely restricted provision/input package under the existing
custody protocol. Existing topical exposure, including Ilshin, is recorded.
Expected results remain with the evaluator until the first attempt is logged.
This track tests whether the language boundary is useful beyond the examples
used to design it. Do not move Angel, MQP, Roundlake or the open demonstration
into a supposedly unseen evaluation after using them for development.

Keep RULE-01, maps/grouping and an ordered fold in the first reusable baseline:
they are ordinary requirements already known to be missing. Implementing those
known demo gaps is valuable engineering, but is not the main future holdout
extension result. Do not remove a working essential feature simply to rediscover
it. Deliberately defer a bounded, documented capability that a real or explicit
synthetic case can require, and publish why it is outside the baseline scope.

## Disclosed candidate gap for the first extension demonstration

Candidate **DYN-CAL-01**: derive a reserve-vintage deadline by adding a declared
number of calendar months to a supplied creation date inside the schedule.
The public reserve research motivates the deadline category, but the vintage
origin and exact month arithmetic are still selected synthetic policies.

The current implementation exposes Date validation/comparison, period membership
and Gregorian-quarter checks; that does not by itself expose date
decomposition/construction or `add_calendar_months`. At the future R1 freeze,
verify the actual inventory again. Retain plain comparison, supplied calendar
facts and all existing features. If calendar-month derivation was already added,
this candidate no longer represents an absent API; choose another justified
gap or report that the requirement already fits.

The broader C1 target includes calendar support, so this is a **staged omission
from R1**, to be exercised before promoting that part of C1. It is not a permanent
hole in the promised broad target. The future baseline descriptor must say that
derived calendar-month deadlines are unsupported, rather than merely lacking
a pretty phrase.

For the open demonstration, a possible proposed operation is:

```text
add_calendar_months(Date, NatMonths, InvalidDayPolicy) -> Outcome<Date>
```

This is not current parser syntax. A candidate `clamp_day` policy preserves the
day when valid in the target month and otherwise uses its last valid day:

- 2024-02-29 + 12 months -> 2025-02-28.
- 2025-01-31 + 1 month -> 2025-02-28.
- 2025-01-31 + 0 months -> 2025-01-31.
- A separate `reject_invalid_day` variant fails for a nonexistent target day;
  out-of-range years fail in either policy. Negative months are outside this
  initial Nat-month interface.

Do not silently introduce “preserve last day of month” or assume iterated month
addition equals one combined addition. Under clamp-day, January 31 +1 +1 can
differ from +2. The schedule must specify whether it computes one deadline from
original vintage creation or repeatedly moves an already adjusted date.

Use a simple synthetic reserve with available balance 20 and no actual-return
application: deadline 2025-02-28, release before deadline 0 and release on that
date 20 under a separately declared inclusive due-date rule; closing balance
then becomes zero. This release is a reserve movement, not evidence of a bank
payment. Add period/cutoff, vintage and scope checks in the neutral fixture.

Legitimate baseline attempts include supplying the deadline as an evidenced
fact, using a pinned full calendar relation with map lookup, or composing an
existing date API. Record each workaround and the changed ownership/evidence
boundary. Do not forbid them to force a failure. If the complete requirement
fits the frozen core with reasonable reusable authoring, classify it as method
or surface work, not new core semantics. If internal date derivation at the
agreed abstraction is missing, an admitted date operation can be the extension.

## Other candidate gaps to investigate, not commitments

| Candidate | Expected classification to test | Why a research/case gate remains |
| --- | --- | --- |
| New readable reserve/deferment or capped redistribution idiom with documented expansion | Usually method or surface extension over folds/maps | A meaningful reviewer task and an independent economic discriminator must justify the abstraction |
| New typed domain measure or event interface with a reusable calculation module | Type/interface plus registration; may need no emitter change | Do not count schema renaming as a new method; require a static guarantee or distinct contract input boundary |
| Mutually dependent royalty bases or a specialized return/interest calculation outside the baseline's acyclic/rational API | Could require an admitted solver/numeric operation; might instead be ordinary composition or supplied facts | No such engine behavior or contractual necessity is assumed from a vendor feature name. Obtain a development-only public case and semantics before selection |

These are a gap register, not a promise of three forced core extensions. Maintain
one primary candidate and an alternate before freeze. A separate evaluator may
choose a different restricted requirement. Do not request withheld details from
the existing held-out family to choose a convenient missing operator.

## Freeze, attempt, extension and compatibility protocol

1. Complete the reusable baseline's declared scope and tests. Freeze exact
   grammar/core/interface/schema/operator inventories, module registry/import
   rules, compiler/runtime/toolchain IDs, supplied-data boundary, state/trace/error
   observations, case policies, oracle revisions and supported resource envelope.
   Record intentional omissions and known exposure separately from accidental
   unimplemented requirements. Preserve runnable source and artifacts.
2. For each track, have an independent financial author prepare neutral facts,
   expected intermediate/final values, state and failure boundaries. Use only
   development material for the open demonstration; restricted material follows
   the evaluator/custodian protocol. Reviewers record roles and prior exposure.
3. Attempt the requirement against the unchanged baseline. Retain source,
   inputs, diagnostics, low-level encodings/workarounds and time/effort. Include
   what the baseline can express, not only the first failed notation.
4. Record the smallest justified change using the classification table. Define
   its syntax/typing/evaluation/errors/trace and lowering before implementation.
   A new core operation needs independent semantics; an expansion must identify
   the unchanged core operations. Resolve evidence and policy choices explicitly.
5. Add the operator/module/phrase through the versioned extension boundary,
   keeping pure calculation and canonical validation intact. Record parser,
   checker, IR, runtime/emitter, schema/wrapper and evidence changes separately.
   A contract-specific bypass or precomputed answer is not a reusable extension.
6. Compare the independent expectation, core interpreter and emitted execution,
   including selected branches, status, balances and required audit. Run frozen
   prior cases in their original versions and under the extension where
   compatibility is claimed. Retain intentional behavior/version changes.
7. Report the actual outcome: configurable terms, reusable method, new surface,
   stronger typing or new core API; effort and files changed; clarity/reviewer
   feedback; preserved and changed behavior. A fits-without-core-change result
   is valid. If a core-extension example is still desired, select another
   justified candidate and preserve the first result rather than rewriting it.

Proof scope remains explicit. The future preservation target covers the new
operation only when its semantics and lowering have actually been proved;
existing scalar lemmas and regression agreement do not extend that claim.

## Immediate consequence for the release plan

The compiler team should tag DYN-CAL-01 as **intentionally deferred from R1,
subject to inventory/case confirmation**, while implementing the known reusable
kernel and current business methods. Preserve a baseline before adding that
optional API. Broad feature coverage and extensibility evidence are separate
deliverables: completing a longer feature checklist does not by itself execute
the extension experiment, and a successful extension demo does not establish
commercial feature completeness.
