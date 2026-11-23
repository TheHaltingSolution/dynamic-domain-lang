# Proposed Quest two-flow reconstruction

Policy DYN02-QUEST-TWOFLOW-NEAREST-EVEN@1 is a disclosed synthetic
`research_assumption`, with review status proposed. It selects only the additional
annual-target-return component in the Quest agreement's Schedule II late-payment
paragraph. Contract interpretation, owner acceptance of the adjacent patent-rights
domain, professional approval and the full combined liability remain unresolved.

The unchanged module-descriptor vocabulary records evidence class `synthetic`.
That transport classification maps to the more specific selected fixture label
`research_assumption` in the comparison output, with status `proposed`; neither
the registration nor this mapping supplies professional approval.

The [filed source agreement](https://www.sec.gov/Archives/edgar/data/824416/000121390025034342/ea023916001ex99-1_quest.htm)
is identified by
`sec-quest-agreement@sha256:9f1c535acfa79aaab13b860e18cd731936425e2d42ac519942d37451deeda151`,
locator `Schedule II, page 19, late-payment paragraph`. The original HTTP response
body retrieved on 23 November 2026 has 328902 bytes and SHA-256
`9f1c535acfa79aaab13b860e18cd731936425e2d42ac519942d37451deeda151`.
The [provenance index](source-index.json) records the external snapshot path;
the HTML body remains outside Git. Registration pins this actual source identity
and locator as parameter choices, independently of the proposed reconstruction.

Exactly one identified USD obligation, one actual full principal payment and
one matching application are supplied. The application date equals the actual
principal payment date; payment lies within the selected half-open period and
does not precede the due date. All supplied economic rows must retain the full
agreement/participant/pool/asset/currency scope. IDs, links and economic payment
identity must be unique. Partial or multiple flows block this selected method;
no allocation or liability rule is inferred for them.

Every supplied economic/calendar row references supplied evidence and is observed
strictly before cutoff. Every supplied evidence observation, including unused
supports, must also precede cutoff. Original due/payment dates are preserved.
The five ordinary Gregorian truth facts in `calendar-facts.json` are pinned by
identity, version, origin and source bytes. Supplied calendar observations must
match those facts. They contain no financial answer; checked SPL looks up both
endpoints and derives the whole elapsed days itself.

For principal P, annual target r and elapsed days d, the mathematical selected
additional charge before rounding is P*((1+r)^(d/365)-1). SPL uses a reusable
exact-rational bounded integer-power library and a finite cent search, without
a power/root/XIRR primitive or an irrational runtime scalar. The exact selected
charge is rounded once to USD 0.01 using half_even on the additional charge's
cent index. Even indices include both half-cent endpoints; odd indices exclude
both. A zero charge uses its nonnegative domain boundary explicitly.

The declared engineering domain is P>=USD 0.01, r>=0, integral 0<=d<=365 and
ceil(P*r/USD 0.01)<2^24. Exponentiation uses nine squaring slots for integral
exponents up to 365; cent selection uses 24 fixed search slots. Out-of-domain
inputs fail. These resource bounds are not agreement terms.

The baseline principal USD 1000, target 20% and 182 elapsed days gives selected
additional charge USD 95.17. The distinct minimum-cent-return alternative is
USD 95.18 and is retained only as bounding detail. Mandatory ties distinguish
half_even on the additional charge from half_away rounding and from rounding
the modeled terminal total before subtracting principal.

The actual principal payment remains a supplied separate fact. No additional
payment event is supplied or executed. Monthly status is `not_computed` and
combined status `unresolved_not_computed`; neither is encoded as numeric zero.
Outputs remain proposed, `research_assumption`, calculated and unissued. Exact
certificates establish the selected mathematical convention on this bounded
fixture; they do not establish a particular Excel implementation's convergence,
the complete Late Payment Charge or a new compiler correctness proof.
