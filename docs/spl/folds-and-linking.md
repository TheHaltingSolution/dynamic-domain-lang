# Finite folds and first-order linking

The reusable baseline implements finite pure state transitions. It does not
derive calendar-month deadlines; DYN-CAL-01 remains deliberately absent.
Compiler-correctness proofs for these capabilities remain deferred.

The fixed R1 operational envelope is 100,000 items per decoded or intermediate
list/map, 100,000 produced join pairs, and 100,000 native/reference interpreter
observations. Oversized values fail `RESOURCE_LIMIT` without truncation or final
outputs. These guards are resource ceilings, with no throughput or service-level
claim. Generated execution enforces collection/pair bounds; its output does not
claim direct target branch coverage or a target-instrumented audit trace.

```text
fold events from initial with state,event {
  define next = state + event;
  require next >= 0 else "NEGATIVE_BALANCE";
  yield next;
}

ordered_fold events from initial
  by key_event => tuple(key_event.effective_date,key_event.priority)
  identified by identity_event => identity_event.event_id
  ties "reject"
  with state,event {
    yield state + event.amount;
  }
```

The initial expression is demanded first, once, including for empty events.
Plain fold traverses the supplied list from left to right. Its two distinct
binders are immutable and cannot shadow an enclosing binding. All step bodies
are checked; each result must preserve the initial state's structural type.
Definitions and assertions execute in their declared order using the existing
lexical dependency rules. A record state can hold a finite output/history list
using `append(list,item)` or `concat(left,right)`.

Ordered fold demands every declared identity in input order, then every
semantic key in input order. Identity and key projections accept the admitted
total-order key types, including finite tuples. Duplicate declared identities
fail `DUPLICATE_EVENT_ID`, including identical IDs with different dates/keys.
Equal complete semantic keys fail `UNRESOLVED_EVENT_ORDER`. Only `ties "reject"`
is supported. An additional event-ID component is used only when explicitly
written into the semantic key; there is no implicit stable/source-position tie
rule. No economic step executes before the entire ordering phase succeeds.

Each step observes event identity, ordering key/tie policy when applicable,
state before, state after on success, and failure status on error. A failed step
stops later events. A diagnostic trace prefix is retained, while the settlement
returns no emissions or closing state. The pure operation does not mutate inputs
or establish external database transaction guarantees.

Calculation-module sources are ordinary SPL schedules containing typed `input`
parameters, `define` declarations and `require` assertions. They contain no
opening, closing or emission ports. Their descriptor interface exports functions:

```json
{"name":"allocate","parameters":[{"name":"amount","type":{"name":"Money","args":[{"name":"USD","args":[]}]}}],"result":{"name":"Money","args":[{"name":"USD","args":[]}]},"definition":"allocated"}
```

The initial function profile requires each export's parameter list to exactly
match the module source's input list. `definition` names the returned definition;
the complete local define/assert block is preserved in lexical order for each
call. Import metadata is exactly
`{module_ref:{id,revision,locator,sha256},alias,symbols:[{export,local}]}`.
The source call uses its declared local symbol, for example `allocate(receipt)`.

The canonical resolver verifies descriptor/source digests and all exact
transitive references before constructing a pure linking manifest:

```text
{modules:[{reference:<exact reference>,source:<source text>,descriptor:<descriptor>}],
 imports:<root descriptor imports>}
```

`SPL.Link.link` and the independent `spl_compiler.linker.link_schedule` consume
that manifest without reading files or evaluating host-language code. The native
CLI accepts `--link MANIFEST.json` for check, IR, interpretation and compilation.
Module imports and function calls must be acyclic. Every export is checked,
including unused exports. Missing transitive pins, unexported symbols, duplicate
aliases, ambiguous local symbols and builtin collisions block linking.

Calls lower to explicit application nodes, preserving named parameter types,
strict arguments and the isolated local block. Arguments evaluate exactly once,
left to right, even when a parameter is unused. Only the evaluated argument
values enter the callee scope. The caller cannot supply captured names, module
helpers cannot capture caller bindings, and nested calls use their module's
declared namespace. There is no textual substitution or arbitrary Lean escape.

Exact pins establish artifact identity, not economic approval. The registered
policy, evidence, canonical codec and state-writer checks retain their separate
scope. Legacy whole-program registrations remain available in their original
profiles.
