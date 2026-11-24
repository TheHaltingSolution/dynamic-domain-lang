# Scoped rate selection from original facts

`SYNTHETIC-SELECTION-01@1` is a disclosed synthetic research assumption. It
calculates entitlement from a single original USD receipt and separately supplied
approved rate rules. It does not issue an obligation or establish actual payment.

Three separately registered methods are selected explicitly:

| Method | Ordinary winner | No applicable rule |
| --- | --- | --- |
| `unique_no_fallback` | Exactly one applicable rule | Block |
| `unique_explicit_fallback` | Exactly one applicable rule | Explicit fallback |
| `priority_explicit_fallback` | Unique greatest-priority applicable rule | Explicit fallback |

The bounded original rule population has three named slots: primary, competing
and unsafe. These are identified registered rules, not a row-order mechanism.
Each original rule supplies agreement, title, channel, half-open effective period,
enabled status, observation, exact rate, source and authority evidence. A rule
applies only when enabled, its agreement/title/channel match the receipt, its
effective period contains the receipt Date and its observation is before cutoff.
The primary and competing rules have priority 20; unsafe has priority -10.
Every ordinary predicate is demanded by selection, including lower priorities.
Arithmetic failure while determining a predicate blocks; it does not mean false.

All source/evidence identities and authority links are checked first. Evidence
must match the canonical agreement/title, be approved for its identified rule
and precede cutoff. The original receipt must match the canonical scope, lie in
the run period, and be observed before cutoff. The explicit fallback is a scoped
policy term for otherwise unmatched receipts; its own authority is required.
Complete evidence and rate-term validation applies even to disabled rules and
the unused fallback. Scope/authority failure is distinct from an ordinary false
matching predicate. No rule is chosen by the adapter.

Cash 100 with primary rate .2 earns 20. A selected primary rate zero earns zero;
it does not activate fallback .1 to manufacture 10. If all predicates are false,
the no-fallback method blocks and the two explicit-fallback methods earn 10.
Two applicable equal-valued rules are ambiguous under unique selection. A tie
at greatest priority is ambiguous under priority selection. Neither ambiguity
evaluates a body or uses fallback. Lower-priority ties are irrelevant to the
greatest winner, but their predicates are still demanded.

The selected body calculates exact receipt amount times original rate divided
by its supplied body divisor. Normal divisors are one. The synthetic fault
witness sets an unselected body's divisor to zero: it must remain lazy. Setting
the selected body's divisor to zero must block, without trying fallback.
The predicate fault witness similarly uses an explicit predicate divisor zero
on an enabled, otherwise matching rule; it must block before any body. These
declared failure probes are not fee or tax policies.

Only the selected body is evaluated. The output retains module ID and rule ID
as a qualified identity pair, plus receipt/rule source and authority references.
The native selection trace additionally retains candidate/predicate decisions,
selected rule, lazy bodies and failures. Early audit output must disappear when
any later calculation fails; blocked finalization emits no statement or closing
state. This profile has no financial state or inferred rounding.
