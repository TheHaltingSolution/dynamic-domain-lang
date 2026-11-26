# Independent original-history gate controls

The new [neutral fixture](../../cases/ordered-gates/neutral.json) and
[selected policy](../../cases/ordered-gates/policy.md) address
`B-C11-GATES`, the finite sourced alternative under `B-C11-SOURCED`, and atomic
variants `C11.OPENING_GATE`, `C11.CLOSING_GATE`,
`C11.CONTINUOUS_ORIGINAL_HISTORY` and `C11.SPLIT_REOPEN_GATE`.
`C11.ATTESTED_FULL_GATE_PROXY_PAYOUT` remains the existing cleared LG-01 method.
Neither its code nor its oracle is changed. A different author will implement
SPL and canonical/native comparison after these original-fact controls freeze.

The source/reviewer basis is the official September 10, 2007 agreement
Exhibit10.43 §1.1 and §2.4(a)(ii), RR04 §4 (lines62–77) and LD03 §6
(lines265–313). Exact source/reviewer/catalog bytes are SHA-pinned in the
fixture and archived externally for verification. The agreement supplies the
rolling work-level economics and distinction from the payout proxy; the
crossing/order/latch/reopen conventions, synthetic proxy/rates, complete history,
aggregate attestation and zero crossed worksheet are explicitly proposed.
There is no historical account reproduction or professional approval claim.

The independent API is `oracles.ordered_gates.ordered_gates(data)`,
`policy(method)` and `exact_json(result)`. Errors raise
`OrderedGateOracleError` before any result/state is returned. Inputs are not
mutated. Imports are Python standard library `copy`, `datetime`, `fractions`
and `re`; no compiler, parser, binding projection, other financial oracle or
executable SPL is read. Money and Instants are exact fractions, serialized as
integer/rational strings. Original Text identities, Unicode lexemes and source
records are preserved without normalization, trimming or case folding. This
does not claim that every outer canonical Text interface admits every such
lexeme, or change declared `Id<Kind>` admission.

Schema `ordered-gates-neutral/1` has `scope`, `policy`, `research`, `registry`,
`opening_state`, optional `prior_result`, and a current frame:

```text
case_id, period{start,end}, cutoff,
rows[], populations[], evidence[], ordering_authority,
aggregate_hurdle, net_worksheet
```

Registry contains original terms, work-eligibility authority, explicit zero
genesis Date and a separate crossed-net pool identity. Scope identifies
agreement, participant, work gate pool, asset, purpose and USD. Original terms
have effective interval, known observation and source/evidence references;
they must cover every replayed period, not only the latest one. New terms,
classifications, amendments and late historical additions require a separately
selected policy and are unsupported here.

Every row retains original identity/line, scope, source/evidence, observation,
explicit sequence, kind and its separate original classification decision.
Receipts carry original received/credited and earned Instants, amount,
nonrefundable flag and channel. Costs carry original incurred Instant, actual
third-party flag, gross and original reductions. Reduction line identities are
globally consumed with receipt/cost lines, preventing receipt-plus-cost-benefit
double recognition. Classification IDs/lines also remain unique across replay.
Excluded records remain visible and population-controlled. The adapter may
validate record shape and custody but must not supply admitted receipt amounts,
surplus, opening totals, payout candidates, solved event ranks or gate results.
The ordering authority is an original approval of the full economic tie key,
not an adapter-selected order. Source/SPL must derive recognition time and sort
or fold its admitted original ordering while checking authority.

Complete population controls are original approved observations of every row ID
and raw gross amount total for each receipt/cost kind. Selected eligible net
cost/receipt amounts are independently calculated. Original classification and
source populations must not be replaced by bindings projected from an SPL
implementation. Complete-empty is explicit; absent history, populations,
aggregate attestation or applicable net evidence is unknown and blocks.

Three opening forms are explicit. `genesis` has no previous amounts and starts
at the registry's zero boundary. `original_history` supplies original raw
adjacent frames from that genesis, with each frame's own cutoff; it does not
claim actual previously executed outputs. `prior_result` supplies actual
serialized oracle closing state and predecessor summary. Both historical forms
are independently replayed from zero under the immutable registry. State
includes all raw frames/results, opening balances, latch, consumed event and
classification IDs/lines and cumulative recognized entitlement. A supplied
predecessor must match period, case identity and full state. Financial replay
and state reconstruction reject a scalar opening or altered result even if
some final amounts happen to agree.

Material output includes original path and selected amount, exact economic
Instant/key, pre/post receipts/costs/surplus, latch before/after, receipt-specific
applicability/reason, full admitted amount, proxy factor, payout contribution,
current and closing totals, current-history continuity, both candidates and
branch/status. Supplied aggregate and net originals remain visible. The result
is calculated unissued entitlement; absent payment evidence is not numeric
paid0. The method's zero fee/reserve operations and net input are specifically
named rather than omitted silently.

Independent hand values are6/8/7/4/0/11 for RR04 split/reopen, latch, full
cross/reopen, reversed authorized tie, opening and closing methods. Additional
controls separate next-row admission, continuous dip versus endpoints, zero
genesis versus latch, below/equal/above crossing, full versus proxy amounts,
fractional earnings, receipt earned-date recognition, original cost reductions
and exclusions, exact submicrosecond/offset times, duplicate/alias/tie/cutoff/
scope/evidence/population/state failures and malformed shapes.

An actual serialized Q1 cost100/receipt80 run yields80/100 and gross0; its
closing state feeds Q2 and yields150/130 and gross6. That actual result feeds Q3
cost30/receipt20, which yields170/160 and new gross2; cumulative recognized8.
All three cutoffs, source facts and results remain in state. Continuous means
opening and every prefix of the selected CURRENT period, not never dipping
throughout all earlier history. Opening/closing period methods are not asserted
equivalent under arbitrary repartitioning. Counterfactual methods do not add
new required atomic variants without separate selection.

Verification is pure-Python financial control only. Native reference/IR/emitted,
canonical publication, audit decisions, actual payment and professional review
are responsibilities of subsequent independent integration. Finite unit tests
and a frozen source snapshot establish the named controls, not full agreement
coverage or compiler correctness.
