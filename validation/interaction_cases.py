"""Finite configuration coverage for rounding, sign, aggregation and failure.

The controls use integer/Fraction arithmetic independently of SPL. Pair coverage
is over the declared 160 feasible input configurations, not all programs or all
contract policies. All 40 mode/stage/sign triples execute with a safe split
population; blocked cells cannot substitute for these financial controls.
"""
from fractions import Fraction
from itertools import combinations, product

from validation.generated_cases import exact_json

DOMAINS = {
    "mode": ("floor", "ceiling", "toward_zero", "half_even", "half_away_from_zero"),
    "stage": ("row", "aggregate"),
    "sign": ("positive", "negative", "mixed", "zero"),
    "partition": ("split", "merged"),
    "path": ("safe", "demanded_failure"),
}
NAMES = tuple(DOMAINS)
SOURCE = '''schedule RoundingInteractions language "spl/0.1-draft" core "spl-core/0.1-draft" schema "spl-data/0.1-draft" {
  input amounts: List<Money<USD>>;
  input row_rounding: Bool;
  input safe: Bool;
  opening balance: Money<USD> from "interactions/balance";
  define raw = sum(amounts, item => item * 0.5);
  define row_total = sum(amounts, item => quantize(item * 0.5, USD 0.01, MODE_LITERAL));
  define aggregate_total = quantize(raw, USD 0.01, MODE_LITERAL);
  define selected = if row_rounding then row_total else aggregate_total;
  emit "raw" = raw;
  emit "selected" = if safe then selected else USD 1 / 0.0;
  closing balance = balance + selected;
}
'''


def rounded(value, mode):
    """Exact independent cent rule, using absolute magnitude for both signs."""
    magnitude = abs(value) * 100
    whole, remainder = divmod(magnitude.numerator, magnitude.denominator)
    if mode == "floor":
        cents = whole + (value < 0 and remainder != 0)
    elif mode == "ceiling":
        cents = whole + (value > 0 and remainder != 0)
    elif mode == "toward_zero":
        cents = whole
    elif mode in ("half_even", "half_away_from_zero"):
        doubled = remainder * 2
        cents = whole + (doubled > magnitude.denominator or
                         doubled == magnitude.denominator and
                         (mode == "half_away_from_zero" or whole % 2 == 1))
    else:
        raise ValueError("unknown rounding mode")
    return Fraction(-cents if value < 0 else cents, 100)


def pairs(cell):
    return {(a, cell[a], b, cell[b]) for a, b in combinations(range(len(NAMES)), 2)}


def selected_cells():
    feasible = list(product(*DOMAINS.values()))
    # Stronger than pairwise for the money-changing core: all 40 safe triples.
    selected = [cell for cell in feasible if cell[3:] == ("split", "safe")]
    # Retain an actual split/merge discriminator for each selected rounding stage.
    selected += [("half_even", stage, "positive", "merged", "safe")
                 for stage in DOMAINS["stage"]]
    uncovered = set().union(*(pairs(cell) for cell in feasible))
    for cell in selected:
        uncovered.difference_update(pairs(cell))
    while uncovered:
        # Enumeration order resolves ties, making the covering set reproducible.
        best = max(feasible, key=lambda cell: len(pairs(cell) & uncovered))
        if not pairs(best) & uncovered:
            raise AssertionError("uncoverable feasible pair")
        selected.append(best)
        uncovered.difference_update(pairs(best))
    return selected


def coverage_contract():
    feasible = list(product(*DOMAINS.values()))
    selected = selected_cells()
    required = set().union(*(pairs(cell) for cell in feasible))
    covered = set().union(*(pairs(cell) for cell in selected))
    return {"format": "spl-rounding-interactions/1", "domains": DOMAINS,
            "feasible_configurations": len(feasible), "selected_configurations": len(selected),
            "required_pairs": len(required), "covered_pairs": len(covered),
            "uncovered_pairs": [list(row) for row in sorted(required - covered)],
            "required_safe_mode_stage_sign_triples": 40,
            "limitations": ["Pair counts describe supplied configuration values, not compiler branch coverage.",
                            "All 40 financial triples are safe; failed runs only cover demanded failure/discard.",
                            "Synthetic exact USD half-rate with fixed cent quantum; no canonical payment or contract approval."]}


def _amounts(sign, partition):
    amounts = {"positive": [Fraction(1, 100)] * 2,
               "negative": [Fraction(-1, 100)] * 2,
               "mixed": [Fraction(1, 100), Fraction(1, 100), Fraction(-1, 100)],
               "zero": []}[sign]
    return [sum(amounts, Fraction())] if partition == "merged" else amounts


def case_for(cell, seed=20261123):
    if tuple(cell) not in set(product(*DOMAINS.values())):
        raise ValueError("configuration outside finite domain")
    if type(seed) is not int or not 0 <= seed < 2 ** 32:
        raise ValueError("seed must be an integer in 0..2^32-1")
    mode, stage, sign, partition, path = cell
    amounts = _amounts(sign, partition)
    raw = sum(amounts, Fraction()) / 2
    row_total = sum((rounded(item / 2, mode) for item in amounts), Fraction())
    aggregate_total = rounded(raw, mode)
    selected = row_total if stage == "row" else aggregate_total
    safe = path == "safe"
    money = lambda value: {"value": exact_json(value), "currency": "USD"}
    return {"id": "interaction-" + "-".join(cell), "seed": seed,
            "features": ["rounding-sign-stage", "partition", "demanded-failure-atomicity"],
            "source": SOURCE.replace("MODE_LITERAL", '"' + mode + '"'),
            "bindings": {"inputs": {"amounts": list(map(money, amounts)),
                                     "row_rounding": stage == "row", "safe": safe},
                         "openings": {"balance": money(Fraction(1, 3))}},
            "expected": {"status": "calculated" if safe else "blocked",
                         "emissions": {"raw": exact_json(raw), "selected": exact_json(selected)} if safe else {},
                         "closing": {"balance": exact_json(Fraction(1, 3) + selected)} if safe else {},
                         "diagnostic_codes": [] if safe else ["DIVISION_BY_ZERO"]},
            "facts": {"configuration": dict(zip(NAMES, cell)), "amounts": list(map(exact_json, amounts)),
                      "rate": "0.5", "quantum": "0.01", "opening": exact_json(Fraction(1, 3)),
                      "row_total": exact_json(row_total), "aggregate_total": exact_json(aggregate_total)},
            "property": "Exact original rows with explicit cent mode/stage; demanded failure discards raw output and closing state."}


def generate_interaction_cases(seed=20261123):
    return [case_for(cell, seed=seed) for cell in selected_cells()]
