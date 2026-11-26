# Synthetic reserve stages, caps and supplied release schedules

This separate SPL implementation executes the frozen original synthetic
[policy](policy.md) and [casepack](neutral.json). It provides two distinct
purpose/measure ledgers: gross-basis reserve and earned-producer holdback.
Both carry USD amounts; purpose and measure checks prohibit interchange.
Two static descriptor registrations bind each original stage and genuine
purpose. Their structured-history cells use those genuine purposes in the
canonical key, so equal agreement/participant/pool/asset scopes remain separate.
`register_reserve_stages()` returns the two explicit stage references; package
preparation selects only the original declared stage. Literal descriptor
constraints also reject swapped stage/purpose references at generic admission.
Generic releases are unconditional under the selected synthetic terms. They
provide no Genius active-claim clearance, excess-return or after-liquidation
interpretation and create no payment or bank movement.

[reserve-stages.spl](reserve-stages.spl) derives once-only original receipt
fees, earnings, original Date/sequence order, cap room/clipping, all vintage
applications, calendar deadlines, original-actual-addition quotas and releases.
Receipts precede applications and releases on each Date. Calendar deadlines
come from `add_calendar_months`, with explicit clamp/reject mode. The original
fee tuple and four-component release identity remain ordered components.
Full replay verifies historical results, all state balances, processed rules,
consumed original identities, cumulative controls and complete original facts.

[source.py](source.py) supplies structural declarations and reproducibly
assembles that source, without reading original case values or an oracle.
[build_modules.py](build_modules.py) transports exact USD/Ratio values,
calendar Dates, normalized UTC instants, complete original JSON and Unicode
identities through a reversible UTF8-hex representation. Original numeric,
timestamp and Unicode spellings remain in raw originals/state. The selected
policy treats `-00:00` as known UTC with explicitly unknown local offset; no
local calendar follows. Transport computes no financial sum or deadline.

The public `reserve_stages_package` and `run_reserve_stages_package` deep-copy
caller objects. The runner reconstructs context, every frame, predecessor and
state from retained originals and checks their complete typed projections
before generic execution. Preparation failure, cancellation and unsupported
profile retries invalidate reused publications. The generic
`run_module_package` API is a **trusted prepared-binding boundary**; it does
not independently parse this case's original JSON. Direct-source negative
controls deliberately bypass the public custody guard.

The finite admission profile has at most four frames/four vintages, eight
ordinary rows per table, 32 evidence rows per frame/registry and one or two
release rules with strictly increasing 1..24 month offsets. Every unused row
and evidence record is admitted. Ordinary carry pins the original context;
the full prefix replays under each original frame's cutoff and static records
must precede the minimum prefix cutoff. Complete-period previews expose no
consumable state. Partial-history previews are outside this profile.

The frozen five independent files retain their original author's expectations;
implementation does not import or invoke the oracle. Module tests run the
original expectation methods through independent SPL-vs-oracle comparisons,
then compare every material result and restored closing-state field. They
separately exercise actual loaded serialized chains, preview, raw/typed
mismatches, direct prepared-source negatives and stale publication retries.
Reference-only controls with neutral predecessor summaries replace only the
opaque reference spelling to satisfy canonical syntax; actual publication
chains use the returned canonical reference and serialized returned cells.

Generate a new unissued registration/templates explicitly with:

```text
python -m cases.reserve-stages.build_modules
python -m unittest Tests.test_reserve_stage_oracle Tests.test_reserve_stage_modules
```

Use the pinned Lean 4.35.0 setup in the repository README. Compiler runs keep
1GiB/180s and runtime/reference/reader runs 256MiB/60s, with 64MiB wire/result
and 1GiB/100000-node logical limits. Failed bounded runs remain failures;
there is no larger-budget retry or backend fallback.

The [release reproduction guide](../../docs/spl/release-reproduction.md)
gives the current native namespace runner command for a clean built checkout.

The retained [financial-stage verification](C:/Projects/Film_TV_participation_dynamic_DSL/artifacts/spl/reserve-stage-checks-20261124-a/verification.json)
indexes 50 completed compact-v2 compare publications at the earlier registration:
the original 16 checkpoints
and six previews, plus 28 finite cap, quota, calendar, exact arithmetic,
unknown-offset, Unicode and fourth-frame checkpoints. Every complete financial
result and restored closing state matches the independent oracle. An independent
Python-emitted **financial library plus typed transport driver** was separately
compiled through C generation, object compilation and linking; its complete
status/emissions/closing/diagnostics match each native result.

Twelve additional native-source rejection controls bypass the case custody
guard, including V1 application7 then application8 despite V2 balance20,
post-liquidation application and a fifth frame. A separate public custody
control blocks before source execution. Compact lifecycle checks invalidate
reused publications for explicit-null original fractions, cancellation and
unsupported profile. The final adapter distinguishes a missing optional
fraction from an explicitly supplied null. The archive honestly retains the
earlier null-original counterexample and separate harness failures.

The earlier registration used a shared technical history purpose; its receipts
provide financial-stage credit and do not establish separate canonical keys.
The final [namespace qualification](C:/Projects/Film_TV_participation_dynamic_DSL/artifacts/spl/reserve-stage-namespaces-20261124-b/verification.json)
repeats all 16 original checkpoints, ten actual successors and six previews
with the two final descriptors, unchanged financial SPL, and independent Python
financial-library/typed-driver agreement. Nine additional atomic rejections
separately exercise public cross-cell/reference custody, intrinsic state-purpose
admission, defensive descriptor constraints and null-original admission; none
claims native-source execution. All 31 completed publications have retained
bounded-reader reports. The final isolated reference suite passes 45 methods.

The evidence includes complete publications, original facts/oracle results,
actual serialized successors, source/build/import pins, generated Lean/C/object/
executable bytes and sampled compiler/runtime/reader process reports. ZIP entries
use relative paths so long content-addressed closure names remain retainable.
These are finite correctness controls, with no quiet-host timing/SLA, universal
admitted-input capacity or compiler-correctness proof claim. Main integration
and source-specific Genius interpretation remain separate.
