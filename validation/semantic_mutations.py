"""Finite synthetic mutation population and source-independent financial controls.

No compiler/parser/adapter imports. The oracle reads original facts and policy;
the separate source factory is never consulted by the financial calculation.
"""
from copy import deepcopy
from decimal import Decimal, localcontext
from fractions import Fraction
import hashlib
import re

BACKENDS = ("reference", "native_ir", "native_emitted", "python_emitted")
# Manually reviewed exact algebraic rewrite, pinned independently of execution.
CERTIFIED_BASELINE_SHA256 = "addd3979e4917fbeb578b474bc00dc88708f41f086e35c70faac2f35ae3432ca"
CERTIFIED_COMMUTED_SHA256 = "51c970d8a35ac781d529fbc129e02b53960c004cae997e82dccaa888ff51f96c"
POLICY = {"id": "SYNTHETIC-MUTATION-CONTROLS-01", "revision": "1",
          "fee_base": "original_gross", "cost_stage": "pre_share", "fee_stage": "pre_share",
          "threshold": "gross_at_least", "rounding": "half_even_cents_after_gate",
          "intermediate_rounding": "none", "floors_caps": "none", "fee_dependence": "fixed_original_gross",
          "state": "opening_recognized_entitlement_plus_current_rounded", "evidence_class": "research_assumption"}
SCOPE = {"agreement_id": "synthetic-mutation-agreement", "participant_id": "synthetic-participant",
         "pool_id": "synthetic-pool", "asset_id": "synthetic-title", "currency": "USD"}


def exact_json(value):
    if isinstance(value, Fraction):
        denominator = value.denominator
        for prime in (2, 5):
            while denominator % prime == 0:
                denominator //= prime
        if denominator != 1:
            return {"numerator": str(value.numerator), "denominator": str(value.denominator)}
        with localcontext() as context:
            context.prec = len(str(abs(value.numerator))) + len(str(value.denominator)) + 8
            text = format(Decimal(value.numerator) / Decimal(value.denominator), "f")
        return text.rstrip("0").rstrip(".") if "." in text else text
    if isinstance(value, dict):
        return {key: exact_json(child) for key, child in value.items()}
    if isinstance(value, (list, tuple)):
        return [exact_json(child) for child in value]
    return value


def _q(value):
    if type(value) is not str or not re.fullmatch(r"(?:0|[1-9][0-9]*)(?:\.[0-9]+|/[1-9][0-9]*)?", value):
        raise ValueError("MUTATION_EXACT_NONNEGATIVE_FACT")
    return Fraction(value)


def _half_even_cents(value):
    cents = value * 100
    whole, remainder = divmod(cents.numerator, cents.denominator)
    if 2 * remainder > cents.denominator or (2 * remainder == cents.denominator and whole % 2):
        whole += 1
    return Fraction(whole, 100)


