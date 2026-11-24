# Synthetic ordered Lionsgate work gate

Policy `SYNTHETIC-LG-ORDERED-GATE-01@1` is a proposed, bounded synthetic
operating policy. It preserves the existing cleared LG-01 policy. The economic
source is the September 10, 2007 Lionsgate–Mandate agreement, Exhibit 10.43
§1.1 and §2.4(a)(ii): work-level rolling full receipts and qualifying actual
third-party net costs differ from the home-video payout proxy. The filed text
leaves crossing allocation, latching, reopening and simultaneous-event priority
unresolved. RR04 §4 and LD03 §6 select the split/reopen scenario below; no
professional approval or historical accounting reproduction is claimed.

[Official filed agreement](https://www.sec.gov/Archives/edgar/data/929351/000095012407004671/v33652exv10w43.htm)
and pinned reviewer/source references are retained in `neutral.json`.

One purchaser-produced eligible work, one seller group and USD are selected.
Work gate, aggregate hurdle and crossed-net pool have distinct explicit scopes.
The aggregate hurdle is an approved supplied attainment attestation effective
strictly before each period begins, observed before that frame's exclusive
cutoff. This method does not derive the aggregate hurdle. The approved crossed
net worksheet is separately supplied, scoped to its period/member set and
explicitly zero. Missing worksheet evidence is unknown and blocks; zero is not
inferred from an empty ledger. This method does not reconstruct crossed net.

Periods are half-open Gregorian dates at UTC midnight. Recognition uses the
later of an original receipt's received/credited Instant and earned Instant,
with explicit nonrefundable confirmation. Actual costs use their original
incurred Instant. Each event has an explicit approval/classification decision;
an excluded event remains in the original population and path with zero selected
effect. Eligible costs must be confirmed actual third-party amounts. Selected
cost is original gross less identified discounts, rebates, allowances, insurance
recoveries and Soft-Money reductions. Reductions cannot exceed gross. An original
line cannot also enter as a receipt, or be used twice under a new row ID.
This is a supplied classification/evidence check, not independent legal approval
of affiliate allocations, a general reserve policy or arbitrary refund handling.

Each frame supplies two approved complete populations, including complete-empty
views, covering all original receipt and cost IDs and their raw gross totals.
Their observations follow period end and all included original observations.
Original event observations must follow economic occurrence and precede the
exact cutoff. Evidence must be approved, correctly scoped/kinded, observed no
later than the record it supports and strictly before cutoff. Unknown/unused
evidence, missing classification and unmatched original identities block.

The complete original history begins at an explicit zero genesis with latch
false. Pre-period raw rows reconstruct opening receipts R and costs C. Within
each current period, economic Instants order events first, then an explicitly
authorized positive integer sequence. The ordering authority lists every event
and its actual time/sequence; unresolved complete-key ties block. Physical input
order, event ID and source file position never decide economic priority.
Original receipt/adjustment and classification identities cannot be replayed or
aliased. Exact submicrosecond Instants and explicit numeric UTC offsets are
compared without rounding or inferred timezones.

For the selected `split_reopen` method, a receipt of full amount a changes
surplus from s=R−C to s+a. Its admitted full receipt is
`max(0,s+a) − max(0,s)`. Costs update C and can close the gate again. Reaching
equality gives zero excess on that row. Home-video admission is then multiplied
by the original explicitly supplied proxy; ordinary admission stays full.
Gross candidate is gross rate times summed payout base. Baseline proxy is 50%
and gross rate 20%, both synthetic replacements for redacted source terms.
Fee offset and reserve movements are explicitly zero. All arithmetic uses exact
fractions, with no implicit cent rounding.

The following separately named finite alternatives are controls, not default
historical interpretations or additional owner-required universal methods.

| Method | Admission policy |
| --- | --- |
| `opening_gate` | Admit all current eligible receipts if opening R≥C |
| `closing_gate` | Admit all current eligible receipts if closing R≥C |
| `continuous_history` | Admit all current eligible receipts if opening and every current ordered prefix R≥C |
| `split_latch` | First positive recognized receipt reaching R≥C opens the latch; split that receipt, then admit full later receipts despite dips |
| `full_cross_reopen` | Admit the full receipt when its post-receipt surplus is positive; an equality-only row admits zero |
| `next_row_reopen` | Admit the full receipt only when pre-receipt surplus is nonnegative |

Latch state is false at zero genesis; empty 0/0 and zero receipts cannot open
it. Equality can open it only on a positive recognized receipt. Continuous
eligibility concerns the current period; complete earlier history reconstructs
opening rather than requiring that the work was always clear since genesis.
Opening/closing/continuous methods can depend on the chosen period grouping;
no universal split/merge or event-partition equivalence is claimed.

Q1 original cost100 followed by receipt80 reconstructs80/100. Q2 is
`[2008-04-01,2008-07-01)`, cutoff `2008-07-05T00:00:00Z`:

| Original ordered event | R / C afterward | Split admission | Payout base |
| --- | ---: | ---: | ---: |
| Apr10 ordinary receipt10 | 90 / 100 | 0 | 0 |
| Apr20 same Instant sequence1 home-video receipt30 | 120 / 100 | 20 | 10 |
| Apr20 sequence2 actual cost30 | 120 / 130 | 0 | 0 |
| May10 ordinary receipt10 | 130 / 130 | 0 | 0 |
| Jun10 ordinary receipt20 | 150 / 130 | 20 | 20 |

Payout base30 gives gross6. Split/latch gives8; full crossing/reopen7;
separately authorized reversal of Apr20 receipt/cost order4; opening-only0;
closing-only11. Both endpoint totals stay150/130. A separate original opening
110/100 followed by cost30 and receipt40 closes150/130: closing-only gives8,
while current-history continuous gross is inapplicable. Without that dip,
continuous eligibility gives8. Equality is allowed at a prefix but generates
no positive split excess itself.

Gross branch inapplicability, applicable computed zero and blocked/unknown
evidence are separate states. The independently valid zero net worksheet stays
observable if the work gross branch is inapplicable. Greater-of selection is
explicit; a valid gross0/net0 is a tie, while inapplicable gross leaves net as
the selected branch. Results are calculated unissued entitlement. No issue,
bank payment, bank-paid zero, withholding or reserve movement is created.

Serialized state pins scope/policy/registry/research and retains original facts,
per-frame cutoffs, financial results, consumed identities and cumulative
recognized entitlement. All historical financial results and the supplied
opening are replayed from originals. Periods must be adjacent, cutoffs increase
and actual predecessor summary must match the entire supplied closing state.
`source_case_id` identifies a calculation, not a canonical result digest;
external `result_ref`, if supplied, is separate provenance. The fixture's
`original_history` mode is disclosed supplied raw history, not a fabricated
actual predecessor. Separate tests use actual Q1→Q2→Q3 serialized results.
Q3 original cost30 then receipt20 opens150/130 and closes170/160, generating
only new split base10/gross2; cumulative recognized8 does not reearn Q2's6.

The initial profile admits at most four total periods, 32 economic events per
period, 64 records per supporting table and complete supplied views. There is
no late-history delta ingestion, amendment, negative raw receipt, general
reserve/interest/net-ledger derivation, payment execution or FX. Invalid facts
or state block atomically with no partial consumable output.
