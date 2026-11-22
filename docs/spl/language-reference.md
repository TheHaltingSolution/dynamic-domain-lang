# Screen Participation Language reference

Version: `spl/0.1-draft`. Status: initial design proposal, 15 November 2026.

Readable authoring addition, 20 November: [spl-readable/0.1-dev](readable-language.md)
provides controlled English-like definitions, percentages, matched funding
branches, closing clauses and reports. Its explicit supporting bindings expand
to the grammar below and the same validated typed IR. The original grammar
remains supported; arbitrary legal prose is not interpreted at execution.

Research reconciliation addendum: 20 November 2026. The Lionsgate case below now
requires separate outside-hurdle and work-level gate evidence and distinguishes
basis-stage video-return reserves from a synthetic payment holdback. This is a
revision of the unfrozen draft, not a new compatibility or approval claim.

Follow-up reconciliation, 20 November 2026: LG-01 now requires hurdle attainment
strictly before the period start. The former `<=` guard conflicted with that
prose and has been changed to `<` as a conservative synthetic fixture policy.
Attainment on the first date is outside this seed, not a resolved historical
ordering rule. This changes the draft bytes and requires a new digest for review.

SPL describes a participation calculation in contract order: applicable money,
named bases, entitlement, settlement and carried balances. Its phrases have a
closed grammar. The compiler does not interpret arbitrary legal prose or decide
what an ambiguous agreement means. A reviewed interpretation supplies that
meaning, and every material definition links to it. This draft is intended to
change alongside the compiler. Both complete schedules below now parse, check
and execute through the bounded native Lean implementation; see
[implementation.md](implementation.md) for current profiles and remaining limits.
Neither constitutes historical statement reproduction.

Read the [package index](README.md), typed core and data/run contract alongside
this reference. The external `Language_Design_Requirements.md`, especially R-01
to R-10, and `Compiled_Language_Testing_Guide.md` supply the requirements and
independent numeric expectations. **Must** below defines proposed conformance;
it does not imply the design or a case policy has already been approved.

## Authored schedules

A schedule consists of immutable definitions, declared inputs, opening state,
assertions and structured outputs. Lexical order presents the contract. Names
form an acyclic dependency graph; forward references in the same lexical scope
are permitted. A compiler may reorder independent computations but cannot move
rounding, consume a balance twice, change a lazy branch, change an economic
fold's order or lose contract order in the explanation.

`input` binds a value supplied by the run manifest and checked against its schema
type. It is not a file path. `opening` resolves an exact state key in the supplied
snapshot. `closing` creates candidate next state without overwriting the opening
value. `emit` names a structured observation; the wrapper formats it and resolves
its standardized statement/detail role. No declaration performs I/O.
An opening-key string is a schedule-declared alias for the complete typed
economic StateCell key, not an alternative storage key. Each alias must resolve
uniquely to the bound agreement, participant, pool, purpose, currency and boundary.
Each opening binding has exactly one closing output port, including unchanged
carry. That port may reuse its opening name and is not a new lexical binding;
the right-hand side always reads the opening value. Other duplicate names remain
errors.

Economic outputs require an agreement, participant, title/pool, period and
currency scope. A compiler must reject unresolved output scope and must not
invent attribution of a pooled amount to titles. Case record types below are
typed projections of canonical data, with source/evidence lineage retained;
they are not a competing interchange schema.

## Lexical rules and grammar

Source is UTF-8. Keywords and identifiers are case-sensitive. Identifiers use
ASCII letters or `_` followed by letters, digits or `_`. Strings use JSON
escaping. Whitespace and `//` comments are insignificant outside strings.
Statements end with semicolons and braces bound blocks. There is no indentation
syntax or implicit conversion of text to a date, amount or typed identifier.

In the EBNF, `*` means repetition, `?` optional, and `|` alternatives. Lexical
categories include `identifier`, `string`, `number` and `currency`. A number is
digits followed by an optional decimal point and more digits; no exponents or
thousands separators. Unary minus is an operator. Currency tokens come from the
pinned schema's finite currency enum. Examples: `USD 100`, `USD 0.05`, `0.20`,
`date "2026-01-01"`. Ratio `0.20` means twenty percent; `20` means twenty.

