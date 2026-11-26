# dynamic-domain-lang

The [bounded research checkpoint](docs/spl/release-checkpoint-2026-11-25.md)
records the selected SPL profiles and capacity evidence. Start with
`AGENTS.md` and the [26 November session handoff](docs/spl/session-handoff-2026-11-26.md)
for the Readable SPL certification phase and its
[testing strategy](docs/spl/testing-strategy.md). The
[release reproduction guide](docs/spl/release-reproduction.md) gives the
frozen regression and native reserve commands.

Invoke `$royalties-participation` in a project conversation to try the
[royalties authoring skill](.agents/skills/royalties-participation/SKILL.md).
The [certification pilot](docs/spl/certification-pilot.md) explains the two
executable Readable SPL schedules, approval workflow, proof scope, and tests.

The [implemented feature inventory](docs/spl/release-feature-inventory.md)
defines the scope for general verification. The [verification guide](docs/spl/general-verification-design.md)
covers comparative kernel certificates, artifact-owned period series, and the
trusted native build. The [validation appendices](cases/validation/README.md)
show format-specific SPL rules linked into a Readable schedule.

Earlier completion work is tracked in the
[finite completion plan](docs/spl/completion-plan.md) and
[requirement backlog](docs/spl/completion-backlog.json), covering all 17 agreed
C1 calculation families plus performance and validation obligations. For the
external agents, use the paste-ready
[research](docs/spl/for-royalties-research-agent.md) and
[design](docs/spl/for-language-design-agent.md) notes.

The [active checkpoint](docs/spl/completion-checkpoint.md) records newer financial
slices, measured audit improvements and verification scopes. Current artifact
consumption uses the [validated completion contract](docs/spl/artifact-publication-design.md).

The [atomic variant inventory](docs/spl/c1-coverage.md) records the reviewed finite
semantic scope, separate backend/evidence axes and remaining gaps.
[Live work](docs/spl/active-work.md) records later checkpoints and active jobs.

Explicit [Minute/Hour conversion](docs/spl/unit-conversion-implementation.md)
is now integrated under owner feature `spl.usage-time/1`; the base dictionary
remains unchanged. Its frozen candidate passes931 tests, with46 additional main
integration checks. Native mixed currency remains reserved for the later tool
demonstration. The `0.4.3-dev` records below are historical baselines.

For a new implementation session, read the
[compiler session handoff](docs/spl/session-handoff.md) after `AGENTS.md`.

23 November 2026 continuation: the first
[bounded conformance campaign](docs/spl/conformance-validation.md) is implemented
and verified. It maps 12 supported variations and six explicit gaps, runs eight
generated cases through three backends and executes 14 existing witness methods.
The 19 new harness checks pass; the kernel baseline remains `0.4.3-dev`.

Research infrastructure for dynamic domain-specific languages, starting with
Screen Participation Language for film and television participation accounting.

The repository includes a native Lean SPL parser, checker, typed interpreter and
Lean emitter. It executes the bounded Skouras, RQ-07 and Lionsgate cases plus
registered synthetic allocation, ordered-fee, waterfall and correction methods.
Reusable functions, keyed collections and ordered folds support these additions.
The ordinary-royalty library adds selected marginal/whole-base tiers, cumulative
meters, caps and a separate nonrecoupable guarantee; its executable cases and
readable policy are in [cases/m1](cases/m1/README.md).
The M1b feature branch adds exact `Quantity<U>` and `Rate<U,USD>` inputs,
tagged outputs and dimension-safe state for the finite `spl.units/1` dictionary
(`Download`, `UsageMinute`). Its [synthetic Download demo](cases/quantities/README.md)
checks USD 150 gross, USD 75 participation, zero/fractional activity and actual
successor meter carry. It uses existing generic type syntax; no new literal
grammar was added. The verified local baseline is `0.4.3-dev` on
`feature/spl-typed-quantities`, based on merged `018dde1`. Its single combined
Python regression run passed all 352 tests; 16 native suites and all 35 review
paths also passed. `main` is unchanged; this local record includes no GitHub
release or push. The [historical `0.4.2-dev` record](docs/spl/baselines/implementation-0.4.2-dev.json)
is preserved.
See
[the implementation and demo instructions](docs/spl/implementation.md).
The initial toy compiler infrastructure remains separate from the Readable SPL
certification pilot and the broader compiler verification work.

Start with the executable [readable Skouras schedule](cases/sv/sv01-readable.spl)
or [readable Lionsgate schedule](cases/lg/lg01-readable.spl). Their financial
definitions come first and technical bindings follow. The
[phased development plan](docs/spl/development-plan.md) records the current
iteration, native typed IR/trace work, and policy/review questions.

## Setup and first run