def oracle(case, policy=POLICY):
    """All material amounts from original records; no source or binding access."""
    if policy != POLICY or case["scope"] != SCOPE or case["population"]["complete"] is not True:
        raise ValueError("MUTATION_SELECTED_POLICY_OR_COMPLETE_POPULATION")
    rows = case["receipts"]
    if type(rows) is not list or len(rows) > 4:
        raise ValueError("MUTATION_FINITE_RECEIPTS")
    ids, parents = set(), set()
    for row in rows:
        if row["scope"] != SCOPE or not row["id"] or row["id"] in ids or row["source_ref"] in parents:
            raise ValueError("MUTATION_ORIGINAL_CONTRIBUTION_IDENTITY")
        if not row["evidence_ref"] or not row["source_ref"] or not row["id"].isascii():
            raise ValueError("MUTATION_ORIGINAL_EVIDENCE")
        ids.add(row["id"]); parents.add(row["source_ref"])
    gross = sum((_q(row["amount"]) for row in rows), Fraction())
    if set(case["population"]["receipt_ids"]) != ids or _q(case["population"]["gross_total"]) != gross:
        raise ValueError("MUTATION_POPULATION_RECONCILIATION")
    cost = _q(case["cost"]["amount"])
    if case["cost"]["scope"] != SCOPE or not case["cost"]["source_ref"] or not case["cost"]["evidence_ref"]:
        raise ValueError("MUTATION_COST_LINEAGE")
    rate, share, threshold = (_q(case["terms"][key]) for key in ("fee_rate", "share", "threshold"))
    opening = case["opening"]
    if opening["scope"] != SCOPE or opening["purpose"] != "recognized_entitlement" or not opening["source_ref"]:
        raise ValueError("MUTATION_OPENING_SCOPE_PURPOSE")
    if not (rate <= 1 and share <= 1 and cost <= gross):
        raise ValueError("MUTATION_BOUNDED_NONNEGATIVE_POLICY")
    fee = gross * rate
    after_cost, after_fee = gross - cost, gross - fee
    pre_share = gross - cost - fee
    if pre_share < 0:
        raise ValueError("MUTATION_SIGNED_LOSS_OUTSIDE_PROFILE")
    share_amount = pre_share * share
    eligible = gross >= threshold
    unrounded = share_amount if eligible else Fraction()
    earned = _half_even_cents(unrounded)
    emissions = {"gross": gross, "cost": cost, "fee_base": gross, "fee": fee,
                 "after_cost": after_cost, "after_fee": after_fee, "pre_share": pre_share,
                 "share_amount": share_amount, "eligible": eligible, "unrounded_earned": unrounded,
                 "earned": earned, "contribution_count": Fraction(len(rows)), "original_ids": [row["id"] for row in rows]}
    return exact_json({"status": "calculated", "emissions": emissions,
                       "closing": {"balance": _q(opening["amount"]) + earned}, "diagnostic_codes": []})


def bindings(case):
    """Mechanical original-fact transport, independent from oracle expectations."""
    money = lambda raw: {"value": exact_json(_q(raw)), "currency": "USD"}
    return {"inputs": {"receipts": [{"id": row["id"], "amount": money(row["amount"]),
                       "asset": row["scope"]["asset_id"], "source_ref": row["source_ref"], "evidence_ref": row["evidence_ref"]}
                      for row in case["receipts"]], "cost": money(case["cost"]["amount"]),
                      "fee_rate": exact_json(_q(case["terms"]["fee_rate"])), "share": exact_json(_q(case["terms"]["share"])),
                      "threshold": money(case["terms"]["threshold"])},
            "openings": {"balance": money(case["opening"]["amount"])}}


def cases(phase="initial"):
    if phase not in {"initial", "strengthened"}:
        raise ValueError("MUTATION_CORPUS_PHASE")
    result = []
    definitions = [
        ("equality-stage-discriminator", ["600", "400"], "500", "0.1", "0.8", "1000", "50"),
        ("just-below-threshold", ["999.99"], "500", "0.1", "0.8", "1000", "50"),
        ("half-even-even-tie", ["1.005"], "0", "0", "1", "0", "0"),
        ("half-even-odd-tie", ["1.015"], "0", "0", "1", "0", "0")]
    if phase == "strengthened":
        definitions += [("at-high-rate-branch-boundary", ["2000"], "500", "0.1", "0.8", "1000", "50"),
                        ("beyond-high-rate-branch-boundary", ["3000"], "500", "0.1", "0.8", "1000", "50")]
    for identity, amounts, cost, rate, share, threshold, opening in definitions:
        rows = [{"id": identity + "-receipt-" + str(i), "scope": deepcopy(SCOPE), "amount": amount,
                 "source_ref": "original-ledger:" + identity + "#" + str(i), "evidence_ref": "synthetic-complete-view:" + identity}
                for i, amount in enumerate(amounts)]
        result.append({"id": identity, "scope": deepcopy(SCOPE), "receipts": rows,
            "population": {"id": "population:" + identity, "complete": True, "receipt_ids": [row["id"] for row in rows],
                           "gross_total": str(sum(map(Fraction, amounts)))},
            "cost": {"id": identity + "-cost", "scope": deepcopy(SCOPE), "amount": cost,
                     "source_ref": "original-cost-ledger:" + identity + "#1", "evidence_ref": "synthetic-approved-cost:" + identity},
            "terms": {"fee_rate": rate, "share": share, "threshold": threshold},
            "opening": {"id": "opening:" + identity, "scope": deepcopy(SCOPE), "amount": opening,
                        "purpose": "recognized_entitlement", "source_ref": "supplied-original-opening:" + identity},
            "payment_status": "not_assessed_calculated_entitlement_only"})
    return result