```ebnf
schedule = "schedule", identifier, "language", string,
           "core", string, "schema", string, "{", declaration*, "}" ;
declaration = input | opening | definition | assertion | closing | emission ;
input = "input", identifier, ":", type, ";" ;
opening = "opening", identifier, ":", type, "from", string, ";" ;
definition = "define", identifier, [":", type], "=", expression,
             ["citing", string], ";" ;
assertion = "require", expression, "else", string, ";" ;
closing = "closing", identifier, "=", expression, ";" ;
emission = "emit", string, "=", expression, ";" ;
type = identifier, ["<", type, {",", type}, ">"] ;
expression = conditional | selection | comprehension | disjunction ;
conditional = "if", expression, "then", expression, "else", expression ;
selection = "choose", "unique", "{", arm+, [otherwise], "}" ;
arm = "when", expression, "=>", expression, ";" ;
otherwise = "otherwise", "=>", expression, ";" ;
comprehension = "for", "each", identifier, "in", expression, "{",
                (definition | assertion)*, "yield", expression, ";", "}" ;
disjunction = conjunction, {"or", conjunction} ;
conjunction = equality, {"and", equality} ;
equality = comparison, [("==" | "!="), comparison] ;
comparison = addition, [("<" | "<=" | ">" | ">="), addition] ;
addition = product, {("+" | "-"), product} ;
product = unary, {("*" | "/"), unary} ;
unary = ["-" | "not"], postfix ;
postfix = atom, {".", identifier | "(", [arguments], ")"} ;
arguments = argument, {",", argument} ;
argument = expression | identifier, "=>", expression ;
atom = identifier | number | string | "true" | "false"
     | currency, number | "date", string
     | "(", expression, ")" | "[", [expression, {",", expression}], "]"
     | "{", [field, {",", field}], "}" ;
field = identifier, ":", expression ;
```

Numeric tokens are checked against an expected numeric type; an unconstrained
decimal defaults to Ratio and a whole-number token to Int. Context can constrain
numeric inference: in `share >= 0` and a Ratio-valued
conditional's `else 1`, context checks 0 and 1 as Ratio. Namespaced header labels
`spl/0.1-draft`, `spl-core/0.1-draft` and `spl-data/0.1-draft` identify the surface,
core and schema profiles respectively; each maps to its manifest version field
value `0.1-draft`. The compiler must check these mappings, not compare the
namespaced labels verbatim to a bare version.
Record field order has no calculation meaning; duplicate fields are errors. Lists preserve order.
Conditional, selection and comprehension expressions must be parenthesized when
used as operands. Calls are restricted to the published pure built-in catalog;
no embedded Lean, network calls, external function loading or unrestricted
recursion. One-variable lambda arguments cannot escape their built-in call.
The examples below are complete draft surface schedules under their declared
case-view types, rather than executable examples in the existing toy compiler.

## Types and arithmetic

| Type | Proposed rule |
| --- | --- |
| `Bool`, `Int`, `Nat` | Boolean and unbounded signed/nonnegative integers; no machine overflow semantics. |
| `Ratio` | Exact rational; decimal literals denote exact fractions. Share ranges require explicit validation. |
| `Money<USD>` | Exact rational with currency tag; fractional cents exist until explicit rounding. This slice supports USD only. |
| `Date`, `Period` | Gregorian local date and half-open `[start,end)` interval with start before end. |
| `Id<K>`, enums | Opaque identifiers qualified by schema kind; finite versioned codes. |
| `Option<T>` | Present or absent, never implicitly zero, empty text or false. |
| `List<T>`, `Map<K,V>` | Finite ordered lists and finite single-valued maps with unique typed keys; tuple keys support multiple indices. |
| Named record | Immutable schema-declared fields. Record literals are checked against a boundary's expected type. |

Addition/subtraction require compatible units and currency. Money times Ratio
produces Money; same-currency Money divided by Money produces Ratio with a
nonzero denominator. Money times Money is ill-typed. Comparison requires
compatible types. There is no financial binary floating-point type. Timestamp
conversion to Date happens in the adapter under a named timezone policy.

`quantize(value, quantum, "half_away_from_zero")` rounds to a positive Money
quantum of the same currency; exact ties move away from zero, including negative
amounts. The catalog also accepts `half_even`, `toward_zero`, `floor` and
`ceiling` with the core's definitions. Unsupported mode strings are compile
errors. No automatic rounding
occurs per item, after multiplication, in a sum, in serialized state or in
reporting. The schedule must declare each amount-affecting rounding point.
Reports retain exact amounts alongside labeled display conversions.

Two receipts of USD 0.05 at Ratio 0.10 yield USD 0.01 when shares are summed
before cent rounding, or USD 0.02 when each share is rounded first. These are
different schedules, not equivalent compiler optimizations. Allocations need an
explicit residual policy. Closing state preserves exact rational precision
unless the state definition explicitly quantizes it.

## Names scope and rule selection

Duplicate names in one lexical scope, unresolved names and dependency cycles
are compile errors. A `for each` body has its own scope; its iterator and local
definitions escape only through the yielded value. Shadowing visible bindings
is rejected in this draft. There is no mutable assignment. Assertions execute
in lexical contract order and demand only definitions on the evaluated path.
Needed forward definitions evaluate before the assertion; an untaken branch
does not force its referenced definitions. An unrelated later definition cannot
preempt an earlier failed assertion. Definition declarations themselves evaluate
when reached; all scope assertions must pass before outputs finalize. Field access is
checked against a record type and a partial map lookup returns Option.

