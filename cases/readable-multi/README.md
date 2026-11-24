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
