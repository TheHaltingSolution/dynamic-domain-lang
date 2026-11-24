# Bounded semantic mutation campaign

This disclosed development population implements the semantic-mutation portion
of the [test-quality plan](test-quality-plan.md). It is not a held-out evaluation,
global compiler adequacy score or historical contract interpretation. Policy
`SYNTHETIC-MUTATION-CONTROLS-01@1` is explicitly `research_assumption`.

Original unique scoped receipt contributions establish gross `G`; one original
approved cost establishes `C`. A complete original population attests the receipt
IDs/total. Supplied terms are fee rate `f`, share `s` and threshold `T`; original
opening state is a recognized-entitlement snapshot, not cash or bank payment.
Fee is fixed original gross `Gf`. Both cost and fee precede share. Eligibility is
`G >= T`; eligible entitlement `(G-C-Gf)s` is rounded once to cents using exact
half-even. Closing recognized entitlement is opening plus rounded current
entitlement. There is no interstage rounding, floor, cap, withholding or payment
inference. The bounded nonnegative domain requires rates/share in [0,1],
`C <= G` and `G-C-Gf >= 0`.

The four original-input cases are threshold equality (G1000/C500/f.1/s.8/open50),
just below (G999.99 with the same terms), and exact positive ties1.005/1.015
(cost/fee0, share1, threshold0, opening0). Equality gives fee100, after-cost500,
after-fee900, pre-share400, share320, rounded320 and closing370. A net fee gives
fee50 and entitlement360; a gross fee after share gives `500*.8-100 = 300`.
The below case retains share319.9928 as an intermediate but recognizes0 and
closes50. Ties recognize1.00 and1.02 respectively.

Phase `initial` retains exactly those four cases and its genuine high-gross
survivor. A separate `strengthened` phase preserves them unchanged and adds
original gross2000 and3000, with cost500, fee.1, share.8, threshold1000 and
opening50. The independent controls are fee200/pre-share1300/earned1040/closing1090
at2000, and fee300/pre-share2200/earned1760/closing1810 at3000. The unchanged
conditional-rate mutant still survives at2000 but recognizes1736 instead of1760
at3000. This deliberately directed second phase closes a known in-domain blind
spot; it is not held-out evidence. Both original corpus definitions and campaign
results remain separate, with remaining per-case survivors visible.

The independent standard-library oracle in `validation/semantic_mutations.py`
consumes originals, not parsed source, compiler bindings or emitted answers. It
owns all financial intermediates, the threshold, exact integer half-even rule,
original IDs/count and closing state. The source factory and mechanical binding
transport are separate functions, never called by the oracle. Every original
record, source byte, binding, expected amount and actual outcome is retained.

The finite mutant catalog has seven semantic alternatives: net fee base, fee
after share, strict threshold, double counting each original contribution,
dropping opening state, half-away rounding, and a conditional rate change only
above gross2000. That last alternative deliberately survives the declared inputs;
it needs a new witness outside this four-case population and is not called
equivalent. Parser and type errors are two separate invalid-source controls.
FX and quote-selection mutations have no executable source and remain reserved,
unexecuted for the later owner tool demonstration.

One additional mutation is equivalent only under an explicit pinned algebraic
certificate: `((G-C)-Gf)s = ((G-Gf)-C)s` over exact rationals. The fee depends on
original gross, both deductions precede the same share, there is no interstage
rounding/cap/floor or order-dependent fee, the same gate applies, and final
rounding/state use the same amount. Both disclosed after-cost and after-fee
views retain their original meanings. The certificate is bound to the exact
authored mutant source and policy. Equal sampled final totals alone never
establish equivalence; execution contradicting the certificate is an unresolved
control failure.

`scripts/spl_mutation_campaign.py --output <fresh-external-directory>` executes
reference, native IR interpreter, native-emitted Lean and separately
Python-emitted Lean. Each native source compiles/exports IR once; every selected
original case then executes each requested path. There is no implicit
reference-only environment fallback and no dependency rebuild. Flags, effective
requested backends, compiler/runtime pins and module origins are recorded.
Frontend-negative sources retain reference and native compilation diagnostics;
they receive no financial execution credit.
The hardened reporter requires an actual selected native frontend rejection,
including command identity and parsed static diagnostics. Native acceptance is
frontend disagreement; timeout, output limit, missing check or an unrelated
process failure is incomplete evidence. None can silently become an invalid-source
consistency result. Even a reserved-only selection needs complete baseline
backend agreement before the campaign completion status is issued.