A selected list of titles does not itself authorize crossing their balances.
Cross-title aggregation must reference an effective membership and declared
purpose such as participant prepayment. The compiler checks structural scope;
input validation checks effective membership and authority. Lexical nesting
alone does not prove contractual authorization.

`choose unique` evaluates its predicates and requires exactly one true arm.
If none match it evaluates `otherwise`, or fails with `NO_APPLICABLE_RULE` if
there is no fallback. Multiple matches fail with `AMBIGUOUS_RULE`, even when
their amounts agree. `otherwise` is not a true predicate arm. Only the selected
result expression evaluates. Predicate errors are not hidden by the fallback.
`if` also evaluates only its selected result branch.

For typed rule tables, `select_priority(rules, context)` chooses the single
greatest integer priority among applicable effective rules. An equal greatest
priority or missing match is an error unless the missing-match case has an
explicit default. A default is a fallback evaluated only when no ordinary rule matches; it is not an ordinary
candidate competing by priority. File order, narrower scope, later amendment or identifier sorting never
creates precedence. The selected rule carries matched/rejected provenance.

`citing` references a versioned interpretation decision containing clause,
document version, evidence class, effective scope/dates, policy, alternatives
and review status. It is not a declaration that the language author has approved
the policy. Missing material policy blocks finalization. A complete named research
scenario may select a stated assumption and finalize a synthetic reconstruction
within its own policy/state lineage. That does not establish actual settlement
approval. Unresolved alternatives remain blocked; compilation does not approve
an assumption.

## Collections settlement and observations

| Operation | Behavior |
| --- | --- |
| `filter(xs, x => predicate)` | Preserve selected order and lineage; accounting exclusions retain their own disposition. |
| `map(xs, x => value)` | One value per input in order. `for each` lowers to map with local definitions and assertions. |
| `sum(xs, x => amount)` | Exact sum; empty means zero of the expected numeric type. Reject an ambiguous empty sum. |
| `lookup(map, key)` | Return Option; missing differs from a present zero. |
| `require_some(option, code)` | Extract present value or emit a typed diagnostic with the source reference. |
| `sort_by(xs, x => key)` | Canonical ordering by explicit total typed key; economic folds require a unique tie key. |
| `min`, `max` | Compare compatible numbers; they do not imply nonnegative values or explain a contractual tie. |
| `in_period(date, period)` | start <= date and date < end; missing dates must be resolved first. |
| `is_calendar_quarter(period)` | Gregorian first-day quarter interval, end exclusive; Q4 ends January 1 of the next year. Fiscal/business calendars are not inferred. |
| `quantize` | Explicit positive quantum and tie mode as above. |

Finite ordered folds are a core capability. A case-specific pure step catalog
may expose them to the surface only with published expansion and semantics.
This grammar defers a general multi-argument function/step syntax. Join, grouping,
allocation and reserve convenience functions similarly require documented typed
library definitions over core primitives. An implementation must reject any
unpublished function rather than guessing its financial meaning.

Recovery is explicit arithmetic: applied = min(eligible, available), remaining =
available - applied. Preconditions establish nonnegative inputs. Negative earned
participation is not silently floored. A priority waterfall uses an ordered fold
with named claims and carry rules; sorting report lines cannot implement it.
A reserve has its own scope, purpose and possibly vintage. With positive
movement magnitudes: closing = opening + additions - releases - applications.
Where a release affects earnings or payable is a separate schedule choice.
Its stage is mandatory: a reserve adjusting a named receipt/cost measure cannot
be substituted with a deduction from earned participation or payable. A release
reverses its original stage under the selected policy; it is not automatically
cash paid. Linked actual returns and reserve applications must affect each
economic measure once, with state movement and cash payment kept distinct.
Advances, reserves, accrual meters and actual cash paid are distinct economic
kinds. Payment facts are neither transfer instructions nor proof of settlement.

Before arithmetic, validate schema, references, corrections, mappings, policy,
state lineage and version compatibility. Assertions then check case-specific
preconditions. Unknown/rejected rows stay in diagnostics and control totals.
Empty facts plus supplied state represent no activity; missing deliveries do not.
The finalization unit includes any shared pool. A material unresolved input
blocks that scope. Default execution is strict. Preview may expose only proven
independent components sharing no pool, gate, state or aggregate with the blocked
component. Such provisional results are not final payable and cannot become
authoritative next-period state. A reduced-scope hypothetical is a separate
scenario, not an unaffected subtotal of the original blocked pool.

