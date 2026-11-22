# Lean development

Read [docs/lean-resources.md](docs/lean-resources.md) for official local Lean
references, introductory guides, version policy, and reproduction instructions.
The library is outside Git at
`C:\Projects\Film_TV_participation_dynamic_DSL\reference\lean4`.
If unavailable, use the published links in that index or populate it with the
provided script. Other workstations may use a different project path.

Use the pinned `lean-toolchain` and setup in README.md. Keep source, proofs,
configuration, small shareable fixtures, and documentation indexes in Git.
Keep toolchains, large datasets, and downloaded references in the external
project folder. `.lake/` is ignored disposable build output.

Check code changes with `lake build`, `lake exe smoke`, and relevant new checks.
Correctness proofs must have explicit scope and assumptions; do not introduce
`sorry` or custom axioms to satisfy them. The toy compiler proof is infrastructure,
not a proof of the future participation compiler.