For each mutant/case, all four baseline outcomes must first match every
independent expected intermediate and state. Missing backend, timeout, malformed
output, incomplete execution, wrong baseline control or backend disagreement is
unexecuted evidence. A parser/type rejection is invalid, not a killed financial
mutant. Complete agreeing calculations that differ materially are killed; equal
ones survive that case. Certified equivalence has its own category. The report
preserves per-case survivors, partial outcomes, stage and reason. It supplies
category counts without a global adequacy percentage.
Those counts are explicitly mutant-case pairs. Distinct mutant summaries keep
their own case counts and killed/surviving case IDs; a mutant killed in one case
does not erase its other surviving cases.

The deliberately weak comparator looks only at final current entitlement. It
misses the dropped-opening-state mutant because earned320 is unchanged while
closing falls from370 to320. The primary comparator includes every material
intermediate, original ID/count, status/diagnostics and closing state. Harness
controls deliberately introduce a wrong oracle, missing backend, contradictory
equivalence and invalid source to ensure they cannot become financial kills or
false passes.

Defaults are at most224 Lean subprocesses,30 seconds per process,300 seconds
campaign wall time and1MiB per stdout/stderr stream. Bounded pipe capture stops
oversized output; partial evidence remains labeled. Selection is limited to the
declared case/mutant IDs. Output must be fresh, with retained source snapshots,
original policies/inputs, raw stdout/stderr, source/target/IR files, outcomes and
classifications. Existing output is never reused as completion evidence. Source
or implementation pin drift makes the campaign partial. No source retuning or
golden changes are made in response to surviving mutants.

The first two frozen runs used identical source tree
`cd3fbbdc723716b2b5bf229b011d822816d355e688623dda0629087111652a19`,
compiler `20ea52ba37b7d84b4d5d7ed62c9c38b44a928cf1ffc2287f2bec358bda31c260`
and runtime `673bb0fe936c48a60c1cf5a1a265fb1d1f9f3cd432f380ee9b3011b7729dace9`,
with no source/implementation drift:

| Frozen phase | Original cases | Mutant-case classifications | Actual Lean processes | Wall time |
| --- | ---: | --- | ---: | ---: |
| initial | 4 | 12 killed,16 survived,4 equivalent,8 invalid,8 reserved/unexecuted | 128 | 222.016s |
| strengthened | 6 | 21 killed,21 survived,6 equivalent,12 invalid,12 reserved/unexecuted | 182 | 300.953s |

The strengthened run used an explicit420s campaign budget; all other limits and
all SPL/mutant/policy definitions remained unchanged. There were nine valid
sources including baseline: initial36 cases per backend (144 completed backend
outcomes), strengthened54 per backend (216). The remaining Lean processes are
compilation/IR export and the two native frontend-negative checks per phase.
Initially six distinct semantic mutants were killed in at least one case and
one survived all four. The strengthened corpus kills all seven in at least one
case, while retaining21 per-case survivors. One distinct algebraic-equivalence
control, two distinct invalid sources and two distinct reserved mutations are
separate categories, not additions to a financial kill denominator.

The original reports are retained externally at
`artifacts/spl/semantic-mutation-initial-20261123-013d80c1` and
`artifacts/spl/semantic-mutation-strengthened-20261123-51a3f0ce` beneath the external
project directory. Their initial invalid-source classification required only
reference rejection, a reporting weakness identified during read-only review.
The archived native compile records independently show exit1 and actual
`TYPE_MISMATCH`/`SYNTAX_ERROR` rejection in both phases. Those reports remain
unchanged. A subsequent bounded negative-only run under new harness source pins
enforces the stronger consistency prerequisite; it does not rewrite or rerun
the financial mutation population or invent new financial kills.