Every definition/assertion has a semantic identity from schedule identity,
declaration/source span, instance key and scope. Traces record exact operands,
source IDs, policy IDs, selected/rejected branches and resulting values. Dead
branches record non-evaluation without invented values. A greater-of exposes
both evaluated candidates; equal amounts record a tie. Input dispositions
are `rejected`, `unmapped`, `excluded` and `included`; outcomes are `calculated`,
`calculated_zero`, `blocked` and `provisional`. A policy exclusion is `excluded`
with a rule reason. An eligible zero is `included` with outcome `calculated_zero`.
A fact can feed different named views but cannot be deducted twice
within one basis/purpose without a separately authorized economic entitlement.
Reconciliation must inspect contribution paths, not just matching totals.

## Development schedule one Skouras Ventura

SV-01 is a synthetic reconstruction of selected sections 7 to 9. It assumes
reviewed-in-fixture eligible-cost subtotals, nonnegative earnings, one currency
and a supplied remaining opening participation-prepayment pool. Reviewer-checked
fixture arithmetic is not approval of a historical opening balance or deduction.
Incorporated expense definitions, historical backward
crossing, negative balances, surcharge and interest are outside this slice.

Case-view fields: SVPicture has asset_id, contribution_present and funding_share;
SVReceipt has fact_id, asset_id, amount and cash_received_date; SVCost has fact_id,
asset_id, amount, incurred_date and eligibility_decision_id. SVPolicy supplies
agreement_id, participant_id, pool_id and period. All views retain canonical
provenance. Picture members must be effective authorized pool members; eligible
cost decisions must cite the appropriate contribution-dependent deduction
schedule and exclude participation prepayments. Adapter normalization does not
authorize deductions. The fixture's incurred-date cost assignment is a research
policy, not a claim that every contractual cost is recognized on that date.

```spl
schedule SkourasVenturaPilot language "spl/0.1-draft"
  core "spl-core/0.1-draft" schema "spl-data/0.1-draft" {
  input pictures: List<SVPicture>;
  input receipts: List<SVReceipt>;
  input eligible_costs: List<SVCost>;
  input policy: SVPolicy;
  opening prepayment: Money<USD> from "sv/participant-prepayment/main-pool";
  require prepayment >= USD 0 else "NEGATIVE_OPENING_ADVANCE";
  define title_results = for each picture in pictures {
    require picture.funding_share >= 0 and picture.funding_share <= 1
      else "INVALID_FUNDING_SHARE";
    define cash_rows = filter(receipts, r =>
      r.asset_id == picture.asset_id and in_period(r.cash_received_date, policy.period));
    define cost_rows = filter(eligible_costs, c =>
      c.asset_id == picture.asset_id and in_period(c.incurred_date, policy.period));
    define cash = sum(cash_rows, r => r.amount) citing "SV-8-CASH";
    define allowed_cost = sum(cost_rows, c => c.amount) citing "SV-8-COST-SCHEDULE";
    define fee_rate = choose unique {
      when picture.contribution_present => 0.075;
      otherwise => 0.25;
    } citing "SV-8-FEE";
    define fee = cash * fee_rate;
    define basis = cash - fee - allowed_cost citing "SV-8-BASIS";
    define share = if picture.contribution_present
      then picture.funding_share else 0.20 citing "SV-8-SHARE";
    define earned = basis * share;
    require earned >= USD 0 else "SV_NEGATIVE_EARNINGS_OUTSIDE_PILOT";
    yield { asset_id: picture.asset_id, cash: cash, fee: fee,
      allowed_cost: allowed_cost, basis: basis, share: share, earned: earned };
  };
  define earned_total = sum(title_results, t => t.earned);
  define recouped = min(earned_total, prepayment) citing "SV-7-POOL-RECOVERY";
  define payable = earned_total - recouped;
  closing prepayment = prepayment - recouped;
  require earned_total == recouped + payable else "SV_SETTLEMENT_RECONCILIATION";
  emit "titles" = title_results;
  emit "pool" = { agreement_id: policy.agreement_id,
    participant_id: policy.participant_id, pool_id: policy.pool_id,
    period: policy.period, earned: earned_total, recouped: recouped, payable: payable };
}
```

Contribution status must agree with approved evidence. A missing contribution
cannot become a zero share by default. The supplied 40% share must arise from
qualifying SFI funds divided by combined qualifying SFI and Ventura funds for
that same Picture, with a nonzero denominator and a selected funding valuation
date. Record documented zero SFI funding separately from missing evidence.
The research response supports the distinction between a title acquisition or
licensor advance in an eligible expense schedule and a section 7 participation
prepayment recovered from earned participation. Never classify one as the other
merely because both are called advances. If the agreement
requires computing that proportion rather than accepting an authoritative
allocation, move the exact division into a named definition. For this fixture
the research handoff supplies a validated share.

