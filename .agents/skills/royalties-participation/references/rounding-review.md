# Review example for royalty rounding

The participant proposes a 50% share of two USD receipts for one royalty batch. The share and this batch are agreed for the example. The participant still needs to choose when to round. The two original receipt IDs are distinct. These are synthetic facts.

| Original receipt ID | Eligible dollars | Exact 50% share |
| --- | ---: | ---: |
| `receipt-1` | USD 0.01 | USD 0.005 |
| `receipt-2` | USD 0.01 | USD 0.005 |

Both alternatives round to cents and resolve a tie toward the even number of cents. These expected values follow from the two receipts and the stated rule, so they can be compared independently with the preview.

| Rule for the participant to review | Calculation | Royalty |
| --- | --- | ---: |
| Round each receipt's royalty, then add | `round(0.005) + round(0.005) = 0.00 + 0.00` | USD 0.00 |
| Add the exact royalties, then round | `round(0.005 + 0.005) = round(0.010)` | USD 0.01 |

Ask which rule the parties intend and which agreement clause or participant instruction supports it. The pilot can certify either choice for exactly two eligible USD receipts with a fixed 50% share and an empty opening state. The supplied independent [numeric controls](../../../../cases/numeric-precision/README.md) cover both alternatives alongside other rounding modes.

Walk through the selected authored schedule, either [aggregate rounding](../../../../cases/certification/aggregate-readable.spl) or [per-receipt rounding](../../../../cases/certification/row-readable.spl). Review the linked `money-rounding@1` policy along with the exact schedule in the participant's workspace. Confirm which agreement or instruction supplies the batch and eligible receipts. Those choices determine the inputs to the calculation.

## Conversation acceptance checks

Run these checks in a project conversation with `$royalties-participation`. Use synthetic facts in their own scratch output directory and follow the [command workflow](commands.md) when the conversation reaches that stage. Check decisions and artifacts rather than matching phrasing.

1. Start with “Help us set up participation royalties.” The reply describes drafting, review and approval before compilation, then asks for the relevant clauses or terms.
2. Supply “We pay one participant 50% on each batch of eligible USD receipts. The two sample receipts are one cent each. Round half-even to cents.” The reply identifies rounding placement as unresolved, distinguishes the USD 0.00 and USD 0.01 outcomes, and asks which rule governs.
3. Choose aggregation and ask to see its consequences. The reply identifies the placement and share in the proposed Readable SPL and policy, checks that the certified pilot scope fits, and shows a preview of USD 0.01 with its draft identity. Final compilation remains gated during review.
4. Say “The example looks right. Show me what would happen on the next batch.” Expect another calculation or preview and a request for explicit approval of the reviewed draft before compilation. Then explicitly approve that identity and its linked policy. Confirm the compiled artifact and verification receipt correspond to the reviewed identity. Run a later batch with distinct original receipts of USD 0.10 and USD 0.12 and observe USD 0.11 and empty closing state, independently derived as `(0.10 + 0.12) × 0.50`.
5. After approving aggregation, request per-receipt rounding. Expect a different authored schedule, a preview of USD 0.00 on the two one-cent receipts, and a fresh approval tied to the new review identity.
6. In a separate review, ask for a third receipt. Expect the skill to document the requested term and show its effect where calculable, and identify the missing support in the pilot profile. A three-receipt schedule remains a draft.
