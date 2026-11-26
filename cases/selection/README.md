# Scoped rule selection

The [readable policy](policy.md) and [original neutral facts](neutral.json)
register three separately named synthetic methods:

| Module suffix / method | Cash 100, matching .2 rule | No match | Selected zero |
| --- | ---: | --- | ---: |
| `unique_no_fallback` | 20 | `NO_APPLICABLE_RULE` | 0 |
| `unique_explicit_fallback` | 20 | Explicit .1 fallback gives 10 | 0 |
| `priority_explicit_fallback` | 20 | Explicit .1 fallback gives 10 | 0 |

[selection.spl](selection.spl) performs scope, Date, observation and authority
checks and executes registered unique/priority selection. The adapter transports
original facts and exact numbers; it never calculates an applicable flag, winner,
selected rate or earnings. The three original rule slots are primary, competing
and unsafe, with explicit source/evidence links. Primary/competing priority 20
and unsafe priority -10 are part of this finite registered policy. The disabled
slots remain original supplied facts; an empty applicable candidate set is not
an absent source population.

Equal-valued duplicate unique matches and tied greatest priorities block before
any body. Predicates remain demanded across lower priorities. A selected failing
body blocks without fallback. A lower-priority unselected body and an unused
fallback may contain division by zero and must remain lazy. Zero earnings from
a selected rule retain that selected identity rather than activating fallback.
The record-valued choice retains rate, earnings and source together; consequently
its trace selection status is `calculated` even when the earned field is zero.
The explicit earned value and selected rule establish the zero discriminator.

The common original-fact frame validates receipt, all rule source/authority
records and fallback terms/authority before selection. This includes the unused
fallback in the no-fallback method; it never makes that method evaluate a fallback
body. All rule matching and earning arithmetic remain inside SPL. Receipt and
rule scope use declared `Id<Agreement>`/`Id<Asset>`, channel is Text, effective
intervals are half-open Dates and observations use the exact exclusive cutoff.
The selected result includes the registered module ID and local rule ID as an
explicit qualified identity pair, plus original receipt/rule/evidence references.
The native trace retains source spans, demanded candidate decisions and skipped
body nodes. No statement issue, bank payment or financial carry is inferred.

## Actual rejection stages

The generic canonical wrapper recursively validates declared scoped IDs. A
one-field agreement/title mismatch in a receipt, rule or evidence record therefore
fails as `MODULE_REFERENCE_SCOPE` **before financial SPL executes**; these
canonical cases correctly have empty traces. This is not a native financial
scope witness. The source also has its own receipt/evidence scope checks for
direct execution, without claiming those checks caused the canonical rejection.

Channel, effective-start/end and rule-observation near misses reach financial
selection. The no-fallback method blocks for no applicable rule; the explicit
fallback variant earns 10. Effective-start equality is included, effective-end
and observed-cutoff equality are excluded. The receipt itself must be in the
run period and observed before cutoff; it is not silently converted to absent
cash. A selected rule's wrong authority identity or false approval reaches SPL
and blocks as `SELECTION_RULE_AUTHORITY`.

Empty evidence, invalid generic approval references and evidence exactly at
cutoff fail wrapper admission as `MODULE_EVIDENCE_REQUIRED`,
`MODULE_EVIDENCE_AUTHORITY` and `EVIDENCE_AFTER_CUTOFF`. They must not be reported
as native calculation failures. The policy and test matrix distinguish these
stages and preserve atomic empty statements/results/closing state on failure.
An early source audit emission is deliberately present to verify that a later
predicate/body failure cannot publish a partial result.

## Registration and verification

Run the mechanical authoring command to regenerate the three descriptors and
unbound templates after an intentional source or policy edit:

```powershell
& C:/Projects/Film_TV_participation_dynamic_DSL/environment/python/python.exe -m cases.selection.build_modules
```

`register_selection(method)` is an explicit authoring operation.
`selection_package(fixture, reference=..., bind=True)` uses existing descriptor
pins, transports originals, and binds current compiler/runtime identities.
Execution does not repin an already issued package. The committed
`*-package.unbound.json` files intentionally have unbound implementation pins;
bind them through the generic wrapper before execution. Each descriptor fixes
its method and module identity through registered methodology domains and pins
this readable policy and the source. Switching a method without selecting its
separate module fails `MODULE_PARAMETER_DOMAIN`.

`Tests/test_selection_modules.py` has six reference methods and two native
methods. Independent hand controls determine expected money, winner and error
before backend comparison. The native source is compiled once for 19 original
fact variants, with native IR and emitted execution compared to the reference.
Two cases also exercise the separate Python-to-Lean emitter. Nine representative
canonical packages exercise actual native atomic finalization. Scope rejection
is separately tested at its real wrapper stage. This is finite behavioral
verification, not a proof of the parser, policy or generic wrapper.
