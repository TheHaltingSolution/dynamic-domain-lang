# Supplied settlement adjustments

This registered synthetic method calculates selected C12/C16 withholding,
minimum-payout eligibility and issued/unissued carry. The
[readable policy](policy.md), [neutral original facts](neutral.json),
[design boundary](../../docs/spl/settlement-design.md) and independent
[oracle](../../oracles/settlement_adjustments.py) define its selected scope.
Evidence remains a proposed `research_assumption`. No tax applicability,
professional approval, bank execution or general settlement lifecycle is inferred.

`amounts.spl` is a pure imported library: aggregate new gross entitlement,
withhold once at the supplied rate with half-even cent rounding, add prior
unissued net entitlement and test the explicit `>=` payout threshold.
`settlement.spl` validates the supplied population and original obligation
applications, calculates actual paid amounts from separate cash evidence, and
retains exact structured state. All input money is nonnegative integral USD
cents; issue, payment and application amounts are positive.

The baseline earns 100, withholds 10 and nets 90. It separately supplies a notice
for 90 and an actual payment/application of 80, leaving 10 on the original
notice. The next period nets 9 and issues nothing: closing unpaid is 19, split
between unissued 9 and the old issued 10. The third period nets 18; its new issue
candidate is 27. A separately supplied notice of 27 and actual payment 20,
applied 10 to each old/new notice, leave 17 on the new notice. Old issued money
is never included in the new issue candidate or withheld again.

Eligibility alone creates no issue notice. The generic canonical wrapper keeps
`issuance_status = unissued`; supplied original issue events and actual cash
are represented separately in the calculation outputs. An old issued balance
remains due even when current new-issue eligibility is below the threshold.

Every run needs one matching complete-settlement-population attestation plus
referenced source evidence. Only this explicit completeness claim permits empty
payment populations to produce `complete_no_events`. Missing completeness blocks
with `no_event_supplied`, no numeric actual-paid result and no consumable state.

## Run and inspect

Use the repository's pinned Python/Lean setup and build before calculations.
Registration is deliberate development preparation; it must not repin an issued
historical package during execution.

```powershell
& 'C:/Projects/Film_TV_participation_dynamic_DSL/environment/python/python.exe' -m cases.settlement.build_modules
& 'C:/Projects/Film_TV_participation_dynamic_DSL/environment/python/python.exe' -m unittest Tests.test_settlement_oracle Tests.test_settlement_modules -v
```

The builder writes `amounts-module.json`, `settlement-module.json` and an
intentionally unbound `canonical-package.json`. For a fresh invocation, call
`settlement_package(fixture, reference=registered_reference)` and then
`run_settlement_package(package, registry_root, backend="compare", artifact_dir=...)`.
The helper binds current compiler/runtime/closure identities without calculating
withholding, eligibility, paid money or balances. Compare mode checks reference,
native IR and native-emitted Lean. Tests register a temporary independent closure
and do not refresh the checked-in fixtures.

The selected helper delegates to the generic runner. For its explicit missing
population diagnostic only, it changes the unfinalized blocked payment label
from generic `not_assessed` to `no_event_supplied`, updating `result.json` to
match. It first rejects any supposedly blocked result carrying finalized results,
state or a result digest. Successful generic results and their digests are never
changed; their calculation's comparison fields carry the assessed payment status.

Tests compare every material financial intermediate, obligation movement and
closing state to the independent neutral-fact oracle. Selected methods exercise
native execution explicitly; reference-only negative groups are named as such.
The carry test serializes actual canonical closing cells, removes their movement
annotation, and passes them to the adjacent successor. It retains the cell's
actual `prior_result_ref` separately from neutral case identity and checks it
against the supplied predecessor summary. These checks establish consistency of
supplied provenance; they do not authenticate or cryptographically verify an
external historical account.

On 23 November 2026, one combined run passed all 29 methods: 17 independent
oracle and 12 module methods, in 123.851 unittest seconds (123.967566 process
seconds), with exit code zero and unchanged checked source bytes. The raw log
and source-pinned record are retained under
`C:/Projects/Film_TV_participation_dynamic_DSL/artifacts/spl/settlement-module-checks-3dffec9f`.
This is a supplemental selected-method run, not a full repository regression or
a broader C12/C16 completeness claim.

## Transport and execution boundary

The adapter validates exact neutral field shapes and Gregorian event-date versus
observation chronology for current earned, issue and payment records. It tags
money, reduces exact rational spellings, and preserves original fields. SPL
checks selected periods, exact cutoff, evidence references/scope, history,
thresholds, issuance amount, payment applications, caps and reconciliation.
There is no Date-to-Instant conversion primitive in this calculation; direct
typed SPL execution does not repeat the adapter's cross-type chronology check.
Carried original issue date/observation/source evidence comes from the exact
predecessor snapshot and is retained, rather than reconstructed from payments.

Neutral history uses category-qualified strings such as `earned:row-1`. Typed
state stores `Tuple<Text,Text>` pairs, mechanically split at the first colon and
joined on export. Raw Text identity can itself contain colons or Unicode. Text
concatenation and Text-keyed maps are outside the current admitted kernel, so
the source uses finite filter/count membership and uniqueness checks plus
existing Text/tuple sorting. It adds no compiler primitive or ASCII restriction
to these raw financial event IDs. Existing typed agreement/participant/pool/asset
identifiers still use the compiler's ASCII identifier profile.

Repeated scans make validation quadratic in the supplied population/history in
the common case; the linked payment/obligation date check can scan their product
per application. The verified fixture is deliberately small: baseline has two
earned rows and one issue/payment/application, and the three-period witness has
at most two active obligations and two current applications. This is no measured
large-population capacity result. The generic fact/event resource guard remains
an admission limit, not a performance promise; future indexing must preserve
the same arbitrary Text identities, ordering, errors and lineage.

The slice excludes cancellation/reissue, signed reversals, transfers, general
deduction ordering, dependent-period restatement, multi-currency settlement,
tax administration, concurrent state commit and general payment execution.
