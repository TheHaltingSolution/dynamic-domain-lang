# Ordered work-gate source profile

This SPL implementation follows the independently authored [policy](policy.md),
[original fixture](neutral.json) and [design](../../docs/spl/ordered-gate-design.md).
It implements the selected synthetic `split_reopen` convention and six explicitly
named controls: `opening_gate`, `closing_gate`, `continuous_history`,
`split_latch`, `full_cross_reopen` and `next_row_reopen`. These conventions do not
claim historical accounting reproduction or professional interpretation approval.
The existing cleared Lionsgate profile is separate and unchanged.

The source reconstructs opening receipts and costs from complete original
history. It derives receipt recognition as the later of original received and
earned Instants, uses incurred Instants for costs, and sorts the exact economic
Instant plus the explicitly authorized sequence. It checks the complete supplied
ordering authority; input position and identity do not break economic ties.
Classification, reductions, complete populations, original identity consumption,
scope, observations, evidence and the independently supplied aggregate/net
attestations are checked before producing a consumable result. Excluded rows
remain visible and validated. Full receipts drive the gate; the home-video proxy
applies afterward to admitted payout amounts.

The baseline reconstructs opening80/100 and closes150/130. Split/reopen yields6,
latch8, full crossing7, next-row4, opening0, closing11 and current-prefix
continuous0. Reversing the separately authorized simultaneous receipt/cost order
yields4. Gross inapplicability, applicable zero and unknown evidence remain
distinct. The zero crossed-net worksheet is an explicit supplied input; no net
ledger or aggregate-hurdle calculation is invented. Fee and reserve operations
are explicitly zero under this selected policy. Entitlement remains unissued;
payment evidence and bank movements are outside the profile.

## Original and physical interfaces

`build_modules.py` transports originals into physical profile
`ordered-gates-original-json/1`. Identity transport `unicode-utf8-hex/1` uses
canonical lowercase, even-length hexadecimal strict UTF-8. Original Unicode
scalar strings, including embedded delimiters and composed/decomposed spellings,
round-trip without normalization. Currency, enums, dates and quantities keep their
domain meanings. Exact escaped raw original JSON is retained alongside typed
financial/evidence rows. The adapter validates their correspondence and rejects
solved-amount/rank fields; SPL derives all financial and ordering results.

Separate typed `frames` and raw `original_frames` avoid inserting full original
JSON into hot financial loops. Native source checks tie their ordered IDs and
table populations together. Transient original-position `row_slot` and evidence
slots support lookups and are checked for range, uniqueness and matching original
IDs. They are transport metadata, not financial identities or economic priority.
Physical permutations may renumber slots while preserving normalized economics.
The canonical transport checks exact raw/typed and restored-state correspondence;
arbitrary native bindings do not gain a claim that SPL parses JSON or authenticates
the external originals.

The public `run_ordered_gate_package` wrapper repeats these mechanical checks
immediately before execution. It reconstructs complete typed/raw frame populations
and their historical prefix, restores the full opening, checks the actual cell and
predecessor correspondence, and ties the outer scope, period and cutoff to the
prepared facts. Post-builder changes to typed amounts and reported totals cannot
silently leave different retained originals attached. A mismatch yields an empty
blocked publication and invalidates a reused destination's prior completion.
Cell metadata and its quantity boundary must match the current original period
and scope. Cancellation during preparation, invalid profile selection and failed
publication leave an incomplete invocation rather than a consumable older success.
The generic module API and CLI accept trusted prepared bindings; their direct use
does not acquire this case wrapper's original-correspondence guarantee. Neither
boundary authenticates a supplied source or predecessor reference.

The outer canonical execution scope retains the real work agreement, participant,
asset and work pool through encoded identities. Descriptor checks bridge the work
pool Text field to that outer pool. Aggregate evidence retains its separate
agreement/participant scope. The crossed-net pool is a separately checked Text
identity with its genuine agreement, participant and member asset; it is never
coerced into the outer work pool's intrinsic `Id<Pool>` scope.

