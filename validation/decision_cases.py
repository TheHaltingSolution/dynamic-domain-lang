"""Finite independent decision tables; no compiler or oracle helper imports.

These cases enumerate named outcomes rather than sample a probability model.
The seed labels replay provenance; all mandatory decision combinations are kept.
"""

HEADER = 'schedule DecisionWitness language "spl/0.1-draft" core "spl-core/0.1-draft" schema "spl-data/0.1-draft" {\n'
BRANCH = HEADER + '''input take_then: Bool;
define selected = if take_then then USD 7 else USD 11;
emit "value" = selected;
}
'''
LAZY_BRANCH = BRANCH.replace('then USD 7', 'then USD 1 / 0.0')
BOOLEAN = HEADER + '''input and_left: Bool; input or_left: Bool;
emit "and" = and_left and (USD 1 / 0.0 > USD 0);
emit "or" = or_left or (USD 1 / 0.0 > USD 0);
}
'''
PRIORITY = HEADER + '''input high_match: Bool; input low_match: Bool; input fallback_safe: Bool;
define selected = choose priority {
  rule "high" priority 7 when high_match => USD 0;
  rule "low" priority 3 when low_match => USD 1 / 0.0;
  otherwise "fallback" => if fallback_safe then USD 10 else USD 1 / 0.0;
};
emit "value" = selected;
}
'''


def generate_decision_cases(seed=20261123):
    """Twelve exact cells over six source templates, with named scope limits."""
    if type(seed) is not int or not 0 <= seed < 2 ** 32:
        raise ValueError("seed must be an integer in 0..2^32-1")
    result = []

    def add(label, source, inputs, features, emissions=None, code=None):
        result.append({"id": "decision-" + label, "seed": seed, "features": features,
                       "source": source, "bindings": {"inputs": inputs, "openings": {}},
                       "expected": {"status": "blocked" if code else "calculated",
                                    "emissions": {} if code else emissions, "closing": {},
                                    "diagnostic_codes": [code] if code else []},
                       "facts": {"decision_cell": label, **inputs},
                       "property": "Independent finite decision table: " + label})

    add("then", BRANCH, {"take_then": True}, ["branch-then"], {"value": "7"})
    add("else", BRANCH, {"take_then": False}, ["branch-else"], {"value": "11"})
    add("lazy-else", LAZY_BRANCH, {"take_then": False}, ["branch-else", "unselected-failure"], {"value": "11"})
    add("demanded-then", LAZY_BRANCH, {"take_then": True}, ["branch-then", "demanded-failure"], code="DIVISION_BY_ZERO")
    add("boolean-skips", BOOLEAN, {"and_left": False, "or_left": True},
        ["and-short-circuit", "or-short-circuit"], {"and": False, "or": True})
    add("and-demanded", BOOLEAN, {"and_left": True, "or_left": True},
        ["and-demanded", "demanded-failure"], code="DIVISION_BY_ZERO")
    add("or-demanded-discard", BOOLEAN, {"and_left": False, "or_left": False},
        ["and-short-circuit", "or-demanded", "atomic-output-discard"], code="DIVISION_BY_ZERO")
    add("priority-zero", PRIORITY, {"high_match": True, "low_match": True, "fallback_safe": False},
        ["priority-zero", "unselected-failure"], {"value": "0"})
    add("priority-fallback", PRIORITY, {"high_match": False, "low_match": False, "fallback_safe": True},
        ["priority-fallback"], {"value": "10"})
    add("priority-body-fails", PRIORITY, {"high_match": False, "low_match": True, "fallback_safe": True},
        ["priority-selected-failure"], code="DIVISION_BY_ZERO")
    add("priority-tie", PRIORITY.replace('priority 3', 'priority 7'),
        {"high_match": True, "low_match": True, "fallback_safe": True},
        ["priority-tie", "bodies-not-demanded"], code="AMBIGUOUS_RULE")
    add("priority-no-match", PRIORITY.replace('  otherwise "fallback" => if fallback_safe then USD 10 else USD 1 / 0.0;\n', ''),
        {"high_match": False, "low_match": False, "fallback_safe": True},
        ["priority-no-match"], code="NO_APPLICABLE_RULE")
    return result
