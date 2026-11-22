# Proposed next core semantics

Execution note: K1-K3 and the M1b dimensional slice now have bounded
implementations recorded in [implementation.md](implementation.md). M1b is
locally verified profile `0.4.3-dev`, completed 22 November 2026 on
`feature/spl-typed-quantities`; `main` remains at merged `018dde1` unchanged.
The [implementation baseline](implementation-baseline.json) records local
verification, not a GitHub release or push. The previous
[`0.4.2-dev` record](baselines/implementation-0.4.2-dev.json) is preserved
byte-for-byte. The original proposals and starting points below remain
historical design material.

## M1b implemented dimensional boundary

The dictionary `spl.units/1` admits exactly `Download` and `UsageMinute`, with
case-sensitive names and no implicit conversion. Existing generic syntax admits
`Quantity<U>` and `Rate<U,USD>` as typed inputs. There is no new English literal
grammar. Money and Ratio retain their legacy runtime representation and typed-IR
assumptions; the new tagged values do not establish an intrinsically typed runtime.

In the matrix, `Q` is `Quantity<U>`, `R` is `Rate<U,USD>` and `s` is Ratio.
Two operands written as Q/Q or R/R must have identical unit/currency types.

| Operation | Result and requirement |
| --- | --- |
| `Q + Q`, `Q - Q`; `R + R`, `R - R` | Matching dimensional type retained |
| Equality and ordering comparisons | Bool, for matching dimensional types |
| `Q * s`, `s * Q`, `Q / s` | Quantity retained; demanded division rejects zero |
| `R * s`, `s * R`, `R / s` | Rate retained; demanded division rejects zero |
| `Q * R`, `R * Q` | Money<USD>, for a matching denominator unit |
| `Q / Q`, `R / R` | Ratio; demanded division rejects zero |
| Unary negation, `abs`, matching `min`/`max` | Dimensional type retained |
| `quantize(value, quantum, mode)` | Positive matching-dimensional quantum; type retained |
| Empty `sum` | Tagged zero of the checked quantity/rate type |

Quantization uses the existing explicit modes `floor`, `ceiling`, `toward_zero`,
`half_even` and `half_away_from_zero`. Signed and fractional dimensional values
are valid exact core values. Money/Quantity, Quantity*Money, unmatched dimensions,
other products/quotients, non-USD rates and FX are unsupported. Legacy scalar
arithmetic signatures and outputs are unchanged.

Records, lists, Options, tuples, maps as values, sum/filter/map, finite folds and
registered imports/exports retain tags. Sorting admits dimensional scalar keys
and dimensional tuple components. Quantity/Rate remain unsupported in Map,
grouping and ordered-fold key types, including nested tuple keys.

