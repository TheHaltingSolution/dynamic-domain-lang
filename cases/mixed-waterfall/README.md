# Mixed original-claim waterfall in native SPL

This is the selected `C07.MIXED_CLAIM_KINDS` research-assumption method from the
[frozen policy](policy.md) and independent [original fixture](neutral.json).
`claim-registry.spl` validates every original source and derives source capacities;
`claim-period.spl` calculates event eligibility, priority/pro-rata applications,
remaining claims and residual member entitlements. `mixed-claims.spl` replays
original historical periods and checks the actual adjacent opening state.

Original current basis240 times approved share.5 produces capacity120. Actual capital
funding100 and advance funding100 remain separate. The separate fee basis250 times
.1 produces fee25. Original entitlement200 times .5 less original return80 times .5 gives
revised entitlement60; separately evidenced actual paid80 exposes correction20.
The correction requires explicit prospective reciprocal-offset authority.

Fee-first120 applies fee25/correction20/capital75/advance0. Its next90 applies
0/0/25/65, leaving advance35. Paid80 stays80. Capital/advance applications create
unissued recoupment allocations; fee/correction applications are retained earning
offsets. Neither is reported as bank repayment. Residuals use the complete
approved roster and positive total weight, including zero-capacity cases.

All economic calculations execute in SPL. The adapter validates original shapes,
exact values and calendar decoding, serializes/restores originals, and binds the
module interface. It imports no oracle or test source. It supplies no calculated
capacity, source balance, priority recipe, selected rate, allocation or result.
SPL validates the immutable registry once at the earliest replayed as-of and the
minimum observation cutoff, both derived in source. This enforces all original
per-period static predicates without assuming monotone cutoffs. Future claim
eligibility and authority knowledge at each earning remain per-event checks.

The physical transport is `mixed-claims-original-json/3`, using the shared
`unicode-utf8-hex/1` convention. Every arbitrary original Text identity/reference
and party/group scope value is transported as lowercase UTF-8 hexadecimal.
Strict decoding rejects uppercase, odd length, invalid/overlong UTF-8 and
surrogates; composed/decomposed originals remain distinct. Fixed enums, USD,
exact values and dates retain their meanings. Canonical escaped JSON snapshots
retain every original record, source line and numeric/time spelling.

Typed tables contain no raw JSON. Separate original-frame and registry-ID
populations are checked by SPL; full originals attach to closing state outside
the financial replay accumulator. The state also pins the normalized
complete typed registry, so an otherwise financially neutral authority change
cannot evade the state boundary. Only the oracle-specified top-level registry
row order is normalized. Original strings are never normalized, trimmed or case
folded. Restoration verifies complete raw/typed correspondence before projecting
original authorities and earning records into results. This is a physical
transport assertion, not native JSON parsing or external authenticity proof.
Earlier physical versions1 and2 are rejected; there is no silent migration.
Original funding Instants additionally carry an exactly decoded UTC Date; SPL compares
that Date with the original eligible Date. No next midnight or year10000 is
manufactured when a future eligible Date is9999-12-31.
The neutral economic state remains `mixed-claim-state/1`.

Generate descriptors and unbound final/preview templates deliberately:

```powershell
python cases/mixed-waterfall/build_modules.py
python -m unittest Tests.test_mixed_claim_oracle Tests.test_mixed_claim_modules -v
```

The reusable libraries are registered function modules. Their rules are ordinary
SPL definitions/assertions; the root carries one structured history cell with
original agreement, debtor-group, pool, asset and purpose keys. Actual carry
JSON-round-trips that cell, removes only its output movement, and uses its actual
`prior_result_ref`. Preview has no consumable closing state.

The policy's admission limits are eight claims/eight roster members/12 parties,
32 rows per original table and four replayed periods. Admission bounds are not a
native publication capacity promise or an all-combinations benchmark. Native
acceptance and exact tested capacities are recorded below only after the full
frozen cohort completes. The publication guard remains64MiB. No FX, new claims,
registry amendments, current nonempty cash settlements, bank execution or
whole-compiler proof is claimed.

Draft failures remain archived under the external SPL artifacts directory as
`mixed-claims-native-draft-{a,b,c}`. Their actual second periods exceeded the
unchanged publication guard. Source-only factoring reduced the completed draft-d
baseline to37,660,227 bytes and the two-period result to58,765,085 bytes; draft-d
uses the earlier physical version1 and is not final version3 acceptance.

## Verified composite evidence

All paths below are under
`C:/Projects/Film_TV_participation_dynamic_DSL/artifacts/spl/`.

- `mixed-claims-checks-1715f26d/verification.json`: the complete physical-version2
  cohort passes51 methods in730.594624s with105 Lean commands, zero failures,
  errors or skips, and unchanged sources/core. It includes all three allocation
  recipes, actual all-kind and capital/advance carry, zero/empty/excess cases,
  event chronology, native Unicode scopes and complete publications.
- `mixed-claims-date-max-957cdbb4/verification.json`: the physical-version3
  changed-source cohort passes49 methods in408.977741s with60 Lean commands.
  It includes all22 independent controls, all23 reference module controls and
  affected native carry/preview/tamper, Unicode, raw/legacy-boundary and maximum
  future Date/UTC-day controls. The earlier decoder overflow is retained in
  `mixed-claims-date-boundary-diagnostic-a`; no year10000 value is introduced.
- `mixed-claims-lf-final-20261123-a/verification.json`: final LF source passes
  the actual all-kind two-period carry/preview/tamper method in149.884955s with
  20 Lean commands. `line-ending-equivalence.json` proves that the sole CRLF-to-LF
  source change preserves the complete parsed program excluding spans. All
  source/import/descriptor/template pins were regenerated against LF bytes.
  `final-audit.json` verifies full loaders, actual predecessor preservation,
  original frozen Git bytes, unchanged sources/core and current template pins.

Every native comparison includes reference, native IR, native-emitted and a
separate Python-emitted control. Every material result and restored state is
compared with the independent original-fact oracle. Final all-kind applications
are25/20/75/0 and0/0/25/65, leaving advance35; original paid80 stays80. Actual
previous results/artifacts remain unchanged after the successor. Preview has no
consumable state. A financially neutral original-authority mutation rejects.

The final complete results are40,132,956 bytes for the first period,66,510,872
for the actual second period and66,310,169 for preview. The largest has597,992
bytes of margin under the unchanged64MiB guard. These witness four original
claim kinds, two residual members and two adjacent actual periods; they do not
establish native four-period or maximum-cardinality publication capacity.
Eight claims and32 evidence rows were checked separately through the reference
path. Scope is composite across the three frozen source snapshots; a clean
integrated repository regression follows promotion.

Final non-README sources are frozen in
`mixed-claims-lf-final-20261123-a/freeze.json`, with compilera0e5b77d,
modulec28785f5 and runtimea7e4f8e5. All three accepted phases retained unchanged
core pins and zero shared-runtime rebuild commands. Full commands, native IR,
emitted sources, traces, actual bindings/results and earlier failures remain
external. This evidence section and ASCII multiplication spelling are the only
post-run README changes.
