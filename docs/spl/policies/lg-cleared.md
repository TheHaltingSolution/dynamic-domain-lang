# LG already-cleared synthetic policy, version 1

Policy identity: `lg-cleared@1`. Economic profile: `lg-cleared-v1`.
Incorporated by [the readable LG schedule](../../../cases/lg/lg01-readable.spl).
This is a bounded synthetic interpretation with proposed review decisions, not
complete agreement implementation or historical payment evidence.

Use the Gregorian half-open quarter in `parameters.policy.period`, baseline
2026-01-01 through, excluding, 2026-04-01. This is a synthetic calendar profile;
the sourced fiscal reporting calendar is not implemented. The declared work
`parameters.policy.asset_id` is `work-D`; agreement, participant and net pool
are `parameters.policy.agreement_id`, `participant_id` and `pool_id` (baseline
`lg`, `seller-group`, `crossed-group`). Agreement/role/pool membership records
must authorize exactly this work for this profile. Work gate scope and crossed
net-group scope remain distinct even though the baseline group has one member.

Two separate prerequisites must hold. The agreement-level outside hurdle
attestation must be true, observed within `manifest.cutoff`, scoped to this
agreement, and effective **strictly before** the quarter start; equality blocks.
Baseline effective date is 2025-12-31. Separately, the supplied work gate-history
attestation must affirm continuous clearance for this exact work and complete
quarter. These facts are `evidence_events` of kinds `hurdle_attestation` and
`gate_history`, authorized by `LG-OUTSIDE-HURDLE` and `LG-GATE-HISTORY`.
Opening cumulative gross must cover opening cumulative cost; ending cumulative
gross must cover ending cumulative cost. Crossing or recrossing during the
quarter is outside this profile and blocks rather than selecting a new policy.

True Cash includes **full** eligible same-work receipts selected by cash-received
date during the quarter. Actual Cost is separately approved same-work actual
cost incurred during the quarter, with `parameters.cost_date_basis` equal to
`incurred_date` and explicit `parameters.cost_decisions`. Missing incurred dates
block. These measures update the separate work-gate cumulative gross/cost
states. Video weighting never changes True Cash or this gate test.

The gross payout base is full eligible non-video receipts **plus eligible
home-video receipts multiplied by the video proxy rate** in
`parameters.policy.video_proxy`. The typed receipt channel flag implements
that classification. The applicable gross and net participation rates are
`parameters.policy.gross_rate` and `parameters.policy.net_rate`. Baseline values
are video proxy **25%**, gross **20%** and net **20%**; actual bound values must
be exposed in the run review package. Baseline non-video 180 plus video 120
times 25% gives gross payout base 210, while True Cash is 300.

When the cleared-work gate holds, Gross Candidate is the **synthetic zero
floor** of (gross rate times gross payout base less the supplied producer fee
offset). This profile applies `parameters.producer_fee_offset` **only to the
gross candidate**, once; it does not subtract it from the net candidate or from
the greater-of result. Baseline offset is USD 12, yielding gross 30.

Crossed Net Subtotal is a **supplied worksheet**, not a subtotal derived by this
compiler. The single `crossed_net_worksheet` evidence event must have approved
authority `LG-NET-BRANCH`, this agreement/net pool/quarter and the authorized
member set. It supplies baseline USD 175; negative subtotals block pending loss
policy. Net Candidate is net rate times that subtotal (baseline 35). Select the
greater gross/net candidate, with equality reported as `tie`; baseline earned
is 35. Exact rational arithmetic introduces no rounding stage.

Opening work-gate gross/cost and **synthetic payment holdback** are separate
supplied `state_cells`, selected through `opening_aliases` and authorized by
provenance and policy lineage at the opening boundary, with agreement,
participant, pool, work, currency and scenario dimensions. Baseline balances
are gross 100, cost 100 and holdback zero. Holdback movements are
`parameters.payment_holdback_addition` and `payment_holdback_release` (both
baseline zero). They must be nonnegative; release cannot exceed opening and
addition cannot exceed earned plus release. Payable equals earned plus release
less addition; closing holdback equals opening plus addition less release.
This synthetic settlement-stage mechanism does not implement the agreement's
basis-stage video-return reserve. Baseline payable 35 is calculated and
unissued, not actual payment. Failed prerequisites/evidence/scope/state block
statement and closing state atomically.

[The registry](manifest.json) records machine-checkable binding and formula
requirements; canonical execution pins this text and exposes its actual
parameters/evidence/state. Native incorporation alone preserves provenance;
the wrapper's consistency checks are bounded checks, not semantic proof or
independent contract interpretation approval.