Every descriptor in the import closure must declare capability
`spl.quantities/1`, codec `spl-quantity/1` and its used admitted units in
`interface.dictionaries["spl.units/1"]` when it uses these types. Unused local
schemas and export signatures are also admitted. Canonical domain bounds and
conservation targets require explicit matching dimensions; empty declared
quantity/rate collections cannot be reconciled against an untagged scalar zero.
The [module boundary](module-interface-v1.md#m1b-dimensional-interfaces-and-state)
defines recursive transport and complete dimensional state identity.

Defensive IR admission checks every type-bearing position recursively, including
otherwise empty collection paths; 15 negative direct-IR cases reject unknown
units and unsupported rate currencies. Final local verification passed one
complete combined run of 352 Python checks in 1638.702 seconds, 16 native suites,
the 86-target build and both smokes, with compiler/schema sources unchanged.
All 35 review paths passed: 24 legacy, four quantity and seven M1 cases.

The [selected Download source](../../cases/quantities/download-participation.spl)
computes 100 Download * USD 1.50/Download = USD 150, then a separate 50% share =
USD 75. Its proposed policy requires nonnegative selected-period facts/rate and
opening meter; it does not impose a universal returns/loss rule. Actual native
successor carry adds 0.5 Download to the prior tagged meter, giving 100.5 and
USD 0.375 earned. Existing toy and scalar proof scopes do not cover the new
tagged runtime paths. Completed local verification and remaining work are recorded
in [the implementation report](implementation.md#m1b-candidate-quantities-and-monetary-rates).

## Original dimensional proposal: quantities and per-unit rates

The following proposal is retained as the design history superseded by the
implemented M1b boundary above; its future-tense statements are not the current
implementation inventory.

The next type extension should first admit typed inputs and outputs for
`Quantity<U>` and `Rate<U,USD>`. Existing generic type syntax is sufficient;
new readable literal phrases are a later authoring change. Use a finite,
versioned unit dictionary and an explicit capability/codec declaration, rather
than interpreting an arbitrary string as a registered dimension.

The first registered witness is quantity 100 times USD 1.50 per matching unit,
giving USD 150, followed by a separately declared 50% share giving USD 75.
Zero and fractional quantities remain exact. Nonnegativity is a selected case
restriction, not a universal type rule for every future return or adjustment.

The implementation contract must cover all of these boundaries together:

- Same-unit quantity addition/subtraction and comparison; quantity times a
  dimensionless ratio; matching quantity times monetary-per-unit rate yielding
  money. Unsupported dimensional combinations fail statically. Rate direction
  and units cannot be erased into interchangeable ordinary `Ratio` inputs.
- Explicit quantity/rate transport tags, recursive decoding in records and
  collections, native IR validation, generated execution, independent reference
  execution, and type-preserving output/audit metadata. A checker-only admission
  or an untagged decimal workaround does not complete the slice.
- Typed zero behavior for empty sums and collections, demanded zero-division
  failures, and either implemented same-unit quantization or explicit rejection
  of unsupported dimensional quantization. Existing numeric defaults must not
  silently turn a quantity result into an ordinary rational.
- Unit-safe state identity before exposing new dimensional balances through
  generic canonical state. The current state scope/key schema has no general
  unit dimension; extending it requires compatibility checks and explicit
  migration where keys change. Existing USD opening decoding also has a USD
  default and must not be reused unchanged for later EUR balances.

After this slice, finite USD/EUR and directional `FX<EUR,USD>` can use the same
dimensional boundary. EUR 100 at USD 1.10/EUR must produce USD 110 with an
explicitly selected quote identity/date, observation cutoff and rounding policy.
Reversed pairs, mixed-currency addition and missing or ambiguous observations
must fail. Quote-source and fallback policies for a named real contract remain
case decisions; no such policy is inferred from the new numeric types.

The next milestone's financial tier/cap/guarantee modules use existing USD
semantics and can proceed independently of this compiler extension. Complete
compiler preservation proofs remain deferred as requested.

21 November 2026. Design proposal for LD-02; not implemented syntax, a released
core version, an accounting-policy approval or a vendor-compatibility claim.

The next reusable capabilities should be finite rule selection, typed indexed
maps, grouping/joins and explicit ordered state transitions. These support
different accounting methods through composition without giving a domain phrase
an unspecified runtime meaning. Every amount-affecting selector, ordering,
membership, default and state purpose remains visible in a schedule or explicitly
incorporated policy definition.

Read this proposal with [the existing core](core-and-compilation.md),
[language reference](language-reference.md), [readable authoring rules](readable-language.md)
and [implementation inventory](implementation.md). This document refines the
proposed operators already listed in the core design; it does not silently add
them to the executable profile. Release priority and module registration belong
to the next-release plan.

## Actual starting point

The inspected executable code includes unique selection (`SPL.IR.Expr.choose`,
`SPL.Runtime.choose`), list map/filter/sum and scalar-key sorting. Unique selection
checks predicates and lazily evaluates the selected body. It does not yet have
first-class registered rule IDs/priorities. The current IR collection node has
one item binder, rather than a general two-binder state transition.

General tuple-key Map types/construction, indexed map access, grouping, joins,
priority tables and general ordered folds are not claimed by the current
implementation inventory. Compiler-internal environment `lookup` functions are
not a source-level Map capability. Tuple keys and their total ordering require
new type/check/IR/runtime work. Existing scalar preservation lemmas do not prove
any of these proposed collection or trace semantics.

## Common semantic contract

All inputs and collections are finite and immutable. Numeric values remain exact
and unit checked. Evaluation returns success(value, semantic observations) or
failure(diagnostic, observations up to failure). A failure yields no finalized
payable or consumable closing state for its atomic settlement scope. A trace
prefix is evidence of attempted computation, not permission to commit an
intermediate balance. Bounds cannot truncate a list, join, rule set or trace.

Ordinary schema/reference validation checks all supplied required fields before
execution. Lazy bodies do not excuse malformed structural input. Economic
expressions, including division and required option extraction, evaluate only
when demanded under the operator rules below. Every body and predicate is still
statically typed even if a particular execution will not demand it.

An unordered input relation is first canonicalized by its declared unique
instance identity. An explicitly ordered list keeps its order. Physical CSV
position, host map iteration and execution scheduling are never implicit
economic ordering. Duplicate values can be legitimate list occurrences; they
retain distinct instance keys or an explicitly ordered list position. Duplicate
fact identity remains an intake error under the data contract.

Diagnostics carry operator/call identity, source span, economic scope and the
implicated rule/key/row/event IDs. The proposed codes below are an interface to
freeze with the feature, not a claim that current diagnostics already use them.

## RULE-01 unique and priority selection

### Typed interface

The following is abstract IR notation, not an accepted source grammar:

```text
RuleArm<C,T> = {rule_id, predicate(context:C):Bool,
               body(context:C):T, priority:Int?, evidence_refs}
choose_unique : List<RuleArm<C,T>> × C × OptionalFallback<T> -> Outcome<T>
choose_priority : List<RuleArm<C,T>> × C × OptionalFallback<T> -> Outcome<T>
```

Predicate/body notation describes finite first-order IR bodies with an explicit
context binder. Rules do not contain executable source text, dynamically loaded
Lean or escaping functions. Imported rate-table data can supply typed conditions
and values through a published compiled rule schema. Merely importing a string
called a condition cannot execute it. All arms/fallback return the same type,
including currency and scope refinements. Each ordinary arm has a nonempty
unique rule ID; priority arms require an Int priority. One optional fallback is
separate from ordinary arms and has its own observation/evidence identity.

### Evaluation order and results

1. Validate rule structure and unique IDs before testing applicability. Duplicate
   IDs fail `DUPLICATE_RULE_ID`, including duplicates whose predicates are false.
   Reject absent priorities for priority selection; do not default them to zero.
2. Evaluate ordinary predicates in ascending rule-ID order, using the pinned ID
   ordering. Priorities do not skip lower-priority predicates. Evaluate every
   predicate if none fails. At the first predicate failure, stop with that
   diagnostic and mark later predicates not evaluated. No arm or fallback body
   runs. A successful higher-priority match cannot hide a malformed predicate.
3. For unique selection, one match selects that arm; two or more matches fail
   `AMBIGUOUS_RULE`, even if body values would be equal. Do not evaluate bodies
   to discover whether conflicting policies happen to agree numerically.
4. For priority selection, select the single matching arm with greatest priority.
   A tie at that greatest matched priority fails `AMBIGUOUS_RULE`. Ties among
   strictly lower-priority matches do not block a unique greater match.
5. With no ordinary match, select the explicit fallback if present; otherwise
   fail `NO_APPLICABLE_RULE`. A fallback is not a low-priority ordinary rule and
   does not compete with a match whose priority is negative. An empty registered
   rule list is allowed only if a fallback and result type are explicit;
   otherwise reject it as `EMPTY_RULE_SET` during checking.
6. Evaluate exactly the selected body, once. Its failure propagates; it does not
   trigger the fallback or the next matching rule. A selected zero is a valid
   value with `calculated_zero`, never a missing rule. Other bodies and an
   unused fallback remain not evaluated. The output retains selected rule ID,
   applicability evidence and all successful predicate results.

Applicability includes any effective-window, territory/title/party and evidence
tests declared by the schedule. The engine does not infer specificity, latest
amendment precedence or consent from a rule label. Boolean short-circuit within
one predicate remains the published left-to-right language behavior.

### Numeric witnesses

For receipt USD 100, priority default fallback 0.10 and an applicable territory
arm at priority -5 and rate 0.20 produce USD 20, not USD 10. A French arm rate
0 produces USD 0 without invoking the fallback. Two unique-mode matches at
0.20 fail even though either body would produce USD 20. Matching priority
arms 3/0.20 and 7/0.40 produce USD 40; two matches at priority 7 fail.

An unmatched body containing `USD 1 / 0` is not demanded. A selected body with
that expression fails rather than returning the fallback. A lower-priority
predicate containing demanded division by zero blocks selection even when a
higher-priority predicate matched. These distinctions require separate traces.

## MAP-01 typed finite indexed maps

### Keys and construction

```text
make_map : List<A> × key(A):K × value(A):V -> Outcome<Map<K,V>>
lookup : Map<K,V> × K -> Option<V>
entries : Map<K,V> -> List<{key:K,value:V}>
```

K must be a declared total-order key type: Bool, Int/Nat, Date, a versioned enum,
opaque namespaced Id, or a finite tuple of admitted keys. Money, Ratio, arbitrary
records, Option and locale-dependent display text are not initial key types.
Text-like codes must be validated into a declared ID/enum first. Tuple arity and
component types are fixed; `(AgreementId,AssetId)` differs from `(AssetId,AgreementId)`.
No partial-index lookup or numeric/text coercion occurs.

Equality is exact typed equality. Order is false before true, numeric integer
order, chronological Date order, enum order declared by its pinned schema,
Unicode scalar lexicographic opaque-ID order after the supported normalization
profile, and lexicographic tuple component order. Enum version changes that
change order are semantic changes. The initial ASCII-only implementation profile
must keep rejecting unsupported ID forms until full normalization is implemented;
this proposal does not silently broaden the codec.

Construction has a specified key-first phase. Evaluate each key exactly once in
input order, propagating the first error. Then reject any repeated key with
`DUPLICATE_MAP_KEY`, even if values are identical. Report all source identities
for the smallest repeated key. Do not evaluate any values when a duplicate is
present. After unique keys are established, evaluate values in ascending key
order, propagating the first error. Return a map whose abstract `entries` order
is ascending key order, regardless of storage representation. This sequencing
makes duplicate identity diagnosis independent of a bad value expression and
must be preserved by interpreter and emitter.

Lookup returns `some(value)` or `none`; a present USD 0 differs from absence.
`require_some` demands an explicit error code, while matching Option can supply
a visible economic fallback. Multiple indices must be supplied as one complete
tuple. There is no ambient zero, nearest key, wildcard or latest-version lookup.

Immutable replacement can initially expand into rebuilding a map from its
entries, after checking whether the target key must already exist. Insertion
uses a unique-key construction; accidental overwrite is never a constructor
feature. A new optimized persistent-update operator is unnecessary until its
semantics and performance need are justified. Update means a new value, not
mutation of opening state or an input collection.

### Witness

Keys `(agreement-1,picture-A)` and `(agreement-1,picture-B)` holding USD 0 and
USD 25 yield `some(0)` and `some(25)`; picture-C yields `none`. A second A row
holding USD 0 still fails construction. Reversing the two unique input rows
preserves entries A then B and map business observations, assuming pure total
key/value projections; input-side validation diagnostics remain attributable to
their source IDs. A tuple in the wrong namespace order fails typing.

## REL-01 grouping and joins

### Grouping

`group_by(rows,key)` returns `Map<K,List<A>>` containing observed keys only.
Evaluate keys once in row order and propagate the first key error. Each group's
rows preserve original relative order and multiplicity. Entries use Map's
canonical key order. An empty input gives an empty map, not a singleton unknown
group. Absent Option keys are not implicitly a SQL null group: the caller must
reject, exclude with reason, or map them into an explicit tagged domain key.

To produce zero-receipt titles, map over an explicit authorized title universe
and look up each group; choose an empty typed list for absent groups and use a
typed zero sum. Universe membership is policy/input, not discovered from receipts.
Grouping does not authorize cross-title recovery or erase source lineage.

With A receipts 60 and 40, B receipt 20 and authorized title C with no receipt,
group sums are A=100 and B=20. There is no C group. An explicit universe report
can produce C=0; an unobserved title is not thereby entitled to an opening balance.

### Inner equijoin

`join(left,right,left_key,right_key)` returns `List<{left:L,right:R}>` with equal
typed keys. Key result types must be identical admitted K. Evaluate all left
keys once in left order, then all right keys once in right order; propagate
the first key error. For successful keys, output one pair per matching occurrence,
ordered by left position and then right position. No deduplication, nearest
match, wildcard matching, temporal matching or case-insensitive comparison occurs.
No match produces no pair. Empty left produces no pairs, but an invalid demanded
right key still fails under this strict key-validation contract.

Multiplicity is deliberate: one USD 100 receipt joined to two matching category
rows creates two pairs; summing receipt amounts after that join gives USD 200.
Two matching left and three right rows produce six pairs. Pair identity includes
both occurrence identities. An optimizer cannot replace this with set semantics.
Each consumer must name the measure it sums and reconcile its join cardinality.

Required dimension lookup should generally use `make_map` plus checked `lookup`,
rejecting duplicate dimensions before multiplying facts. A checked many-to-one
join can expand to that pattern. It must reject missing dimensions rather than
quietly adopting the inner join's omission behavior.

### Absence-preserving join

A proposed `left_join` convenience returns `List<{left:L,right:Option<R>}>`.
Use the same eager key checks and order as inner join. For a left occurrence
with no match emit exactly one pair with none; otherwise emit one some-pair per
right match. It is not an implicit one-to-one join. The caller must handle none
before an amount is demanded. A checked at-most-one variant can expand through
grouping/map lookup and cardinality assertions. Do not introduce SQL null values
or default missing rate zero.

Group and join may be implemented initially as finite list traversals. Whether
they are primitive IR nodes or versioned library expansions is an implementation
choice only if type, multiplicity, error order and observations are identical.
A named inner join/group observation must still link to its input occurrences.

## FOLD-01 bounded ordered state transitions

### Interface and ordering contract

```text
fold : List<E> × initial:S × step(state:S,event:E):S -> Outcome<S>
ordered_fold(events, initial, semantic_key, tie_policy, step)
```

`step` is an explicit nonrecursive first-order IR body with state and event
binders. It can use finite lists, records, maps, exact arithmetic, lazy branches
and assertions. It returns one new S of the same fixed type. It cannot change a
schema, modify a captured binding, perform I/O or create unbounded recursion.
Local observations carry the event instance identity. A state record can include
observed outputs in a finite list; its growth remains subject to declared bounds.

Plain `fold` is a left fold over an already ordered list: s0=initial and
s(i+1)=step(si,ei). It evaluates the initial state, then steps once in list order;
empty input returns the evaluated initial state. `ordered_fold` is a transparent
expansion: evaluate/validate semantic keys, resolve ties according to declared
policy, sort, then plain fold. There is no automatic timestamp or priority field.

An economic ordering key is distinct from a trace serialization key. The former
can change entitlement; the latter merely orders equivalent observations. An
example economic key is (effective_date, approved_event_priority), with an
explicit tie policy for equal keys. An event ID may be appended only when the
schedule explicitly adopts ID order as the economic tie convention. Stable sort
or source position cannot resolve an otherwise unresolved legal tie.

The default equal-semantic-key policy is `UNRESOLVED_EVENT_ORDER`. A schedule
can instead declare an approved additional key, or group simultaneous events
and supply a specifically defined simultaneous transition. The engine does not
infer commutativity from equal totals or automatically prove that tied steps
commute. A future verified commuting-step optimization is a separate capability.

The order-validation phase rejects duplicate event identity and unresolved
semantic-key ties before evaluating economic steps. An ordered explicit event
path can supply a validated unique sequence index instead of inferred chronology;
its authority and scope are still inputs. As-of availability and economic
effective time are separate filters performed under the selected schedule.

### State errors and observation

At each step, read si, evaluate only demanded step expressions, validate the
step's declared invariants and produce si+1. A failure stops later steps. The
prefix records the attempted event and last successful state, but no successor
state or partial payable is finalized for the atomic scope. No retry skips the
bad event and no input/opening record is consumed or mutated. Replaying identical
inputs and opening state reconstructs identical business values and event path.

Each step observation includes operator ID, event ID, semantic key, adopted tie
policy/evidence, scope, state-before and state-after (or typed movement links),
selected rule/candidate IDs, exact operands, rounding and invariant outcomes.
Canonical trace ordering can use stable operator/event/instance keys after the
economic dependency edges are fixed. Traces must preserve intermediate threshold,
cap and balance effects; equal opening/closing endpoints do not imply equal paths.

Run bounds must specify maximum input events, intermediate collection cardinality,
join pairs, nested-step/trace observations and supported execution resources.
Exceeding any limit fails `RESOURCE_LIMIT`; no first-N-events result is valid.
Bound checks are explicit implementation envelopes, not financial caps. Pure
Lean semantics recurse structurally over finite event lists; operational resource
limits sit outside the unbounded mathematical result and return no approximation.

### Witnesses

Under an explicitly synthetic advances-before-earnings policy, start with
available advance USD 0 and events issue 15,000 then earn 10,000. Recover 10,000,
pay zero and close advance 5,000. Reverse those transitions and earnings pay
10,000 before the advance exists, leaving advance 15,000. Same event multiset,
different economics: ordering must be declared, not chosen for convenience.

For a synthetic reserve cap 30, opening vintage balance 12, apply 7, release 5,
then add 20 closes 20 without exceeding 30. Add 20 first reaches 32 and fails a
per-transition cap, even though period-end balance would also be 20. Reserve
vintage matching and the basis/payment stage are separate schedule rules.

For an unlatching gate, opening receipts/costs 100/100, cost 20 and then receipt
30 visits 100/120 before closing 130/120. A latch model may give a different
receipt entitlement. Fold supplies the event path; it does not select either
interpretation or imply an ordered policy is authorized by a contract.

## Surface sketches and expansion boundaries

These phrases are proposals only; the current parser must reject them until a
versioned syntax and expansion are implemented:

```text
Select the single applicable Participation Rate from Territory Rules.
Select Participation Rate by declared priority, otherwise Default Rate.
Index Opening Claims by Agreement, Participant and Claim Identifier.
Group Eligible Receipts by Picture Identifier.
Match each Receipt to exactly one Territory Rule Record.
Apply Events in Effective Date then Approved Priority order;
  fail on an unresolved ordering tie;
  carry Available Advance and Accrued Payable through each event.
```

Each human phrase needs explicit typed registrations for collections, context,
keys, body/step, scope and evidence. Headings and names never identify a rate
table, legal priority, party or event-date selector implicitly. The step and all
amount-affecting choices must remain readable or explicitly incorporated, rather
than being hidden in a binding footer labeled technical.

| Capability | Extension boundary |
| --- | --- |
| Registered unique selection | Existing lazy unique calculation can be retained, but stable rule IDs/context and canonical predicate/trace order require explicit implementation work. Source-order arms cannot silently acquire a different observable error order. |
| Priority selection | Can expand to evaluated predicate records, maximum priority and a unique winning choice once finite list/key facilities exist; a dedicated IR node may preserve simpler audit observations. No new numeric mathematics is needed. |
| Map and tuple keys | New executable structural types and operations; internal environment lookup is insufficient. Sorted association lists are an adequate initial pure runtime. |
| Group/inner/left join | Finite expansions over lists/maps/folds are possible. Multiplicity, key-check order and trace contract must survive an expansion. |
| Ordered fold | General two-binder finite transition is a new executable operator; ordered wrapper can expand to key validation/sort plus fold. No unrestricted recursion, clock or hidden mutation is required. |
| Waterfalls, tier rules, reserve aging, proportional allocation | Methods/libraries over the primitives when their economics is explicit. They are not approved policies or vendor-compatible features merely because expressible. |

None of these extensions makes a raw vendor export a validated financial input.
Adapters, economic authorization and reporting profiles remain separate work.

## Acceptance witnesses and interactions

Acceptance requires reviewed independent expected values, agreement of native
IR interpretation/emitted Lean/separate reference implementation, and matching
intermediate scopes, statuses and semantic observations. Numeric equality alone
does not excuse rule ambiguity, join multiplication or an incorrect event path.

| ID | Test and required observation |
| --- | --- |
| RULE-01A | USD 100, selected 20% gives 20; selected 0% gives calculated_zero and selected rule ID, not fallback. |
| RULE-01B | No match selects explicit 10% fallback giving 10; no fallback fails NO_APPLICABLE_RULE. Negative-priority ordinary match still wins over fallback. |
| RULE-01C | Two unique matches or equal highest priorities fail before body evaluation; a lower-priority tie does not block a unique higher winner. |
| RULE-01D | Unselected body division by zero stays not evaluated; selected-body error propagates; predicate error blocks selection before any body. Rule-list permutations preserve registered-ID predicate order. |
| MAP-01A | Present zero versus absent key stay distinct. Duplicate equal-valued keys fail before value-body evaluation; wrong tuple namespace/order fails checking. |
| MAP-01B | Map construction permutation with total pure projections preserves canonical entries/observations. No overwrite, locale matching or partial-index lookup. |
| REL-01A | Group 60+40 at A and 20 at B gives A100/B20; C appears as zero only under explicit authorized universe completion. Empty group map and typed empty sum remain distinct values. |
| REL-01B | One 100 receipt joined to two matching dimensions yields two pairs and sum200; checked many-to-one variant fails duplicate dimension instead. Two-by-three gives six pairs in specified pair order. |
| REL-01C | Unmatched inner-join row yields no pair; left join yields one none pair; required dimension lookup fails. Preserve source row and reason for each outcome. |
| FOLD-01A | Advance issue15,000 then earn10,000 gives closing5,000/pay0; reverse gives closing15,000/pay10,000. Unresolved same-time order fails before steps. |
| FOLD-01B | Cap witness reaches32 and fails when add20 precedes old-vintage release/application; period-end equality must not mask failure. |
| FOLD-01C | Mid-period gate dip is visible despite positive endpoints. Empty events return unchanged initial state; failed event preserves diagnostic prefix but no final state. |
| COMP-01 | Receipts US100/CA200/FR75/other50; selected rates .20/.40/0/fallback.10 give earnings20/80/0/5=105. Group into one explicitly authorized pool, opening advance70, recover70, payable35, closing0. Trace zero FR, fallback other, each selected rule and pool movement. |
| COMP-02 | Partition COMP-01 into two authorized pools and prove no cross-pool recovery. An absent opening-map cell blocks that pool; a present zero cell is valid. Joined duplicate membership must fail the checked relationship before duplicating earnings. |
| COMP-03 | Two receipts .05 at 10%: quantize each with half-away cent gives .02; sum exact first then quantize gives .01. Moving grouping, rules or fold across quantization is invalid optimization. |
| COMP-04 | Duplicate effective rule IDs fail even in a group with selected zero; unused result bodies stay lazy, but structural duplicate validation still runs. |
| COMP-05 | In a fold, fail the second event's required map lookup: no third transition, no closing output; earlier event trace is retained and replay with repaired data starts from original opening snapshot. |
| COMP-06 | Permute unordered source arrays with unchanged IDs: same registered-rule selection, grouped membership, explicit economic path and business trace. Permute a deliberately ordered event list without changing its declared sequence authority: reject inconsistency or observe changed economics, never silently canonicalize it by fact ID. |
| LIMIT-01 | Exceed join-pair, event or observation bounds: RESOURCE_LIMIT and no truncated final settlement/state; test exactly at and above each pinned boundary. |

Before implementing a surface shorthand, freeze its operator types, diagnostic
precedence, expansion identity and trace obligations in a small feature fixture.
The pure Lean targets should expose Result/Except-style executable checks and
structurally finite traversals. Later correctness statements must cover values,
errors, scope/state and the chosen semantic observations explicitly; no existing
scalar theorem should be relabeled as proof of these proposed capabilities.
