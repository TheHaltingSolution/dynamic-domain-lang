# Lean 4 reference library

Local library: `C:\Projects\Film_TV_participation_dynamic_DSL\reference\lean4`

These official upstream source checkouts contain prose and code examples,
readable and searchable offline. They are not rendered website mirrors and do
not need to be built to read them. Upstream licenses and attribution are retained.
Do not edit these reference copies as project code.

On Windows the programming guide uses a sparse checkout excluding
`examples/second-lake/greeting/Aux.lean`, because AUX is a reserved filename.
Its content remains in Git (`git show HEAD:examples/second-lake/greeting/Aux.lean`
from that checkout). All chapter prose is available in the working copy.

| Directory | Use | Published guide |
| --- | --- | --- |
| `reference-manual/` | Language behavior, modules, elaboration, tactics, macros, IO, Lake | [Lean 4.35.0 reference](https://lean-lang.org/doc/reference/4.35.0/) |
| `functional-programming/` | Data types, recursion, monads, IO, dependent types | [Functional Programming in Lean](https://lean-lang.org/functional_programming_in_lean/) |
| `theorem-proving/` | Propositions, proof terms, tactics, inductive types, induction | [Theorem Proving in Lean 4](https://lean-lang.org/theorem_proving_in_lean4/) |

Read each checkout's README to locate its chapters. In Verso books, prose is
embedded in `.lean` files; other editions may use Markdown or reStructuredText.
The reference chapters are in `reference-manual/Manual/`; programming chapters
are in `functional-programming/book/FPLean/`; the proof guide's book sources are
under `theorem-proving/book/`.

```powershell
rg --files C:\Projects\Film_TV_participation_dynamic_DSL\reference\lean4 -g '*.lean' -g '*.md' -g '*.rst'
rg -n 'induction|simp|Lake|lean_exe' C:\Projects\Film_TV_participation_dynamic_DSL\reference\lean4
```

## Guidance for agents

1. Read this repo's `lean-toolchain`, Lake configuration, and existing code first.
2. For implementation, start with the programming guide and matching reference.
   For compiler correctness, read the proof guide, then the reference sections on
   inductive types, tactic proofs, the simplifier, and proof validation.
3. The reference is pinned to `v4.35.0`, matching this repo. Tutorials are pinned
   to commits but may cover different Lean versions. The external `snapshot.json`
   records their build toolchains, which may also differ from example versions.
4. Prefer the matching reference over `latest`. Check APIs against the installed
   toolchain's `src/lean/` tree and compile examples with this repo's toolchain.
5. Keep calculation semantics pure and isolate IO. State source and target
   semantics and arithmetic, rounding, and input assumptions in correctness claims.
   Do not use `sorry` or custom axioms to make a proof pass.
6. Run `lake build`, `lake exe smoke`, and relevant new checks after code changes.

## Reproduce or refresh

Repository URLs and exact revisions are tracked in `docs/lean-resources.json`.
Populate or verify the local library from the repo root:

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File .\scripts\Sync-LeanDocs.ps1
```

The execution policy option applies only to that child process. The script
downloads missing checkouts, verifies existing revisions and clean working trees,
and records provenance in the external `snapshot.json`. It does not build books
or install their dependencies. Git and network access are needed on first run.
Use `-ProjectRoot 'D:\YourProject'` for another location.

To refresh, review upstream versions and update the manifest. Use a new project
folder or archive the old snapshots before downloading replacements. The script
never resets or deletes existing checkouts with mismatched revisions or edits.
