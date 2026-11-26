# Quantized original-parent allocation

The immutable [selected policy](policy.md), [original fixture](neutral.json) and
[independent oracle](../../oracles/quantized_allocation.py) select parent-first
half-even rounding and two distinct allocation authorities. This is a proposed
synthetic `research_assumption`, not an interpretation of an unidentified contract.

[allocation.spl](allocation.spl) is a pure registered library. It rounds each
original parent once, calculates exact target-based cent quotas, floors and
fractional remainders, ranks by descending remainder then ascending ASCII
recipient identity, and assigns residual cents. It also retains original-parent
exact quotas and separately calculates the authorized supplied-cent alternative.
The adapter provides no solved targets, quotas, ranks or residuals.

[quantized-allocation.spl](quantized-allocation.spl) checks the complete scoped
recipient and authority populations, approval Dates, exact observation cutoffs,
current parent periods and original history. It replays historical periods,
rejects reused parent IDs, source references and specific upstream lines, and
requires the actual adjacent closing cell and matching predecessor snapshot.
Method, policy and complete original recipient registry remain pinned in state.
Only selected children are recognized contributions; reported original parent
amounts are a separate amount space, and no cash payment is inferred.

The finite limits are eight recipients, four original parents in a period and
eight historical periods on input. An input with eight histories can produce a
ninth history entry; a subsequent close is blocked. Empty parent populations and
zero-valued parents are explicit, while an absent recipient universe or zero
weight denominator blocks. Every supplied original row remains validated.

[build_modules.py](build_modules.py) validates closed record shape, exact
nonnegative decimal/fraction lexemes, the selected ASCII identity profile and
specific upstream-line syntax. It transports original values into typed inputs;
the original numeric and Instant lexemes remain beside their decoded values and
are restored from actual state by `neutral_state`. SPL checks typed Instant
values against their source spellings. Numeric decoding/lexeme consistency is a
canonical transport responsibility; raw arbitrary native bindings do not acquire
a separate provenance guarantee. The ASCII restriction is this case's declared
identity profile and does not change unrelated Text IDs.

Explicit registration writes both descriptors and the unbound canonical example:

```powershell
python cases/quantized-allocation/build_modules.py
python -m unittest Tests.test_quantized_allocation_modules
```

Execution defaults to native IR/generated Lean/reference comparison. Tests build
temporary registrations so issuing a new case does not silently repin an existing
package. Native-named tests request comparison explicitly; reference and physical
shape checks are labeled separately.

The first source draft retained a full 1,890-node trace of 84,470,385 bytes and
failed the unchanged 64 MiB publication guard. Its anonymous replay instance
embedded the complete original record in repeatedly escaped dependency IDs. The
current source uses a transient wrapper whose `id` is the validated original case
ID and whose `original` still contains the full record. This is a new source
representation with the same financial policy; no old/new graph identity or
general capacity claim follows. The failed draft remains external at
`artifacts/spl/quantized-allocation-draft-native-b`.

The frozen 23 November cohort passed all 44 methods in 177.268 seconds: 24
immutable oracle controls and 20 module methods. Nine module methods made 15
explicit native IR/generated Lean/reference comparisons (ten calculated, five
blocked) through 60 actual Lean commands. All 15 publications passed the bounded
completed-result loader and equaled the returned result. Source and compiled
artifact hashes stayed unchanged; there were no failures, errors or skips.
Evidence is external at `artifacts/spl/quantized-allocation-checks-20261123-a`,
including source snapshots, preprojection original-fact controls, actual inputs,
typed IR, emitted Lean, decoded stdout capture, full publications and both hash
manifests. Compiler/module/runtime pins are `20ea52ba…` / `a5165f5d…` /
`673bb0fe…`; the retained verification contains their complete values.

The measured native maxima tested separately include eight recipients and four
parents, with a largest result of 24,754,928 bytes under the unchanged 64 MiB
guard. Actual native adjacent carry preserved complete original values, decimal
and timestamp spellings; its second result was 13,716,139 bytes. The eight-history
input boundary and subsequent blocked close were tested with actual reference
state across nine empty closes. This does not establish native completion for
every Cartesian combination of the finite bounds, a larger population, payment
execution or a performance SLA. Timings include concurrent immutable unit-suite
host load.
