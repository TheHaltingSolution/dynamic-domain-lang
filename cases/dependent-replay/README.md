# Authorized dependent replay and prospective attribution

This implementation follows the separately authored [original casepack](neutral.json),
[policy](policy.md), [independent oracle](../../oracles/dependent_replay.py) and
[design](../../docs/spl/dependent-replay-design.md). Two pinned synthetic routes
separate a calculated restatement from prospective signed attribution. Neither
route changes an original issued artifact, records a new issue/payment or claims
professional approval.

SPL independently reconstructs original flat/marginal earnings from original
bases and terms, checks the original issued amounts and cumulative meters, and
validates actual original payments through their separate bank/application/
complete-population controls. Original issued100 and actual paid80 remain
different measures. Replacing original basis200 with180 at50% produces90; next
original basis60 earns30. Restatement recognizes90/30; prospective attribution
retains issued100 and recognizes current30−10=20. Both reconcile outstanding40.

The dependent case has original P2 marginal earnings10 from lower20 at10% and
upper40 at20%, with opening cumulative basis200 and threshold220. Correcting P1
to180 changes that opening and derives lower40/upper20, P2 earnings8 and closing
basis240. Historical deltas−10/−2 yield outstanding18 after actual paid80.
Prospective attribution retains issued100/10 and proposes signed current−12.
The native source derives every slice, delta, replacement effect, period line,
recognition and issued/unissued/paid bridge. It does not treat the correction as
a revised-total payment or borrow an independent unchanged P2 answer.

## Known views, authority and state

Every original issue is recalculated under its own original receipt cutoff.
New replacement evidence does not enter that historical original view. All
static registry rows, including unused evidence/terms, are validated against the
minimum current-frame cutoff, calculated in SPL without assuming increasing
cutoffs. Each frame and correction separately applies its own observation,
effective Date, approval/recording and scope predicates.

Authority links the original issue/receipt/basis line, replacement, selected
route, predecessor and entire already-closed chronological dependent suffix.
Receipt Date/sequence and correction recorded-Date/sequence are complete economic
keys; ties reject. Physical order, technical slots and lexical IDs do not select
monetary priority. Replacement/request/original identity consumption prevents
relabeling or repeating the same correction. The issued-time UTC Date comparison
does not construct a next midnight beyond9999-12-31.

State retains the original registry, original frame facts, complete recalculated
results, active original replacements, consumed identities, period views and
meters. The complete prefix is replayed before incoming state and predecessor
summary can reconcile. Actual carry uses JSON-round-tripped closing cells,
removes only their output movement and retains the actual key, quantity, boundary
and canonical predecessor reference. Original supplied issued-result references
remain original facts; they are not fabricated canonical execution evidence.
References identify provenance rather than authenticate external custody.

The original current-cash population must explicitly be complete-empty. Missing
completeness is unknown; nonempty current participation cash requires another
policy. Original bankpaid80 is retained independently. Negative account balance
or an original receipt overpayment after replay rejects without a floor or an
implicit recovery against fresh earnings. Existing authorized-offset policies
are separate. Chained replacements, changed original terms/registry, partial
periods, bank execution, external issue approval and FX are outside this profile.

## Physical interface and execution boundary

Physical profile `dependent-replay-original-json/1` uses identity codec
`unicode-utf8-hex/1`: canonical lowercase, even-length strict UTF-8 hexadecimal,
with unnormalized original Unicode strings and escaped raw records retained.
Original IDs containing delimiters remain distinct. Original replacement lookup
uses the validated original frame case ID plus replacement ID; a replacement ID
is not incorrectly assumed globally unique across different frames. Adjustment
keys are tuples of exact original components, not invented concatenated IDs.
USD, Dates, Instants, Money and Ratio keep their domain types.

The real agreement, pool and asset use checked intrinsic IDs. Beneficiary,
payer and recipient identities remain explicit encoded Text with separate role
checks; the generic outer participant is bridged by descriptor constraints.
The payer is never forced into the beneficiary's intrinsic participant slot.
Original IDs, scopes, sources, number/time lexemes and original fields survive
in raw context/registry/frame snapshots. Registry state arrays use original-ID
order; their explicit Dates/sequences govern economics.

The adapter parses exact original values, shapes, original line-reference syntax,
date ordinals/midnights and issued/paid UTC Dates mechanically. Evidence slots
enumerate original evidence positions only. Native SPL checks every evidence ID,
slot range/uniqueness, matching fact reference, kind, scope, approval and cutoff.
No financial totals, selected replacements, earned amounts or recognition are
calculated by the adapter. Thin typed rows drive financial loops; original raw
snapshots stay outside those hot folds. Native original-ID/order/population ties
remain explicit. The canonical transport verifies exact raw/typed and restored
state correspondence; arbitrary native bindings do not gain a claim that SPL
parses JSON or proves an original record's authenticity.