def source(variant="baseline"):
    gross = "sum(receipts, row => row.amount)"
    fee_base, effective_rate = "gross", "fee_rate"
    pre_share, raw = "after_cost - fee", "share_amount"
    comparator, rounding, closing = ">=", "half_even", "balance + earned"
    if variant == "fee-base-net": fee_base = "after_cost"
    if variant == "fee-after-share": pre_share, raw = "after_cost", "share_amount - fee"
    if variant == "strict-threshold": comparator = ">"
    if variant == "double-contribution": gross = "sum(receipts, row => row.amount + row.amount)"
    if variant == "drop-opening-state": closing = "earned"
    if variant == "half-away-rounding": rounding = "half_away_from_zero"
    if variant == "uncovered-high-gross-rate": effective_rate = "if gross > USD 2000 then fee_rate + 0.01 else fee_rate"
    if variant == "commuted-exact-pre-stages": pre_share = "after_fee - cost"
    if variant == "invalid-type": fee_base = "true"
    text = '''schedule SemanticMutation language "spl/0.1-draft" core "spl-core/0.1-draft" schema "spl-data/0.1-draft" {
  input receipts: List<{id:Id<Contribution>,amount:Money<USD>,asset:Id<Asset>,source_ref:Text,evidence_ref:Text}>;
  input cost: Money<USD>;
  input fee_rate: Ratio;
  input share: Ratio;
  input threshold: Money<USD>;
  opening balance: Money<USD> from "recognized-entitlement";
  define gross = GROSS;
  define after_cost = gross - cost;
  define fee_base = FEEBASE;
  define effective_rate = EFFECTIVERATE;
  define fee = fee_base * effective_rate;
  define after_fee = gross - fee;
  define pre_share = PRESHARE;
  define share_amount = pre_share * share;
  define eligible = gross COMPARATOR threshold;
  define unrounded_earned = if eligible then RAW else USD 0;
  define earned = quantize(unrounded_earned, USD 0.01, "ROUNDING");
  closing balance = CLOSING;
  emit "gross" = gross;
  emit "cost" = cost;
  emit "fee_base" = fee_base;
  emit "fee" = fee;
  emit "after_cost" = after_cost;
  emit "after_fee" = after_fee;
  emit "pre_share" = pre_share;
  emit "share_amount" = share_amount;
  emit "eligible" = eligible;
  emit "unrounded_earned" = unrounded_earned;
  emit "earned" = earned;
  emit "contribution_count" = sum(receipts, row => 1);
  emit "original_ids" = map(receipts, row => row.id);
}
'''
    for key, value in {"GROSS": gross, "FEEBASE": fee_base, "EFFECTIVERATE": effective_rate, "PRESHARE": pre_share,
                       "COMPARATOR": comparator, "RAW": raw, "ROUNDING": rounding, "CLOSING": closing}.items():
        text = text.replace(key, value)
    return text.replace("input cost:", "input cost") if variant == "invalid-syntax" else text


def source_hash(text):
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def mutants():
    result = [{"id": identity, "source": source(identity), "kind": "semantic"} for identity in (
        "fee-base-net", "fee-after-share", "strict-threshold", "double-contribution", "drop-opening-state",
        "half-away-rounding", "uncovered-high-gross-rate")]
    result += [{"id": "commuted-exact-pre-stages", "source": source("commuted-exact-pre-stages"), "kind": "equivalent",
                "certificate": "exact-fixed-gross-prestage-commutation/1", "baseline_source_sha256": CERTIFIED_BASELINE_SHA256,
                "mutant_source_sha256": CERTIFIED_COMMUTED_SHA256}]
    result += [{"id": identity, "source": source(identity), "kind": "frontend_negative"} for identity in ("invalid-type", "invalid-syntax")]
    result += [{"id": identity, "source": None, "kind": "reserved", "reason": "FX/quote mutation reserved for later owner tool demonstration; not executed"}
               for identity in ("fx-conversion-reserved", "quote-selection-reserved")]
    return result


