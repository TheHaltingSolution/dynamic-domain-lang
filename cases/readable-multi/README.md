# Multiple readable settlement headings

The [readable source](two-participants-readable.spl) visibly reports USD12 for
the first explicit participant and USD7 for the second. Its footer registers
both participant expressions and report columns. These simple source constants
exercise roles and report transport, not a new royalty or payment policy.

[The independently written core source](two-participants.spl) and shared
[typed bindings](bindings.json) supply the comparison. Multiple headings have
separate generated participant roles; ordinary monetary definitions, public
report names and closing writers retain existing core behavior. Reusing one
unambiguous `Settle` binding is permitted. This source declares no bank movement.

The retained [verification](C:/Projects/Film_TV_participation_dynamic_DSL/artifacts/spl/readable-multi-checks-20261124-a/verification.json)
indexes four native-IR/native-C/reference/Python-emitted positive programs and
eight pre-runtime rejection controls. New role/heading diagnostics retain exact
authored spans. Ordinary core duplicate-name diagnostics retain each backend's
existing behavior, verified against c80 single-heading controls. The three old
readable profiles preserve their expansion, authored mapping, full reference
outcome and native IR; their independent core IRs remain unchanged as well.