The public wrapper takes a private package copy and repeats full mechanical
preparation from retained original context, frames and state before executing.
It checks complete inputs, selected policy, scope, cutoff, period and cells.
Preparation mismatches atomically publish an empty blocked result, replacing
previous completion even when an artifact destination is reused. Generic module
CLI execution instead assumes trusted prepared typed bindings; its caller must
establish that custody correspondence. Native source still decides all financial,
authority, original-known-view and history-admission predicates.

Preview reviews the same complete checkpoint and has no consumable closing
state. Finite limits are four total ledger periods, eight rows per ordinary
table and32 evidence rows. These are admission limits, not native compilation
or publication-capacity promises. Instants follow the frozen oracle's explicit
known-offset/UTC-range admission, with exact fractions and lowercase `t`/`z`;
no ambient timezone or local legal calendar is inferred.

Generate the descriptor and four fresh unbound templates with:

```powershell
python -m cases.dependent-replay.build_modules
```

The35 independent oracle methods and18 owned reference/transport methods cover
both routes/scenarios, all material intermediate values, actual serialized
successors without repeated corrections, threshold/fraction/upward/no-op cases,
old issued/paid controls, full suffix authority, aliases/order/scope/cutoff/
population failures, raw Unicode/lexemes, evidence slots and public preparation
mutation/atomicity. Direct generic binding negatives are reference-stage controls.
The later composite native qualification below supersedes the earlier pending
status while preserving each cohort at its actual code and build pins.

## Composite native qualification, 24 November 2026

This candidate uses compiler/module/runtime `441f0e7c/04db83ff/77a18c19`.
Financial source, descriptor, four templates and all five independent originals
are unchanged. Complete results and original state, rather than final totals
alone, are compared through reference evaluation, native IR, native-emitted C
and the independent Python emitter's embedded program compiled to C.

The records under the external `artifacts/spl` folder have distinct scopes:

- `dependent-replay-native-helper-20261123-a`: original 70-method run remains
  **failed**, with 67 successful methods, three harness failures and one archive
  cleanup error. Two output-bearing paths exceeded Windows MAX_PATH; an intrinsic
  scope rejection correctly occurred at canonical admission before native
  execution. The failure does not establish a financial source discrepancy.
- `dependent-replay-native-followup-20261124-a`: 23-method run remains **failed**.
  Its 22 non-lifecycle methods passed, including all eight real first/successor
  publications across simple/dependent and restatement/prospective routes.
  Five lifecycle assertions expected an unwrapped child message from the public
  bounded loader; the running marker correctly invalidated the old result.
  Long archive-copy destinations also caused a cleanup error. Those successful
  publications were preserved independently by extended-path custody copies.
- `dependent-replay-native-final-20261124-a`: **24 methods pass**, zero failures,
  errors or skips, 490.955163 test seconds (498.504635 including cached required
  builds/smokes and audits), no source or compiled drift. This fixes the
  mechanical quantity-boundary/header tie, separates three intrinsic canonical
  scope admissions from reached native source guards, tests public wrapped
  loader rejection without accepting resource failures, and uses relative ZIP
  retention. Actual dependent first/successor/preview controls, all original
  reference controls, raw/cell custody, cancellation, invalid audit settings and
  publication failures pass. The ZIP has 2,284 individually SHA-checked entries.

Root separately bounded-reloads eleven complete publications: the eight prior
first/successor results and three final dependent first/successor/preview results.
Every original monetary intermediate, issued artifact, paid80, full history,
state, actual predecessor reference and no-repeat successor agrees with the
frozen independent oracle. The simple bridge remains40; the genuine tier replay
changes original10 to8 and leaves18. Preview has no consumable state.

This is a composite finite qualification, not a claim that all 74 final test
methods ran as one cohort or that main integration is complete. Wrong original
scope/shape/type cases retain their actual admission-layer credit; a generic
prepared binding bypass does not prove raw JSON custody. Fixed runtime/reader
256MiB/60s, compiler-only1GiB/180s, wire/result64MiB, logical1GiB and100,000-node
guards remain unchanged. Process metrics are child working sets, not overall
parent/host memory or an SLA. Original authentication, external issuance,
bank execution, overpayment recovery and FX remain outside this profile.

The eighteen whitespace-only lines in the frozen financial SPL are preserved
with its existing source/descriptor pins; other new files pass whitespace checks.