def population(phase="initial"):
    return {"version": "spl-semantic-mutation-population/1", "phase": phase, "policy": deepcopy(POLICY), "cases": cases(phase),
            "baseline": {"id": "baseline", "source": source()}, "mutants": mutants(),
            "required_backends": list(BACKENDS), "disclosure": "finite disclosed development population, not held-out or global adequacy"}


def differences(expected, actual, prefix=""):
    if isinstance(expected, dict) and isinstance(actual, dict):
        paths = []
        for key in sorted(expected.keys() | actual.keys()):
            path = prefix + "." + key if prefix else key
            if key not in expected or key not in actual:
                paths.append(path)
            else:
                paths.extend(differences(expected[key], actual[key], path))
        return paths
    return [] if expected == actual else [prefix]


def classify(mutant, expected, baseline, outcomes, *, validation=None, required_backends=BACKENDS, policy=POLICY):
    """A financial classification needs a complete, correct baseline and backends."""
    result = {"classification": "unexecuted", "stage": "evidence", "reason": "", "differences": {}, "weak_final_only_survives": None}
    if mutant["kind"] == "reserved":
        return {**result, "stage": "reserved", "reason": mutant["reason"]}
    if not required_backends or set(required_backends) != set(BACKENDS):
        return {**result, "reason": "required backend population changed or missing"}
    for backend in required_backends:
        observed = baseline.get(backend, {})
        if observed.get("execution") != "completed" or observed.get("observable") != expected:
            return {**result, "reason": "baseline independent-control/backend prerequisite failed: " + backend}
    if validation and validation.get("status") == "invalid":
        native = validation.get("native_frontend_observation", {})
        if native.get("status") == "accepted":
            return {**result, "stage": "frontend_disagreement", "reason": "reference rejected source but native compilation accepted"}
        rejected = (native.get("status") == "rejected" and native.get("execution") in {"completed", "process_failed"}
                    and type(native.get("command_id")) is str and bool(native["command_id"])
                    and bool(native.get("diagnostic_codes"))
                    and set(native["diagnostic_codes"]) <= {"TYPE_MISMATCH", "SYNTAX_ERROR"})
        if not rejected:
            return {**result, "stage": "frontend_incomplete", "reason": "native frontend rejection missing or incomplete: " + native.get("reason", native.get("execution", "missing check"))}
        return {**result, "classification": "invalid", "stage": "frontend_consistency", "reason": "reference and actual native frontend reject; no financial execution credit",
                "frontend_diagnostics": {"reference": validation["reason"], "native": native["diagnostic_codes"]}}
    for backend in required_backends:
        observed = outcomes.get(backend, {})
        if observed.get("execution") != "completed" or not isinstance(observed.get("observable"), dict):
            return {**result, "reason": "missing/incomplete mutant backend: " + backend,
                    "partial_observations": {key: value for key, value in outcomes.items()}}
    actual = outcomes[required_backends[0]]["observable"]
    if any(outcomes[backend]["observable"] != actual for backend in required_backends):
        return {**result, "reason": "mutant backends disagree; not a financial mutation classification"}
    paths = differences(expected, actual)
    result.update(stage="calculation", differences={backend: paths for backend in required_backends},
                  weak_final_only_survives=actual.get("emissions", {}).get("earned") == expected["emissions"]["earned"])
    if mutant["kind"] == "equivalent":
        certified = (policy == POLICY and mutant["id"] == "commuted-exact-pre-stages"
                     and mutant.get("certificate") == "exact-fixed-gross-prestage-commutation/1"
                     and mutant.get("baseline_source_sha256") == CERTIFIED_BASELINE_SHA256 == source_hash(source())
                     and mutant.get("mutant_source_sha256") == CERTIFIED_COMMUTED_SHA256 == source_hash(mutant["source"]))
        if not certified:
            return {**result, "classification": "invalid", "stage": "equivalence_definition", "reason": "certificate/source/policy assumptions do not match"}
        if paths:
            return {**result, "classification": "unexecuted", "reason": "certified equivalence contradicted by execution; investigate"}
        return {**result, "classification": "equivalent", "reason": "pinned algebraic commutation certificate under exact fixed-gross pre-stages; not inferred from samples"}
    return {**result, "classification": "killed" if paths else "survived",
            "reason": "material observable/state mismatch" if paths else "survived this original-input case; no global equivalence inferred"}