| Picture | Cash | Fee | Allowed cost | Basis | Share | Earned |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| A without contribution | 100,000 | 25,000 | 10,000 | 65,000 | 0.20 | 13,000 |
| B with contribution | 60,000 | 4,500 | 5,500 | 50,000 | 0.40 | 20,000 |

Pool earned is 33,000; opening prepayment 15,000; recovered 15,000; payable
18,000; closing prepayment zero. There is no asserted title allocation of that
pool offset. With zero opening prepayment, payable is 33,000. With opening
40,000, closing is 7,000; a second period with earned 5,000 carries 2,000; a
third with earned 10,000 yields payable 8,000 and closing zero. Those periods
need separate facts and linked closing/opening snapshots. All pilot arithmetic
is exact dollars; a cent-settled extension must insert a reviewed rounding rule.

## Development schedule two Lionsgate derivative works

LG-01 is a selected-provision capability fixture for section 2.4(a)(ii), not a
complete end-to-end interpretation. Rates and offset are synthetic redaction
substitutes. Breakeven uses full eligible home-video cash while payout uses a
25% proxy; these must remain separate definitions over the same facts. The seed
has one eligible purchaser-produced derivative work and aggregate seller-group
participation before any seller-specific allocation. Opening work-level state is
exactly at breakeven. That endpoint does not establish when the gate first opened
or whether it dipped below and recovered during the period.

There are two separate prerequisites. The broader post-Closing Contingent
Participation Hurdle is a case-level prerequisite under sections 2.3(c), 2.4(a)
and 2.4(d); True-Cash Breakeven is specific to this derivative work. LG-01
supplies an explicit synthetic attestation that the broader hurdle was attained
before the period, rather than computing it from this work's gate. The broader
hurdle involves eligible 3(a), 3(b) and derivative participation compared with
Base Consideration, Cost of Funds and specified insurance tail cost. The strict
exceeds and excess-only payment wording for 3(a)/3(b) must not be imported as
this work's equality rule or a deduction from its producer-fee amount. Any
pre-attainment derivative contribution or same-event attainment ordering remains
an unresolved interpretation, outside this already-attained seed.

LGReceipt includes asset_id, amount, cash_received_date and is_home_video plus
canonical source identity and scope. Its cash-only date is a fixture restriction:
the sourced definition also permits qualifying amounts credited in lieu of
payment and recognition when earned or nonrefundable. Those distinct dates must
be represented before extending the seed to credited or refundable events.
LGCost includes asset_id, amount and incurred_date plus cost eligibility evidence.
Its view must include only qualifying actual third-party out-of-pocket costs,
with eligible affiliate allocation and the selected discounts, rebates,
recoveries and Soft-Money adjustments. Overhead, supervisory and distribution
fees do not enter this work's True-Cash measure. Do not count the same benefit
both as increased receipts and reduced costs. These classification requirements
do not supply missing historical amounts or resolve reserve recognition.
LGPolicy includes agreement_id, participant_id, asset_id, pool_id,
period, video_proxy, gross_rate and net_rate; all rates are nonnegative and the
fixture pins them to 0.25, 0.20 and 0.20 respectively. Membership is a validated
eligible crossed-title pool for the net branch only; `pool_id` does not widen
this work's gate or gross branch. Gate state and gross receipts/costs bind the
single `asset_id`. The supplied net subtotal identifies its separate group,
members, fiscal-date selectors and supporting reconciliation. Standalone Net
Profits, 3(b) Amounts, fiscal groups and companion overhead allocation are not
interchangeable. A classification flag must come from a versioned mapping:
qualifying physical video and electronic sell-through/download-to-own can be
Home Video Rights, while VOD and near-VOD are separate classifications.

`LGHurdleAttestation` has agreement_id, attained: Bool and effective_date: Date.
It also carries attestation/source identity, observed/recorded date, review
status, interpretation and scenario reference in its canonical evidence link.
Validation confirms the selected post-Closing pathway and evidence coverage.
It is an explicit supplied case assumption, not a calculation or proof of the
broader hurdle. The synthetic LG-01 policy requires
`effective_date < policy.period.start`: an equal or later date blocks this seed
with `LG_HURDLE_TIMING_POLICY_REQUIRED`. A date-only attestation on the first day
does not establish prior attainment. Encoding same-boundary or same-event
ordering requires a separately selected policy and scenario.
`LGGateHistoryAttestation` has asset_id, period: Period and
cleared_throughout: Bool with the same evidence metadata. A true value declares
that the gate remains cleared over the complete interval under the selected
policy. Missing, false, wrong-scope or wrong-period evidence blocks this seed;
it does not select a speculative alternative. A history ledger could replace
the attestation only with an approved event-order and reopening/latch policy.