Install Git and [Elan, Lean's toolchain manager](https://lean-lang.org/install/manual/).
The VS Code extension is `leanprover.lean4`; it provides editor support, while
Elan installs the compiler and Lake build tool. Open this repository folder in
VS Code, then open a fresh terminal after installation.

From the repository root:

```powershell
$env:ELAN_HOME = 'C:\Projects\Film_TV_participation_dynamic_DSL\environment\elan'
$env:PATH = "${env:ELAN_HOME}\bin;$env:PATH"
lean --version
lake build
lake exe smoke
lake exe participation
python scripts/quantity_demo.py
```

The quantity demo checks four cases against native interpretation, generated
Lean and independent financial controls. Its review artifacts are written to
the external project artifacts folder; use `--output` to choose another location.

`lean-toolchain` pins Lean to **4.35.0**. Elan installs that version when needed;
Lake comes with it. No separate C compiler installation was needed on the
Windows machine used to verify this setup.

Expected output from the executables:

```text
Lean smoke tests passed (compiler, generated module, and checked proof).
Lean infrastructure example: 33000
```

On this workstation, the toolchain lives in the project folder rather than the
Git repository. The commands above select it for the current PowerShell session.
Alternatively, `scripts\lean-shell.cmd` opens a Command Prompt with it selected;
pass a project folder as its first argument to use another location.
For a normal user-profile Elan installation on another machine, omit that step.

## Storage policy

Commit source code, proofs, small shareable fixtures, specifications, setup
scripts, dependency manifests, and toolchain version pins to this repository.
Keep installations, caches, large datasets, and local research material outside
Git under `C:\Projects\Film_TV_participation_dynamic_DSL`:

| Folder | Contents |
| --- | --- |
| `environment/elan/` | Elan, Lean toolchains, bundled native compiler, and standard libraries |
| `data/` | Large input datasets and local snapshots |
| `artifacts/` | Large experiment outputs, exports, and releases |
| `ResearchAgent/` | Existing research documents and supporting evidence |

Lake's disposable `.lake/` build products and downloaded package checkouts stay
beside the source but are ignored by Git. They can be recreated from the pinned
configuration. The `Generated/` directory currently holds a small tracked
example; large generated outputs belong in the external artifacts folder.

Local VS Code settings are ignored because they contain machine-specific paths.
This workstation sets the user `ELAN_HOME` to the project environment and uses
local VS Code settings for the extension and terminal PATH. Restart VS Code to
pick up user environment changes. Select the environment immediately in
an existing PowerShell terminal using the commands below:

```powershell
$env:ELAN_HOME = 'C:\Projects\Film_TV_participation_dynamic_DSL\environment\elan'
$env:PATH = "${env:ELAN_HOME}\bin;$env:PATH"
```

To recreate the external environment, install Elan with `ELAN_HOME` set to the
desired `environment/elan` path and run `lake build` from the repository. Elan
downloads the version pinned in `lean-toolchain`. CI uses its own temporary
environment and does not depend on these Windows paths.

## Initial structure

One Lake package keeps compiler, target runtime, proofs, and generated examples
on the same toolchain. These are separate Lean modules and library targets;
independently distributed packages can be introduced when needed.

| Location | Purpose |
| --- | --- |
| `Participation/Compiler.lean` | Toy source expressions, reference evaluator, and lowering |
| `Participation/Runtime.lean` | Pure target expressions and evaluation |
| `Participation/Proofs/CompilerCorrectness.lean` | Semantic preservation for every toy source expression |
| `Generated/Smoke.lean` | Handwritten placeholder for future emitted Lean modules |
| `Main.lean` | Executable wrapper for the target example |
| `Tests/Main.lean` | Kernel-checked examples and executable smoke checks |

`lake build` builds both libraries and both executables, including the proof
module. Warnings are errors. Commit `lake-manifest.json` alongside the toolchain
and Lake configuration; `.lake/` contains ignored build products.

## Verification direction

Official offline reference sources and introductory guides are indexed in
[docs/lean-resources.md](docs/lean-resources.md). Future agents should start
with [AGENTS.md](AGENTS.md). Downloads live outside Git under `reference/lean4`
in the project folder; exact source revisions are tracked in the repo.

The starter theorem states that evaluating any compiled toy expression gives
the same result as evaluating its source. Its proof uses structural induction,
with no `sorry`, custom axioms, or external proof packages. Lean's standard
libraries suffice for this initial setup. Mathlib can be added, pinned to a
compatible revision, when the mathematical model needs it.

This theorem verifies only the toy lowering. It does not verify the eventual
parser, type checker, Lean source emitter, native compiler, accounting policy,
or file I/O. The example amounts are smoke-test data, not contract calculations.

The intended research architecture follows the supplied *Screen Participation
Language Research Plan* (14 November 2026): contract syntax, a typed core with
independent semantics, Lean module generation, and a pure settlement function
behind an I/O wrapper. Future correctness statements should relate the core
semantics to generated calculations, with explicit assumptions about arithmetic,
rounding, and valid inputs. Generated artifacts have their own library here;
a separate generated-code package remains a later deployment decision.

## Screen Participation Language draft

The initial SPL language and compiler design is indexed in
[docs/spl/README.md](docs/spl/README.md). It includes the proposed language
reference, typed core and Lean compilation boundary, canonical data/run
contract, requirements and validation plan, and questions for the research
agent. This remains an evolving design draft. The bounded implementation and
its coverage limits are recorded in [implementation.md](docs/spl/implementation.md).
