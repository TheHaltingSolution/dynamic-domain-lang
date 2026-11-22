# Synthetic reserve vintage ledger, revision 1

This proposed registration preserves RR-02 and its supplied synthetic fixture.
`SYNTHETIC-RES-VINTAGE` and `synthetic-vintage` are explicit policy selection and
fixture authority decisions. Their proposed status is not professional approval.

One scoped structured state cell holds the complete finite vintage list for one
agreement, participant and pool, exclusively for `return_reserve`. Each vintage
has its own identifier, USD balance, currency and purpose. The source checks
each record's scope and unit; its typed codec requires unique vintage identifiers.
The initial original snapshot needs no fabricated prior result. Published
successor cells retain their scoped boundary, provenance and prior result
reference. The structured transition has a single authoritative writer.

Movements must lie within the half-open settlement period and be observed
strictly before the selected Instant cutoff, equal to the manifest cutoff.
Each unique movement references unique matching evidence for the same vintage,
scope, purpose, currency, amount and date. The source requires approved evidence
under the selected fixture authority and its observation before cutoff. Evidence
kinds distinguish authorized addition, actual return application and authorized
release. These actual typed evidence rows remain input ports, without adding
attestation fields or synthesizing approvals.

The selected stages are addition, actual return application, then unused release
per vintage. Applications and releases cannot exceed the stage's available
balance. This is exact finite-period ledger arithmetic, without rounding. It
does not select a receipt, earnings or payment-stage reserve, or establish
chronological cap compliance. The baseline independent controls close vintage-1
at zero and vintage-2 at 20; the aggregate closing reserve is 20. A following
quarter may carry the published structured snapshot and liquidate the remaining
vintage with supported applications/releases. The ledger does not compute a
payable, issue an obligation or prove actual cash payment.