The reviewed crossed_net_subtotal is an intermediate worksheet input with its
own supporting rows and decision references, never a cash receipt or unexplained
override. Expanding that worksheet into SPL remains necessary before claiming
receipt-to-net coverage. The chosen fixed producer-fee offset convention is a
research assumption; its repeat application across periods is not approved.
The gross branch's zero floor is also an explicit research policy, immaterial
to LG-01's positive candidate but requiring separate review before a negative
gross-minus-offset case can claim contract coverage.

```spl
schedule LionsgateDerivativePilot language "spl/0.1-draft"
  core "spl-core/0.1-draft" schema "spl-data/0.1-draft" {
  input receipts: List<LGReceipt>;
  input actual_costs: List<LGCost>;
  input policy: LGPolicy;
  input outside_hurdle: LGHurdleAttestation;
  input work_gate_history: LGGateHistoryAttestation;
  input crossed_net_subtotal: Money<USD>;
  input producer_fee_offset: Money<USD>;
  input payment_holdback_addition: Money<USD>;
  input payment_holdback_release: Money<USD>;
  opening gate_gross: Money<USD> from "lg/work-D/true-cash/cumulative-gross";
  opening gate_cost: Money<USD> from "lg/work-D/true-cash/cumulative-cost";
  opening payment_holdback: Money<USD> from "synthetic/work-D/payment-holdback";
  require outside_hurdle.agreement_id == policy.agreement_id
    else "LG_HURDLE_WRONG_SCOPE";
  define outside_hurdle_attained = outside_hurdle.attained citing "LG-OUTSIDE-HURDLE";
  require outside_hurdle_attained else "LG_OUTSIDE_HURDLE_NOT_ATTAINED";
  require outside_hurdle.effective_date < policy.period.start
    else "LG_HURDLE_TIMING_POLICY_REQUIRED";
  require work_gate_history.asset_id == policy.asset_id
    else "LG_GATE_HISTORY_WRONG_WORK";
  require work_gate_history.period.start == policy.period.start and
    work_gate_history.period.end == policy.period.end else "LG_GATE_HISTORY_WRONG_PERIOD";
  define work_cleared_throughout = work_gate_history.cleared_throughout
    citing "LG-GATE-HISTORY";
  require work_cleared_throughout else "LG_GATE_HISTORY_POLICY_REQUIRED";
  require gate_gross >= gate_cost else "LG_CROSSING_POLICY_REQUIRED";
  require producer_fee_offset >= USD 0 else "LG_NEGATIVE_FEE_OFFSET";
  require crossed_net_subtotal >= USD 0 else "LG_NET_LOSS_POLICY_REQUIRED";
  require payment_holdback >= USD 0 and payment_holdback_addition >= USD 0 and
    payment_holdback_release >= USD 0 else "SYNTHETIC_INVALID_HOLDBACK_MOVEMENT";
  define current_receipts = filter(receipts, r => r.asset_id == policy.asset_id and
    in_period(r.cash_received_date, policy.period));
  define current_costs = filter(actual_costs, c => c.asset_id == policy.asset_id and
    in_period(c.incurred_date, policy.period));
  define cash_measure = sum(current_receipts, r => r.amount) citing "LG-TRUE-CASH";
  define actual_cost_measure = sum(current_costs, c => c.amount) citing "LG-TRUE-CASH-COST";
  define next_gate_gross = gate_gross + cash_measure;
  define next_gate_cost = gate_cost + actual_cost_measure;
  require next_gate_gross >= next_gate_cost else "LG_RECROSSING_POLICY_REQUIRED";
  define breakeven_satisfied = next_gate_gross >= next_gate_cost;
  define payout_base = sum(current_receipts, r =>
    r.amount * (if r.is_home_video then policy.video_proxy else 1))
    citing "LG-GROSS-VIDEO-PROXY";
  define gross_candidate = if breakeven_satisfied
    then max(USD 0, payout_base * policy.gross_rate - producer_fee_offset)
    else USD 0 citing "LG-GROSS-BRANCH";
  define net_candidate = crossed_net_subtotal * policy.net_rate citing "LG-NET-BRANCH";
  define contingent_earned = max(gross_candidate, net_candidate) citing "LG-GREATER-OF";
  define selected_label = if gross_candidate == net_candidate then "tie"
    else (if gross_candidate > net_candidate then "gross" else "net");
  define before_holdback = contingent_earned + payment_holdback_release;
  require payment_holdback_release <= payment_holdback
    else "SYNTHETIC_HOLDBACK_RELEASE_EXCEEDS_OPENING";
  require payment_holdback_addition <= before_holdback
    else "SYNTHETIC_HOLDBACK_ADDITION_EXCEEDS_AVAILABLE";
  define payable = before_holdback - payment_holdback_addition
    citing "SYNTHETIC-PAYMENT-HOLDBACK";
  closing gate_gross = next_gate_gross;
  closing gate_cost = next_gate_cost;
  closing payment_holdback = payment_holdback + payment_holdback_addition - payment_holdback_release;
  emit "comparison" = { cash_measure: cash_measure, payout_base: payout_base,
    gross_candidate: gross_candidate, net_candidate: net_candidate,
    selected_label: selected_label, earned: contingent_earned,
    outside_hurdle: outside_hurdle, work_gate_history: work_gate_history };
  emit "settlement" = { agreement_id: policy.agreement_id,
    participant_id: policy.participant_id, asset_id: policy.asset_id, net_pool_id: policy.pool_id,
    period: policy.period, earned: contingent_earned,
    payment_holdback_addition: payment_holdback_addition,
    payment_holdback_release: payment_holdback_release, payable: payable };
}
```

