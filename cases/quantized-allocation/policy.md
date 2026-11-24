# Quantized original-parent allocation

`SYNTHETIC-QUANTIZED-ALLOCATION-01`, revision `1`, is an explicit synthetic
`research_assumption`. It selects two named methods, with no default contract
interpretation, payment execution or claim about general Unicode collation.

For each independently identified original USD parent amount P, round P once to
a cent target T using exact half-even rounding. Allocation quotas use **T**,
not P. Preserve P, T and T-P independently. Each parent is rounded separately;
this is not rounding the aggregate of unrelated parents.

An approved allocation authority names the original parent ID and specific
upstream line, the complete original recipient IDs, and exactly one nonnegative
exact weight per recipient. The complete denominator W must be positive, even
when P is zero. Missing or unknown recipients, duplicated terms, zero W, an
unmatched source or missing authority block; there is no fallback recipient.

`exact_weights_largest_remainder` calculates exact cent quota
q_i = (100*T)*w_i/W, floor base b_i = floor(q_i), and fractional cent remainder
f_i = q_i-b_i. Residual cents R = 100*T-sum(b_i) satisfy 0 <= R < recipient count.
Rank by descending f_i, then ascending stable recipient ID; award one cent to
the first R recipients. The selected child amount is (b_i+award_i)/100.
All original weights, W, original-parent exact quotas P*w_i/W, target-based
exact shares T*w_i/W, bases, remainders, ranks and residuals remain available.

The stable-ID profile is the bounded case-sensitive ASCII subset
`[A-Za-z0-9][A-Za-z0-9_.:-]{0,63}`. Ascending ASCII lexical ordering resolves
equal remainders, including uppercase before lowercase. This policy explicitly
authorizes that identity order; physical row order never resolves a tie.

The baseline P=USD 0.01 with X/Y weights 1/1 gives T=.01, exact cent quotas
.5/.5, bases 0/0 and residual 1. X receives .01 and Y receives 0. The parent
remains an original fact, not another counted financial contribution alongside
its derived children.

The fractional discriminator P=.015 with X/Y weights 1/2 first rounds to T=.02.
Target quotas are .006666.../.013333... USD, so selected children are .01/.01.
The original-parent quotas .005/.01 are retained separately; independently
half-even rounding those original quotas would give 0/.01, a different method.

`authorized_supplied_cents` separately authorizes original supplied cent amounts
for every approved recipient. These must reference the same parent, be
nonnegative integral cents and sum exactly to T. They need not equal the
weight-derived allocation. The complete original weights remain present, and
their computed allocation is reported as an independent comparison. For P=.01
and equal weights, authorized X=0/Y=.01 is valid under this method while the
weight method gives X=.01/Y=0. Conservation alone cannot select the authority.

Authorities retain approved/recorded Dates and must be approved by the explicit
as-of Date, effective for the exact current period, and observed before the
exact Instant cutoff. Parent, recipient, weight, supplied-amount and evidence
observations must also precede that cutoff. Date-period inclusion is half-open.
Unused authorities and unmatched supplied child rows fail. No solved target,
rank, remainder or derived weighted child amount is accepted as a source field.

This finite profile has at most 8 recipients, 4 original parents per period,
and 8 historical periods replayed before the current period. Zero-valued parents
and weights are allowed subject to W>0. An explicit empty parent population
produces no child contributions; a missing recipient universe blocks.

State pins scope, policy/method, complete original recipient registry and the
original period history. Actual adjacent predecessor state is required. Original
parent IDs and specific upstream line references remain consumed across periods;
renaming the same upstream parent under a new row ID cannot create more value.
Historical cutoffs remain active during replay. Cross-scope carry, policy or
recipient amendments are outside this selected profile. Derived allocations are
accounting classifications, not evidence of cash paid.
