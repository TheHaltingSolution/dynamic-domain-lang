# RR03 canonical capacity measurement

The capacity harness exercises the checked-in synthetic RR03 original-record
generator against the unchanged `cases/sv/sv01.spl` schedule. It runs the
public canonical comparison workflow with `compact-v2`, followed by a separate
public consumer reload. Each close runs in a fresh Python process. This is a
serial, single-pool research workload.

## Reproduce

From a clean, short-path checkout on Windows, select the pinned Lean and run
the normal Lake build before collecting measurements. Use Python 3.12 and a
fresh evidence directory outside the checkout.

```powershell
$env:ELAN_HOME = 'C:\Projects\Film_TV_participation_dynamic_DSL\environment\elan'
$env:PATH = "$env:ELAN_HOME\bin;$env:PATH"
lake build
lake exe smoke
python -B scripts/spl_capacity.py --repeats 4 --output C:/path/to/new-evidence `
  --host-load-note 'Describe concurrent workloads and observed host conditions.'
```

The harness puts its own checkout first on Python's import path and passes the
pinned Lake `LEAN_PATH` to its children. The campaign records Git and build
identities before sampling and checks them again at the end. Keep source and
build outputs stable until it finishes. The documented command works with the
project's embedded Python by substituting its executable for `python`.

The first use of a target may include a compiler cache miss. The campaign
records compiler code generation, object compilation and linking then, and
excludes miss samples from cached-target summaries. Fresh processes and
output directories can reuse the compiled target and host filesystem cache.
Four repeats give three cached samples when the initial sample compiles, and
four when the target is cached before that size begins.

## Observations and controls

- The 100/1,000 records comprise 60/600 cash parents, 30/300 incurred costs,
  5/50 funding evidence events and 5/50 invoice parents. There are 2/8
  pictures, one bundle, one participant and one distributor. Exact two-way
  allocation produces 66/660 typed receipts. Invoice face values remain in
  their own amount space.
- The regular samples preserve the standard RR03 generator output and seed.
  The separately named `RR03-CARRY-2026/1` annual authority profile applies
  from Q1 through Q4. Each quarter has fresh cash, cost and invoice facts, a
  quarter-specific interpretation snapshot and the original cumulative
  funding roster with identical IDs, amounts and dates. The periods are
  consecutive half-open Gregorian quarters. The four closes contain
  385/3,850 distinct originals at the two sizes.
- The exact original-fact oracle runs before projection. For each close the
  harness checks all title and pool outputs, funding and cost projection,
  allocation and invoice ancestry, source dispositions and lineage, the
  original funding evidence IDs by picture, and reconciliation by amount
  space. It checks state and payment/issuance
  status against the independent expectations. The first close recovers
  USD 250 of remaining advance. The following closes recover USD 0. A
  successor takes only the predecessor's successful public reload state with
  `movement` removed, including its actual `prior_result_ref`.
- The API clock begins at reading the retained neutral input, includes binding
  and the full canonical call, and ends at the validated API return. The
  consumer clock covers the next public reload. Generation, independent
  oracle and independent reconciliation are outside these clocks. The
  stage observer retains transient reader logs, so its I/O overhead is
  included. Nested phase clocks are inclusive.
- The stage reports cover native audit, comparison target, reference and
  all five complete graph validations. These are execution validation,
  owned attachment, precommit publication, postcommit validated return and
  independent consumer reload. Publication and load timings include their
  respective integrity checks and I/O.
- Per-close memory is the coordinator process-lifetime peak working set.
  The process reports record individual children's peak working sets and
  applicable sampled guards. These figures exclude descendants and are
  separate measurements. Retained `sample.json` files also give original and
  bound input bytes, result bytes, compact wire and logical sizes, and
  node/edge counts.
- A failed close retains its observed process evidence and stops the sequence.
  Later samples are explicitly marked unexecuted. The campaign reports
  cached-sample counts, medians, nearest-rank p95 and maxima. At these small
  sample counts p95 is the observed maximum. The chain supplies period
  measurements and carry evidence. Its four dependent closes do not form a
  repetition distribution.

See `campaign.json` and the per-close `sample.json` files under the
evidence directory. Each close also retains its original package and batch,
the independent oracle, the canonical publication and the consumer logs.
