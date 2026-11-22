# Selected synthetic capital waterfall

This is a project-selected C03/C07 synthetic policy with proposed review status.
The optional RR-03 Roundlake numeric seed motivates one fixture. It is not a
historical execution, an interpretation approved by a professional, or evidence
of vendor equivalence. The 120 / 100 / 100 witness distinguishes recovery methods.

All amounts are exact USD, without rounding, FX, interest or bank execution.
For each period: fee = gross cash times supplied fee rate, **before** eligible
costs; available funds = gross minus fee minus eligible costs. Negative cash,
ineligible costs, costs exceeding available cash, and missing scope/evidence
block the whole calculation. No unselected scope is silently discarded.

The shared capital ledger belongs to the explicitly declared participant group,
agreement, pool, asset and capital_recovery purpose. The group identity is a
separate participant identity in the canonical authorized participant set; it is
never an individual beneficiary. Beneficiaries are explicitly enumerated. Each
claim names its beneficiary and has capital kind, original principal and current
unrecovered balance. The group-owned structured state retains every claim,
including zero balances, across serialized period boundaries. No new claims or
capital additions are introduced by the selected method. Multiple distinct
claims may name one beneficiary; duplicate claim identity blocks.

Priority recovery orders claims by the complete supplied (priority, sequence)
tuple, ascending; identity is declared separately, with ties rejected. Both
methods retain this explicit order for deterministic movement reporting. Neither
source position nor lexical claim ID supplies an economic tie breaker. Pro rata
recovery allocates min(funds, total opening claims) in proportion to each opening
balance. Zero total claims gives zero recovery without division. Recovery cannot
exceed any opening claim. Residual funds are allocated using supplied nonnegative
beneficiary weights and their positive total; zero total weight blocks even when
the residual is zero. Fee rate and residual weights are supplied terms; recovery
method and ordering are explicit methodology. Group state closes once, with
per-claim movement detail and beneficiary statements, never once per beneficiary.

Scope, purpose, currency, period and cutoff are explicit checked package/source
boundaries. All financial facts must carry the exact selected agreement, pool,
project, group, purpose and USD currency, lie in the selected half-open civil
period, and reference evidence observed strictly before the supplied cutoff.
Future amendments, refunds, competing claim kinds, reserve uses, revised claims
and interpretation of the filed Roundlake agreement are outside this fixture.
