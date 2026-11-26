# Independent Genius basis-reserve controls

This is a standard-library oracle over original synthetic facts for the selected
[policy](../../cases/basis-reserves/policy.md). It precedes a separately authored
SPL implementation. It does not import compiler modules, source adapters or SPL
calculation helpers. The contract-specific stage is reserve before fee; the
unused-vintage balance is released once, with the selected fee on release.

The source and review trail is:

- [Primary SEC agreement](https://www.sec.gov/Archives/edgar/data/1098016/000119312506200074/dex101.htm),
  §§1–4, 9(c), 10–11, 20 and 24(d).
- [RR04 decision §3](C:/Projects/Film_TV_participation_dynamic_DSL/ResearchAgent/documents/SPL_RR04_Completion_Decisions.md:44).
- [LD03 integrated reserves specification §5](C:/Projects/Film_TV_participation_dynamic_DSL/ResearchAgent/documents/SPL_LD03_Completion_Review.md:198).
- The fixture pins the exact local review bytes by SHA-256. These are research
  assumptions and proposed operating details, not professional acceptance.

The API is `oracles.basis_reserves.basis_reserves(run_data)`. It returns exact
`Fraction` amounts and raises `BasisReserveOracleError` with a stable `BR_...`
diagnostic for invalid inputs. `exact_json(result)` serializes exact fractions
as canonical integer or rational strings. There is no native or SPL execution
claim for these controls.

The fixture envelope `basis-reserve-original-history/1` contains `facts`, a
complete five-checkpoint original history. It deliberately contains no supplied
opening financial answer or solved release amount. A runner transports a prefix
for each original checkpoint and supplies the previous run's actual serialized
closing state. `Tests.test_basis_reserve_oracle.view` performs that mechanical
transport; `chain` executes Jan → Apr → May → Jul → Oct. Source implementation
must derive reserve additions, due dates, return applications, release balances,
Net Receipts, fee and allocation from these originals.

| Original input | Required content and control |
| --- | --- |
| `scope` | Contract, participant, pool, asset and USD currency, exactly matching every fact and evidence record |
| `policy` | Exact pinned ID/revision, within-vintage method, six-month clamp rule, inclusive full-unused timing, stage order and exact arithmetic |
| `authority` | Original versioned scoped sales-period/covered-program/successor finding, effective interval, 20% reserve and disclosed synthetic 10% fee, approval, observation, source/evidence |
| `checkpoints` | Original ID and case identity, adjacent half-open intervals from Jan 1 2009, UTC-Date as-of, separate exclusive Instant cutoff, approval/source/evidence |
| `receipts` | Nonnegative original actual cash amount, receipt date, explicit stage sequence, US physical lane, original cash-line reference and election reference |
| `elections` | One approved original election/non-election per receipt, original vintage ID, same-day establishment, purpose, approval date/source/evidence |
| `returns` | Nonnegative original return magnitude, date/sequence, receipt/vintage/claim IDs, original return-line reference and separate application authority |
| `return_authorities` | Exact original return/receipt/vintage edge and purpose, approval date/source/evidence; unused/unknown edges reject |
| `populations` | One complete cumulative original receipt/election/return/application population per checkpoint, original totals, explicit zero other-adjustment population, source/evidence |
| `clearances` | Complete approved zero remaining guarantee and expense claims, explicit empty unresolved-claim IDs, source/evidence |
| `evidence` | Original scoped identity, kind, approval, exact observation Instant and source reference |
| `opening_state`, `prior_result` | Actual predecessor closing state, original case/period identity, optional externally supplied result reference; first run has an explicit zero genesis frame |

The run schema is `basis-reserves-neutral/1` with the above arrays, `case_id`,
`research` and `run_checkpoint_id`. The history envelope itself is not a run.
Bounds are 12 checkpoints, 24 receipts, 48 returns and at most 256 rows in any
array. Amount inputs are nonnegative exact decimal/rational strings. All output
effects remain exact fractions; a separate cent policy would require a distinct
method. UTC offsets and fractions beyond microsecond resolution are compared
exactly; no wall clock or inferred local zone is used.

For vintage `v`, initialize `added_v = G_v × 1/5` if elected, else zero. For each
linked return `r`, require `r <= available_v`, then subtract it once. On the
derived six-month due day, release all remaining `available_v` and set it to
zero. The output retains `added`, `applied_returns`, `released`, `available`,
original dates and lineage, including consumed original claim and release IDs.
The per-vintage and global checks are:

```text
added_v = applied_returns_v + released_v + available_v
current_net_receipts = current_gross − current_additions + current_releases
current_fee = current_net_receipts × 1/10
current_allocation = current_net_receipts − current_fee
cumulative_gross − cumulative_returns
    = cumulative_net_receipts + total_closing_reserve
```

The Jan hand control yields 800/80/720. Fee-before-reserve incorrectly gives a
100 fee and 700 allocation and is explicitly distinguished. The due controls
derive July V1 140/14/126 and October V2 160/16/144 from original cash and the
single May return. Deducting that return again incorrectly gives total Net
Receipts 1,680 instead of 1,740. Positive non-election gives 1,000/100/900.
The exact fraction discriminator `G=1/3` gives addition `1/15`, Net Receipts
`4/15`, fee `2/75` and allocation `6/25`.

Each output includes current checkpoint amounts/movements, every material
checkpoint result, cumulative totals and a structured closing state containing
the full original fact registry plus authority, research, policy and boundary.
Historical snapshots are copied rather than aliased to mutable later balances.
Replay rebuilds all prior meters and movements from originals under their own
cutoffs and checks exact equality with the transported opening. Case identity is
`source_case_id`, not a fabricated canonical result digest. A supplied-history
opening is supported only when separately labeled; it is not actual predecessor
evidence. Actual predecessor mode requires its matching original period and
closing state. Changed original facts, terms, scope, provenance or balances block
instead of silently migrating state.

Duplicate IDs, cash-parent aliases, return claims/line aliases, tied stage
sequences, mismatched scope/purpose/authority, missing population/clearance,
cutoff-equal or late source evidence, unknown vintages, forged openings and
overdue positive opening balances block. Recognizing the same full history does
not add its old financial effects to opening balances again. A second partial
return equal to V1's remaining 140 consumes it exactly; 150 cannot borrow V2's
160. Returns on the due date precede release; later returns require a different
signed source policy.

The initial acceptance remains **partial** for sourced C09: §10's excess-return
Net Receipts reduction is retained as an explicit remaining requirement. The
bounded method rejects that case rather than inventing negative-fee corrections,
zero floors or cross-vintage borrowing. Actual accounting approval, source fee
bands, upstream guarantee derivation, successor history verification and bank
payment evidence are also outside this control. Pacific Gold–Daval remains a
documentary CAD comparator; there is no native-currency approval or FX execution.

Verification is the isolated five-file source snapshot, standard-library import
check, hand controls and serialized five-run witness recorded externally under
`C:/Projects/Film_TV_participation_dynamic_DSL/artifacts/spl/`. That execution
record supplies the exact test count, hashes and stdout without claiming backend
agreement as an independent financial expectation.
