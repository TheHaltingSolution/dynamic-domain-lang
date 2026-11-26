"""Reproducible neutral facts and independent exact controls for a small domain.

This is a development corpus, not held-out evaluation. The oracle uses only
standard-library Fraction arithmetic and integer comparisons. It imports no SPL
parser, evaluator, codecs, rounding helpers, or implementation financial logic.
The one authored SPL template intentionally permits compilation once per run.
"""
from __future__ import annotations

from decimal import Decimal, localcontext
from fractions import Fraction
import random


DEFAULT_SEED = 20261123
MIN_CASES = 8
MAX_CASES = 64
SOURCE = '''schedule GeneratedBoundaries language "spl/0.1-draft" core "spl-core/0.1-draft" schema "spl-data/0.1-draft" {
  input amounts: List<Money<USD>>;
  input threshold: Money<USD>;
  input round_value: Money<USD>;
  input observed: Instant;
  input cutoff: Instant;
  input safe_branch: Bool;
  input authorized: Bool;
  opening balance: Money<USD> from "generated/balance";
  define total = sum(amounts, item => item);
  define reached = total >= threshold;
  define included = observed < cutoff;
  define rounded = quantize(round_value, USD 0.01, "half_away_from_zero");
  define selected = if safe_branch then total else USD 1 / 0.0;
  closing balance = balance + total;
  emit "total" = total;
  emit "reached" = reached;
  emit "included" = included;
  emit "rounded" = rounded;
  emit "selected" = selected;
  require authorized else "GENERATED_AUTHORITY_REQUIRED";
}
'''


def exact_json(value: Fraction) -> str | dict[str, str]:
    """Encode an exact control without importing implementation transport code."""
    remainder = value.denominator
    for prime in (2, 5):
        while remainder % prime == 0:
            remainder //= prime
    if remainder != 1:
        return {"numerator": str(value.numerator), "denominator": str(value.denominator)}
    with localcontext() as context:
        context.prec = len(str(abs(value.numerator))) + len(str(value.denominator)) + 8
        decimal = Decimal(value.numerator) / Decimal(value.denominator)
        text = format(decimal, "f")
    return text.rstrip("0").rstrip(".") if "." in text else text


def _money(value: Fraction) -> dict:
    return {"value": exact_json(value), "currency": "USD"}


def _half_away_cents(value: Fraction) -> Fraction:
    # For absolute value measured in cents, floor(x + 1/2) selects the
    # nearest integer with an exact half always moving away from zero.
    magnitude = abs(value) * 100 + Fraction(1, 2)
    cents = magnitude.numerator // magnitude.denominator
    return Fraction(-cents if value < 0 else cents, 100)


def _case(index, seed, label, amounts, threshold, rounding, tick, opening,
          *, safe=True, authorized=True):
    total = sum(amounts, Fraction())
    # Both timestamps have identical whole seconds; integer 10^-7 ticks
    # independently establish the strict before relation without parsing ISO.
    observed = f"2026-07-03T00:00:00.{tick:07d}Z"
    cutoff = "2026-07-03T00:00:00.0000002Z"
    code = ("DIVISION_BY_ZERO" if not safe else
            "GENERATED_AUTHORITY_REQUIRED" if not authorized else None)
    expected = {"status": "blocked" if code else "calculated",
                "emissions": {}, "closing": {},
                "diagnostic_codes": [code] if code else []}
    if not code:
        expected["emissions"] = {"total": exact_json(total),
                                 "reached": total >= threshold,
                                 "included": tick < 2,
                                 "rounded": exact_json(_half_away_cents(rounding)),
                                 "selected": exact_json(total)}
        expected["closing"] = {"balance": exact_json(opening + total)}
    return {"id": f"generated-{index:03d}-{label}", "seed": seed,
            "features": ["exact-sum", "threshold-at-least", "strict-instant-cutoff",
                         "signed-half-away", "branch-laziness", "atomic-state"],
            "source": SOURCE,
            "bindings": {"inputs": {"amounts": [_money(x) for x in amounts],
                                     "threshold": _money(threshold),
                                     "round_value": _money(rounding),
                                     "observed": observed, "cutoff": cutoff,
                                     "safe_branch": safe, "authorized": authorized},
                         "openings": {"balance": _money(opening)}},
            "expected": expected,
            "facts": {"amounts": [exact_json(x) for x in amounts],
                      "threshold": exact_json(threshold),
                      "round_value": exact_json(rounding),
                      "observed_tick": tick, "cutoff_tick": 2,
                      "tick_seconds": "0.0000001", "opening": exact_json(opening),
                      "safe_branch": safe, "authorized": authorized},
            "property": ("Exact sum and closing balance; >= threshold; strict < cutoff; "
                         "round once to USD .01 half away; unselected division is lazy; "
                         "any demanded failure returns no emissions or closing state.")}


def generate_cases(seed: int = DEFAULT_SEED, count: int = MIN_CASES) -> list[dict]:
    """Return eight mandatory boundaries followed by seeded bounded samples.

    Count is 8..64, seed is an integer in 0..2^32-1. Amount lists have at most
    five entries, each between USD 0 and 1,000; thresholds are within USD 1
    of their sum, and the rounding probe is between USD -20 and 20. Exact
    thirds in the fixed corpus check rational transport as well as summation.
    Unsupported source forms, canonical package validation, dimensional values,
    payment semantics and emitted target branch coverage are outside this set.
    """
    if type(seed) is not int or not 0 <= seed < 2 ** 32:
        raise ValueError("seed must be an integer in 0..2^32-1")
    if type(count) is not int or not MIN_CASES <= count <= MAX_CASES:
        raise ValueError(f"count must be an integer in {MIN_CASES}..{MAX_CASES}")
    rng = random.Random(seed)
    base = Fraction(rng.randint(2, 100))
    opening = Fraction(rng.randint(0, 1000), 10)
    specifications = [
        ("below-before", [base - 1], base, Fraction("1.004"), 1, {}),
        ("equal-at", [base], base, Fraction("1.005"), 2, {}),
        ("above-after", [base + 1], base, Fraction("1.006"), 3, {}),
        ("negative-tie", [Fraction(1, 3), Fraction(2, 3)], Fraction(1), Fraction("-1.005"), 1, {}),
        ("empty", [], Fraction(), Fraction(), 2, {}),
        ("rational-sum", [Fraction(1, 3), Fraction(1, 3)], Fraction(1), Fraction("-1.004"), 3, {}),
        ("authority-block", [base], base, Fraction("1.005"), 1, {"authorized": False}),
        ("demanded-failure", [base], base, Fraction("1.005"), 1, {"safe": False}),
    ]
    while len(specifications) < count:
        amounts = [Fraction(rng.randrange(0, 100001), 100) for _ in range(rng.randrange(0, 6))]
        threshold = sum(amounts, Fraction()) + Fraction(rng.choice((-1, 0, 1)), 100)
        specifications.append(("seeded", amounts, threshold,
                               Fraction(rng.randint(-20000, 20000), 1000),
                               rng.choice((1, 2, 3)), {}))
    return [_case(index, seed, label, amounts, threshold, rounding, tick, opening, **flags)
            for index, (label, amounts, threshold, rounding, tick, flags) in enumerate(specifications)]
