# Certified pilot command workflow

Run from the checkout root with Python and the pinned Lean toolchain. The [setup instructions](../../../../README.md) locate the shared project environment. If `python` on this workstation resolves to the Windows Store alias, use `environment/python/python.exe` under the external project root. Run `lake build` before the first use. Give each agreement its own working directory outside Git, with a fresh output directory for each settlement period.

The executable profile has fixed templates for exactly two eligible USD receipts with distinct original IDs, a fixed 50% share, half-even rounding to cents and no opening state. The templates differ in whether rounding happens once on the aggregate or separately for each receipt. Eligibility and membership in the period or batch come from the participant's supplied facts. The same certified schedule can run on later inputs within its stated domain. Review or draft other agreements separately when their executable rules differ.

## Draft and preview

```text
python -m spl_compiler.royalties init WORKSPACE --rounding aggregate
python -m spl_compiler.royalties preview WORKSPACE SAMPLE.json
```

Use `--rounding row` for the per-receipt schedule. Use a new directory for `WORKSPACE`. Open `WORKSPACE/agreement.spl` and review its terms, the linked policy and inputs with the participant. Supply one or more sample files to `preview`. Each sample supplies two distinct, nonempty ASCII receipt IDs and exact USD values as decimal strings or normalized rational objects.

```json
{
  "receipts": [
    {"id": "receipt-1", "amount": "0.01"},
    {"id": "receipt-2", "amount": "0.01"}
  ]
}
```

The preview shows independent rounding alternatives in `half_even_usd_cents` and checks the interpreted draft against its selected alternative. Report the expected results and actual preview to the participant. Identify `review_sha256` and what the participant would approve, including the linked policy. Use approval and certification to unlock settlement runs.

## Record approval and compile

After the participant explicitly approves the current review and policy, use the approved digest from that review.

```text
python -m spl_compiler.royalties approve WORKSPACE REVIEW_SHA256
python -m spl_compiler.royalties compile WORKSPACE
```

The command records the selected review identity. The conversation records who authorized it and their actual instruction. If the compiler reports a problem, use its diagnostic and keep calculation and settlement claims at the stage actually reached.

## Settle and reload

```text
python -m spl_compiler.royalties run WORKSPACE PERIOD.json OUTPUT_DIR
python -m spl_compiler.royalties reload OUTPUT_DIR
```

Use the IDs and amounts from the original receipts in `PERIOD.json` with the same shape as the samples. From the reloaded result, check `status` is `calculated`, read the USD amount in `results.participation.value`, and inspect `closing_state` and `certificate`. The pilot calculation returns an empty closing state and the certificate identity checked for that run. Present any blocked result with the supplied diagnostics. Payment issuance is a separate participant action.
