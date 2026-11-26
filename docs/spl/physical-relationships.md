# Bounded physical relationship safeguards

The physical package validator checks the relationships used by the existing
SV incurred-date, RQ-07 posted-date and LG cleared-work workflows before
projection or SPL execution. The original fixture adapter, the canonical
package validator and the financial calculation each have a separate role.

| Relationship | Enforced rule |
| --- | --- |
| Original identity | A fact ID is unique. Within each amount kind and versioned source batch, a physical source row can supply one fact. The same rule applies within each evidence kind when evidence names a source batch and row. |
| Financial fact ancestry | A supplied parent resolves to one fact. Cycles and a cash receipt with a cash ancestor block. Several cash receipts may share an invoice parent. The invoice stays in its own amount space. |
| RQ-07 cash application | A cash application requires an invoice parent for its original source asset. The independent subtotal of applications against each invoice cannot exceed its face. The pinned raw adapter also checks application, invoice and bank references and reconciles each bank deposit. |
| Agreement and cost bindings | Agreement asset and role relationships are unique. Effective participant and distributor binding retains the named physical profile cardinality. A cost selection names one incurred-cost fact, with at most one decision per fact. |
| Exact-weight split | One selected group per original cash fact assigns one row per authorized in-scope title. Every child view ID is distinct from every original fact ID. The allocation scope, active period and approved weights govern the split, and weights sum exactly to one. |

The [physical relationship tests](../../Tests/test_physical_relationships.py)
reconcile two original cash receipts of USD 90 and 60 against six distinct
child contributions with weights 0.2, 0.3 and 0.5. The title totals are USD
30, 45, 75 and an explicit zero for a fourth title with no contributed cash.
The USD 1,000 invoice face is excluded from the cash measure. Each child
retains its original cash fact ID and the resulting earned and payable totals
are both USD 32.40. The positive case compares native interpretation, emitted
Lean and the reference evaluator. Mutations with missing or duplicate
references, aliases and conflicting recipients fail at package admission.

The RQ-07 original adapter produces two cash applications totaling USD 160,000
against USD 210,000 of separate invoice face. The tests preserve individual
invoice identities and the three direct or allocated cash contributions. A
mutation can move USD 1 from one application to another while preserving all
grand totals. The per-invoice check still rejects the overapplication.

The [collection witnesses](../../Tests/test_collections.py) separately exercise
the core join's six occurrences for a 2-by-3 matching key. The join deliberately
preserves multiplicity. The physical checks govern which identities may
contribute to particular financial measures. The named
[quantized allocation](../../cases/quantized-allocation/README.md) profile
also checks its required recipient registry and parent-first cent
reconciliation in SPL under its documented limits.

Run the focused checks from the checkout under the pinned toolchain and a
Python import path selected for that checkout.

~~~powershell
lake build
lake exe smoke
lake env lean --run Tests/SPLCollections.lean
python -m unittest Tests.test_physical_relationships Tests.test_acceptance Tests.test_mixed_workloads
~~~

This covers the named physical bindings and selected collection and allocation
controls. General descriptor-level relationship declarations and validation of
arbitrary schedule joins remain deferred.