The endpoint guards reject below-breakeven opening/closing values. They cannot
detect an intra-period dip followed by recovery. For example, opening 100/100,
then cost 20, then receipt 30 closes 130/120 while dipping to 100/120 in between.
The separate throughout-period attestation bounds this seed; endpoints must not
be used to manufacture it. Its selected policy and evidence are traced separately
from both gate totals. A false gate can be represented lazily, but dynamically
crossing/reopening cases need approved chronology and branch applicability:
inapplicable gross is distinct from applicable calculated zero and blocked input.
The net branch remains independently observable when applicable under the outside
hurdle and its selected interpretation. An unopened work gate must not silently
erase a valid net candidate.

| LG-01 observation in USD | Expected value |
| --- | ---: |
| Outside Contingent Participation Hurdle | Explicit scenario attestation of prior attainment |
| Work-level gate during period | Explicit scenario attestation of remaining cleared |
| Opening cumulative cash / cost | 100 / 100 |
| Current non-video / home-video receipts | 180 / 120 |
| Current actual cost | 0 |
| Closing cumulative gate gross / cost | 400 / 100 |
| Payout base | 180 + 120 times 0.25 = 210 |
| Gross candidate with offset 12 | 210 times 0.20 minus 12 = 30 |
| Net candidate with reviewed subtotal 175 | 175 times 0.20 = 35 |
| Earned / payable with no basis reserve or synthetic holdback movements | 35 / 35 |

Changing only net subtotal to 100 yields net candidate 20 and earned 30.
Subtotal 150 yields two 30 candidates and label `tie`. With synthetic opening
payment holdback 5, addition 4 and release 2, the 35-earned fixture yields payable
33 and closing holdback 7. This optional post-earnings mechanism is not the
agreement's video-return reserve; its state purpose, case ID and decision remain
synthetic. Set all holdback inputs/state to zero for bounded LG-01. A historical
case cannot enable the optional mechanism merely by citing section 2.4(a)(ii).

### Sourced reserve stage and separate synthetic comparisons

The research response supports a distributor-conditioned reasonable Home Video
Rights return reserve in the named True-Cash Breakeven, DW Gross Receipts and
retained-rights measures, with a redacted cap and liquidation within twelve
months. The retained-rights pathway is outside this seed. This is evidence of a
basis/measure-stage effect, not a general authorization to withhold the same
amount from contingent earnings or cash payable. The separate 3(b) Amounts
reserve must not be inherited into the supplied net subtotal without resolving
its grouping and standalone Net Profits interaction.

The actual cap amount/unit/base, vintage age origin, interim release evidence,
application matching, order and exact recognition remain unapproved. A basis-stage
extension must declare the affected measures separately, distributor/rights/work
scope, formation and effective dates, vintage, deadline, linked return facts and
movement provenance. Avoid counting a return once as an actual base adjustment
and again when applying its reserve. An unused reserve release reverses its
chosen basis effect and changes a gate or candidate only through that measure;
it does not imply that cash was transferred.

Use a separate synthetic cleared-gate scenario with ordinary receipts 100,
home-video revenue 100, proxy 0.50, gross rate 0.20, offset zero and nonbinding
net candidate. A reserve addition of 20 before the proxy gives payout base
`100 + (100 - 20) * 0.50 = 140` and gross candidate 28. A payment holdback of 20
instead leaves earned 30 and payable 10. The research scenario chooses the first
transformation for a basis-stage demonstration; the public text does not fix
that exact transform. In an isolated release comparison, releasing 12 contributes
1.20 to the gross candidate under this pre-proxy choice, while the payment-stage
alternative releases 12 of prior payable with current earnings unchanged.

An independent vintage example reconciles opening 12 + additions 20 - actual
return applications 7 - unused releases 5 = closing 20; next period 20 - 8 - 12
= zero. A synthetic cap 30 is respected if the old vintage's application/release
precedes new booking; reverse ordering momentarily reaches 32. Quarter-end totals
cannot establish event-time compliance. The hypothetical cap, booking-date age
origin and event order are research assumptions; the twelve-month maximum comes
from the clause. Keep this example separate from LG-01's zero reserve activity.