Original timestamps and numeric lexemes remain in raw records. Typed Instants
compare exact fractions and explicit offsets. Logical output's exact timestamp
counter uses the oracle's Gregorian ordinal-day origin; mechanical conversion
accounts for its one-day difference from the compiler's epoch. It does not choose
recognition time, round submicroseconds or infer an ambient timezone.

## History and execution

`genesis` supplies an explicit zero boundary. `original_history` discloses raw
adjacent historical frames without claiming they were previously executed.
`prior_result` instead requires the actual serialized canonical closing cell and
matching predecessor summary/reference. SPL replays every frame with its own
cutoff, pins scope/policy/registry/research and compares full reconstructed state.
Q1→Q2→Q3 gives80/100→150/130→170/160, new gross0/6/2 and cumulative8.
References identify provenance; they do not assert cryptographic source approval.

Preview reviews the same complete checkpoint and emits no consumable closing
state. It is not a partial-history calculation. The finite input profile allows
four total periods, 32 economic rows per period and 64 rows per supporting table;
each cost may have64 reductions. These input bounds do not assert native
compilation or publication capacity at their maxima. Late-history delta ingestion,
amendments, negative raw receipts, general reserves, crossed-net reconstruction,
payment execution and FX remain outside this profile.

Execution keeps `audit_profile="array-v1"` as the wrapper default. Explicit
`audit_profile="compact-v2"` requires a native backend and publication destination.
Both completed formats use their own validated loaders. Native case tests select
compact v2, retaining the audit sidecar while separately compiling and executing
the independently Python-generated financial target under the same compiler and
runtime limits. The native and Python financial generators remain separate.

Generate fresh unbound descriptor/templates with:

```powershell
python -m cases.ordered-gates.build_modules
```

`Tests.test_ordered_gate_modules` retains 16 explicit reference/adapter methods
and adds 18 native selectors plus four prepared-wrapper controls. The controls compare every
material output and complete original closing state against the independent
oracle, including actual serialized three-period carry, preview, seven methods,
cutoff/scope/population/alias/tie failures, exact timestamps, raw lexemes and
physical slot checks. Explicit direct-physical negatives distinguish native source
validation from the public wrapper's preparation rejection. One negative boundary
control documents that the generic API can calculate changed typed facts while
the case wrapper rejects their inconsistent retained originals; that generic
result has no original-fact case qualification. Final native/canonical acceptance
uses the separately dated composite evidence below.

An external evidence launcher may retain the test work tree as a ZIP with relative
entries. Short owned output prefixes retain a `control.json` method mapping and
avoid Windows path limits; these paths do not affect financial ordering or identity.

## Recorded finite evidence

External records remain under
`C:/Projects/Film_TV_participation_dynamic_DSL/artifacts/spl`:

- `ordered-gates-reference-023482bc`: the original 29 oracle and 16 reference/adapter
  methods, including actual serialized reference carry and preview.
- `ordered-gates-full-20261123-a`: all 66 methods ran; all 18 native selectors passed.
  The attempt remains **failed** for two shared-cell boundary preparation subtests
  and one Windows path-limit retention error. Only 165 missing immutable closure
  copies were recovered from their exact frozen SHA-pinned bytes; financial results
  and traces were not regenerated.
- `ordered-gates-followup-20261124-a`: 23 affected controls passed after adding cell
  metadata/boundary ties, cancellation invalidation, short owned paths and ZIP
  retention. This includes the original 16 reference/adapter methods, all four
  prepared-wrapper methods and three affected native methods.

The initial native record uses compiler `22dbd43d` / module `4071115d`; the follow-up
uses `441f0e7c` / `04db83ff`, with runtime `77a18c19`. Economic SPL `a40b438e`, the
five independent specification files, descriptor and unbound templates are exact
throughout. This is composite finite evidence, not one all-final-source cohort or
a general compilation/publication capacity claim. Actual Q1/Q2/Q3 carry yields
new gross 0/6/2 and cumulative 8; same-Q3 preview has no consumable state. Every
material comparison and complete restored original state is checked, with the
issuance and payment execution boundary remaining outside this profile.
