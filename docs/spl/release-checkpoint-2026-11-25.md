# SPL bounded research checkpoint

The verified source is `87d140df4aada6c800fcd96932bb2a24c84761fa`, tagged
`spl-bounded-research-20261125`, on Lean 4.35.0. The release executes the named
Screen Participation Language
profiles with exact financial quantities, pinned policy and source inputs,
and inspectable result, state and lineage. The [release reproduction
guide](release-reproduction.md) gives the commands for a fresh checkout.

All 1,558 regression methods passed with zero failures, errors or skips.
Twelve short, isolated worktrees built the default and indexed targets and
ran both smoke executables. The aggregate verified that their selector
sets cover the complete suite exactly once, with unchanged source and build
fingerprints. The [release evidence index](release-evidence-2026-11-25.json)
records exact identities, archive hashes and external receipts under the
project's `artifacts/spl/` directory. The earlier candidate canary stopped
after 203 methods and has its own partial receipt.

## Financial cases and interfaces

| Profile | Finite qualification |
| --- | --- |
| C09 reserve stages | Gross-basis reserve and earned-producer holdback have distinct state keys for the same financial scope. Original gross USD 100, fee USD 10 and a 20% reserve rate yield additions of USD 20 and USD 9 respectively. The selected release schedule consumes original actual additions under its stated limits. |
| C10 cross-contract burdens | Separate claimant entitlement remains USD 100. The covered agreement starts at USD 200 and ends at USD 170, USD 185 and USD 200 across the selected carry chain. Paid and accrued bases produce distinct burdens. |
| C11 ordered gates | The selected original-event sequence gives USD 0, USD 6 and USD 2 across three periods. The original scope and saved boundary govern carry. |
| C13 corrections | The simple and dependent examples give USD 40 and USD 18 outstanding. Original issues and actual payments remain distinct. Repeating the accepted correction adds zero. |
| Exact numeric profile | Ratio and monetary quantization are dimensioned separately. The retained profile exercises five rounding modes, signed ties and row versus aggregate rounding. |
| Reports and dates | Checked report and closing fields retain their types. Scoped evidence IDs link the original funding, gate and worksheet events to projected inputs. Authored source locations and concrete binding pointers accompany covered failures. Optional report and intended-issue dates remain supplied metadata. |
| Relationships | Named physical profiles check unique original identities, references, authorized recipients, allocations and invoice applications before calculation. The 2-by-3 witness reconciles six contributions back to two original cash records and retains a zero-activity title. |
| Audit and carry | Compact-v2 retains the complete native logical graph under its declared guards. The bounded old-v1 receipt carries qualified state cells. Calculation and preview keep issuance and payment authority separate. |

For original facts, policies, backend credit and the precise bounds of those
claims, see the [case evidence index](session-handoff-2026-11-25.md#5-what-has-actually-been-verified),
[physical relationships](physical-relationships.md), [report and audit
coverage](report-audit-coverage.md) and [current requirement inventory](completion-backlog.json).

The portable reserve rerun on this commit produced 16 calculated checkpoints,
including ten actual successors, and six unissued previews with no consumable
closing state. An independently compiled Python-emitted program matched the
native result on each run. The public reader also reloaded nine pre-source
blocks. The two namespace tests used the same agreement, participant, pool
and asset. Their respective producer results were USD 35 and USD 36 in the
first period and USD 10 and USD 9 from the subsequent release.

## Repeated capacity measurement

The measured RR03 single-pool workload is the legacy SV synthetic cash, cost,
invoice and funding mix. It exercised public compare-mode calculation with
compact-v2 and independent public consumer reload. Four fresh-process
observations per size succeeded. The first 100-record sample compiled the
target. Cached median total times through the consumer reload were 5.062
seconds for 100 records and 40.183 seconds for 1,000 records.

Four actual successive closes at each size consumed the previous
publication's state and result reference. Each sequence recovered USD 250
in the first quarter and USD 0 thereafter. The chains retained 385 and 3,850
distinct original records. The [capacity envelope](capacity-envelope.md)
gives input sizes, output sizes, latency, working sets, guard proximity,
host conditions, earlier observed failures and unmeasured workloads.

## Scope and follow-up

The release qualifies the named profiles and their finite execution checks.
The Lean toy proof applies to its toy lowering. Contract accounting approval
and payment require their own evidence. Professional review would need to
identify the actual original source, policy and result bundle.

Broader feature-combination testing awaits the owner discussion. General
data interfaces, additional sourced contracts, convenience syntax, native FX,
the tool-driven compiler extension and large-scale batch infrastructure
remain future work under the [owner scope](session-handoff-2026-11-25.md#1-read-this-first-the-owners-final-scope).
