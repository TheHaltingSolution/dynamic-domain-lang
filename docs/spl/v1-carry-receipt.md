# Bounded receipt for existing v1 state

`load_completed_v1_carry_receipt(path)` returns an explicit `V1CarryReceipt`,
serialized as `spl-validated-v1-carry-receipt/1`. It partially extracts genuine
existing financial/state fields after complete owned-file, result-byte and
JSON-token validation. It is not a canonical result or a replacement audit.
The default `load_completed_result` and existing v1 artifacts stay unchanged.

The receipt records the old publication version/invocation, exact completion
and result SHA256/byte count, selected existing status/results/closing-state/
manifest/verification/result-digest values, and trace validation scope. It never
pretends an omitted audit is `trace: []`. The old result digest is copied
metadata; its semantic meaning is not re-proved by the receipt reader.

The incremental parser hashes the same open result bytes that it parses. It
keeps one trace node resident at a time and validates every skipped value,
including duplicate keys in nested objects, JSON number syntax/nonfinite
values, UTF8 encoding, escapes, truncation, trailing data and depth. Native
trace origin additionally requires unique node identities, earlier dependency
references and the native schema's detail references. Ordinary operand/result/
state records with reference-like field names are data. Reference or unknown
origins receive explicit token-only qualification and no new native credit.

All manifest entries, relative invocation ownership, file sizes/digests and
the unchanged final marker are checked. The new reader uses the existing
64 MiB result, 8 MiB marker, depth128, 100,000 observation and sampled Windows
256 MiB/60-second worker budgets. These are bounded child measurements, not
whole-parent or OS job limits. Selected existing finite-float metadata follows
the old v1 JSON interpretation; financial codecs are not relaxed.

`receipt.opening_cells()` requires actual `calculated`/`calculated_zero` status
and final manifest mode where supplied. It returns fresh copies of the source
cells, removing only output-only `movement` and retaining every original
quantity/key/boundary/scope/unit/prior-result reference. Malformed selected,
status, manifest or closing-cell shapes fail with `PublicationError`. The
public class is a data holder, not an authentication capability. A successor's
normal canonical source/terms/type/scope/state validation still applies.

## Actual old C10 evidence and separate compilation limit

The unchanged `/5` source has SHA256
`e9b76f271fcfe4b5ec6162eebe439bb9b1ab4b9bb9897f0f4021d34d910017c0`.
Its existing completed Q2 publication is retained in
`entitlement-burdens-checks-702907fd/actual/q2`. The ordinary whole-array v1
loader, when sampled under256 MiB, failed at276,561,920 bytes. That failure is
retained in `compact-c10-20261123-a/old-v1-preparation`.

The new receipt reader validates the same56,496,486 result bytes and all owned
files in5.036546 seconds at37,494,784 sampled peak bytes. It checks17,042 native
nodes and21,494 edges. The receipt is116,504 output bytes; this reduced output
is a declared partial extraction, not omitted audit credited as a full result.
Evidence is `compact-c10-v1-receipt-20261123-a`.

The old marker/result hashes are respectively
`a4f2e2842d7246fe0a70b0ca0f1e8b2bc654e1eb15b264e5dbf941cfbaa3b559`
and `b4daf31c2819be9b889bfa91197c6f3e55547794e5727630b7a3ac498b13b5a2`.
Actual extracted cells equal the archived Q3 opening cells, preserving
`result@sha256:ab6b784cd20f58c59421baf197ee119881725f8cef4429599191d03c1e2895df`.
Newly bound Q3 inputs/openings equal the archived original Q3 bindings exactly.
No old files were rewritten or retrospectively re-pinned.

This does not complete C10. Fresh opt-in Q1 audit/reader completed, but compiling
the unchanged204,897-byte emitted program exceeded the separate1 GiB/180-second
compiler profile at1,078,091,776 sampled bytes. One explicitly authorized
`compiler1g180-j1` diagnostic, adding only pinned Lean `--threads=1`, also failed
at1,078,087,680 bytes. Both failures remain retained. Q2/Q3/preview/full43 methods
were not executed, and no new C10 financial result or successor authority was
credited. No memory or audit budget was increased.
