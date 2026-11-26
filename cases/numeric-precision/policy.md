# Explicit ratio precision and statement rounding

`SYNTHETIC-NUMERIC-PRECISION-01` supplies six separately pinned synthetic
configurations for `B-NUM-PRECISION` (F02–F04). These are numerical development
policies, without professional contract approval, historical statement amendment
or payment authority.

The original expression retains its unit and exact expressed value. Percentage
12.345 means dimensionless Ratio0.12345. Selected precision of two percentage
decimal places corresponds to Ratio quantum0.0001; four decimal places of a
fraction also correspond to0.0001. Two fraction decimal places instead mean0.01.
Normalizing the rational value must not erase those distinct precision units.
Precision places are supplied policy metadata, not inferred from the number of
digits in an original value's spelling.

Ratio rounding occurs explicitly before applying the selected ratio to original
USD bases. Half-even maps0.12345 to0.1234; half-away-from-zero maps it to0.1235.
Original basis10000 therefore gives1234 or1235, while the unrounded-ratio control
is1234.5. The ratio delta remains dimensionless; its separate monetary effect is
reported in USD. A USD quantum is invalid for ratio precision.

Money has a separately supplied positive USD quantum, baseline0.01. Each original
basis0.01 at original Ratio0.5 derives an exact half-cent0.005. For two distinct
original lines, half-even row rounding yields0, while aggregate rounding yields
0.01. Half-away row rounding yields0.02, while aggregate rounding yields0.01.
These are separate operating policies, not equivalent transformations.

Supported modes are `floor`, `ceiling`, `toward_zero`, `half_even` and
`half_away_from_zero`. Nearest modes compare exact distance; half-even chooses
an even integer number of quanta at ties, and half-away chooses the candidate
farther from zero. Floor/ceiling have their mathematical signed meanings;
toward-zero truncates magnitude. Zero/negative quanta, wrong dimensions/currency
and unsupported modes reject. Signed ratios and original monetary bases are
deliberately admitted in this numerical profile; no implicit share range, loss
floor, cent default or rounding after every operation is introduced.

The statement retains each original line, exact basis, earnings before/after
ratio rounding, rounded display amount and monetary rounding delta. It also
retains exact totals, sum of rounded detail, aggregate control and selected
row/aggregate total. An explicit signed statement bridge is selected total
minus sum of rounded detail. It is not assigned silently to an original line.
Ratio-rounding and money-rounding bridges separately reconcile the original
exact earnings to the selected statement. Directed modes and signed cancellation
may require positive or negative statement bridges.

Original line IDs and original references remain distinct and unique; equal
contributors are not deduplicated. A supplied complete population identifies all
original IDs and signed USD basis total. Missing completeness is unknown and
blocks; complete-empty is known zero. Agreement, participant, pool, asset and USD
scope must match. Valid Unicode spellings and all original numeric records remain
unchanged. Exact decimal strings or normalized rational objects are admitted;
there are no binary floating-point amounts. Bounds are eight original lines,
one ratio expression and selected precision places0..6.

A supplied policy reference pins the exact supplied policy document by ID,
revision and canonical-content SHA256. Changing a mode, point or quantum under
the old pin rejects. An explicitly repinned document is a different supplied
configuration. This stateless API does not prove external registration,
authorization or immutable revision history; that requires a separately evidenced
registry/prior-registration boundary. It does not reject a repinned document
merely by pretending to know an absent earlier registration.

All results are unissued statement calculations. There is no state, bank
instruction, bank-paid-zero inference, reserve/allocation execution, FX or
professional approval. A later independent source author must establish actual
native types, mode-literal dispatch, canonical preparation/policy pins, complete
publication and cross-backend execution under unchanged resource guards.
