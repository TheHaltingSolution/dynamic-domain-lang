# Linkable SPL validation appendices

The [receipt validator](sv-receipt-validation.spl) and the
[posted-cost validator](sv-posting-cost-validation.spl) use the existing
`SVReceipt` and `SVPostingCost` formats. Each declares a typed input list and
period, checks fact identity and date membership, and exports `validate`.
The [readable policy](policy.md) describes the checks for a participant.

This example expects period-scoped feeds. A schedule that consumes a wider
history can select its period's facts explicitly before passing the selected
rows to these validators. The checks use `cash_received_date` for receipts
and `recognition_date` for posted costs. Both feeds admit their first day and
exclude their ending boundary. Eligibility and feed completeness come from
the supplied evidence.

The [Readable schedule](participation-readable.spl) names the policies and
requires the validator calls before emitting its result. The
[registry reference](reference.json) pins the schedule's descriptor, which
pins both validator modules. Each library descriptor pins its SPL and
readable policy. The example exports the resolved closure as a native linking
manifest, so the same source and dependencies reach interpretation,
compilation and verification.

From the repository root, use the pinned Lean setup and a fresh output
directory. The example uses `work/` as a placeholder for that directory.

```powershell
python -m cases.validation.link_manifest work/link.json
python -m spl_compiler.verification certify `
  cases/validation/participation-readable.spl work/certificate --link work/link.json
python -m spl_compiler.verification run work/certificate cases/validation/bindings.json
```

The fixture independently yields USD 25 from USD 150 of receipts and USD 25
of posted costs at a 20% share. The comparative certificate checks the
compiled settlement against the reference translation over all typed
bindings, including the guards. The tests also exercise duplicate identities,
dates on both sides of the period boundary, and a later failed period with
no partial result. This evidence covers translation and these checked
behaviors. The separate Lean soundness proof shows that successful
zero-failure counting establishes half-open membership for every supplied
row with typed date fields. It applies to the runtime operations emitted by
both date guards. A general soundness proof for the grouping-based duplicate
check remains outside that theorem. [Validation proof](../../SPL/ValidationProofs.lean) ·
[Validation tests](../../Tests/test_linkable_validation.py) ·
[General verification design](../../docs/spl/general-verification-design.md)