## Clause and requirement map

| Example decisions | Provision and bounded policy | Gap |
| --- | --- | --- |
| SV-8-CASH/FEE/BASIS/SHARE | Section 8 cash basis and contribution-dependent method | Incorporated definitions, losses and contribution history. |
| SV-8-COST-SCHEDULE | Separate eligible expense views per method | Interest, surcharge, common-cost allocation and full eligibility. |
| SV-7-POOL-RECOVERY | Section 7(a) forward prepayment recovery from nonnegative earnings | Backward crossing, advance timing and other offset priority. |
| LG-OUTSIDE-HURDLE | Sections 2.3(c), 2.4(a), 2.4(d); separate aggregate prerequisite supplied as attestation | Historical attainment inputs/date, pre-attainment contribution and same-event ordering. |
| LG-GATE-HISTORY | Scenario attestation of work-level gate cleared throughout the period | Endpoint totals do not establish absence of dips; opening/crossing/reopening policy remains unresolved. |
| LG-TRUE-CASH/COST | Section 2.4(a)(ii) per-work full eligible home-video breakeven ledger | Receipt/credit recognition, actual third-party cost/affiliate adjustments, reserve treatment and subsequent losses. |
| LG-GROSS-VIDEO-PROXY/BRANCH | Distinct payout basis | Synthetic redacted values and proposed offset convention. |
| LG-NET-BRANCH/GREATER-OF | Compared reviewed crossed net worksheet subtotal | Full net-profit calculation not encoded here. |
| SYNTHETIC-PAYMENT-HOLDBACK | Optional illustrative post-earnings hold/release state | No sourced authority for this stage in the selected reserve sentence. |
| LG-BASIS-RESERVE | Section 2.4(a)(ii) named measures, distributor condition and twelve-month maximum | Actual redacted cap, vintage origin, matching, release and recognition; no basis-reserve schedule implemented here. |

| Requirement | Surface feature |
| --- | --- |
| R-01 | Named definitions, citations, lexical contract order. |
| R-02 | Version header, typed input bindings, explicit opening keys. |
| R-03 | Validation/assertions, absent/zero distinction, fact dispositions. |
| R-04 | Scope, membership, unique/priority selection, pool output. |
| R-05 | Exact arithmetic, half-open dates, explicit quantization. |
| R-06 | SV conditional method; LG separate gate/payout and greater-of. |
| R-07 | Opening/closing balances, reserve movements, explicit correction facts. |
| R-08 | Pure computation, pinned versions, deterministic ordering. |
| R-09 | Structured emissions, trace, reconciliation, scope-level finalization. |
| R-10 | Closed grammar lowering to independently specified typed core. |

## Evolution and implementation boundaries

Implement the SV arithmetic/output slice first, then the LG selected provision,
with independent expected intermediates. New syntax needs a positive parser
example, negative case, typing/lowering rules and an observable semantic case.
A convenient domain phrase must expand to published core operations; otherwise
it adds a capability needing its own semantics.

Freeze surface, core, schema, policy and fixtures separately before a held-out
exercise. A rate/date edit is a parameter change; a new operator composition is
a method; an equivalent phrase is a surface extension; a new semantic operator
is a core extension. Related Lionsgate exhibits stay in one research family.

Before approval, obtain contract-reader and participation-accountant review,
settle case gaps, validate case-view projections against canonical records, and
compare the independent oracle, core evaluator and generated Lean path. The
current repository's toy compiler and theorem do not validate these schedules.

## Research reconciliation and remaining handoff

The 20 November revision uses the supplied `SPL_Research_Responses.md` (including
its 19 November verification) and `SPL_RQ03_RQ04_Lionsgate_Research.md`, especially
the separate prerequisite, three formula sheets and reserve-stage analysis.
Their source anchors are Exhibit 10.43 sections 1.1, 2.3(c), 2.4(a)(ii), 2.4(d)
and 9.11, plus the separate executed overhead letter Exhibit 10.45 section 1(b).
The research agent checked those filings; this revision does not claim a fresh
source verification. Reviewer-checked arithmetic and research readings do not
constitute approved historical interpretations. No held-out provision was used
to extend this surface draft.

The next case handoff must supply actual or explicitly synthetic hurdle
attestation, work and net-group identities, throughout-period gate evidence,
support for the crossed-net subtotal and selected fee-offset convention. A
dynamic-gate or sourced-reserve implementation additionally needs approved
event ordering, recognition and stage rules. Missing evidence must block that
claimed scope or keep it a named synthetic scenario, not become a hidden default.
These changes use existing records, assertions, lazy branches and exact
arithmetic; they do not yet justify a new core primitive or grammar feature.
