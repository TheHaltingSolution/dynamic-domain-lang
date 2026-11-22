"""Independent exact controls for the selected Download participation policy.

This consumes neutral source records, not compiler bindings or projections.
The supplied usage view is restricted to one half-open period and observations
strictly before cutoff. Counts/rates are nonnegative in this case; those rules
do not restrict every possible dimensional value in the language.
"""
from datetime import date
from fractions import Fraction
import re


class QuantityOracleError(ValueError):
    pass


def _need(condition, code):
    if not condition:
        raise QuantityOracleError(code)


def _exact(value):
    _need(type(value) in {int, str}, 'EXACT_VALUE_REQUIRED')
    if isinstance(value, str):
        _need(re.fullmatch(r'-?(?:0|[1-9][0-9]*)(?:\.[0-9]+|/[1-9][0-9]*)?', value) is not None,
              'EXACT_VALUE_REQUIRED')
    return Fraction(value)


def _day(value):
    _need(type(value) is str and re.fullmatch(r'[0-9]{4}-[0-9]{2}-[0-9]{2}', value), 'INVALID_DATE')
    try:
        result = date.fromisoformat(value)
    except ValueError:
        raise QuantityOracleError('INVALID_DATE') from None
    return result


def _instant(value):
    _need(type(value) is str, 'INVALID_INSTANT')
    match = re.fullmatch(r'([0-9]{4}-[0-9]{2}-[0-9]{2})T([0-9]{2}):([0-9]{2}):([0-9]{2})(\.[0-9]+)?(Z|[+-][0-9]{2}:[0-9]{2})', value)
    _need(match is not None and match[6] != '-00:00', 'INVALID_INSTANT')
    hours, minutes, seconds = map(int, match.group(2, 3, 4))
    _need(hours < 24 and minutes < 60 and seconds < 60, 'INVALID_INSTANT')
    zone = match[6]
    offset = 0
    if zone != 'Z':
        zh, zm = int(zone[1:3]), int(zone[4:])
        _need(zh < 24 and zm < 60, 'INVALID_INSTANT')
        offset = (zh * 3600 + zm * 60) * (1 if zone[0] == '+' else -1)
    fraction = Fraction('0' + match[5]) if match[5] else Fraction()
    return Fraction(_day(match[1]).toordinal() * 86400 + hours * 3600 + minutes * 60 + seconds - offset) + fraction


def _identities(rows, field):
    _need(type(rows) is list, 'RECORD_LIST_REQUIRED')
    identities = []
    for row in rows:
        identity = row[field]
        _need(type(identity) is str and bool(identity), 'IDENTITY_REQUIRED')
        identities.append(identity)
    _need(len(set(identities)) == len(identities), 'DUPLICATE_IDENTITY')


def _calculate(data):
    _need(data['schema_version'] == 'quantity-neutral/1', 'UNSUPPORTED_NEUTRAL_SCHEMA')
    scope, terms, opening = data['scope'], data['terms'], data['opening_state']
    _need(set(scope) == {'contract_id', 'participant_id', 'pool_id', 'asset_id', 'currency', 'unit'}, 'SCOPE_REQUIRED')
    _need(all(type(value) is str and value for value in scope.values()), 'SCOPE_REQUIRED')
    _need(scope['unit'] == 'Download' and scope['currency'] == 'USD', 'SELECTED_SCOPE_DIMENSION')
    _need(opening['scope'] == scope and opening['unit'] == scope['unit'], 'OPENING_SCOPE')
    start, end = _day(data['period']['start']), _day(data['period']['end'])
    _need(start < end, 'INVALID_PERIOD')
    cutoff = _instant(data['cutoff'])
    _need(terms['rounding'] == 'exact_no_rounding' and terms['quantity_policy'] == 'nonnegative_selected_period', 'SELECTED_POLICY_REQUIRED')
    _need(terms['per_unit'] == scope['unit'] and terms['currency'] == scope['currency'], 'RATE_DIMENSION')
    rate, share, prior = _exact(terms['rate']), _exact(terms['participation']), _exact(opening['quantity'])
    _need(rate >= 0 and prior >= 0 and 0 <= share <= 1, 'SELECTED_TERM_DOMAIN')
    _identities(data['evidence'], 'evidence_id')
    evidence = {}
    for row in data['evidence']:
        _need(_instant(row['observed_at']) < cutoff, 'EVIDENCE_AFTER_CUTOFF')
        evidence[row['evidence_id']] = row
    _identities(data['usage'], 'record_id')
    total = Fraction()
    identifiers = []
    for row in data['usage']:
        _need(row['unit'] == scope['unit'], 'USAGE_UNIT')
        _need(row.get('scope', scope) == scope, 'USAGE_SCOPE')
        _need(start <= _day(row['effective_date']) < end, 'USAGE_OUTSIDE_SELECTED_PERIOD')
        _need(_instant(row['observed_at']) < cutoff, 'USAGE_AFTER_CUTOFF')
        _need(row['evidence_ref'] in evidence, 'USAGE_EVIDENCE_REQUIRED')
        amount = _exact(row['quantity'])
        _need(amount >= 0, 'NEGATIVE_SELECTED_QUANTITY')
        total += amount
        identifiers.append(row['record_id'])
    gross = total * rate
    earned = gross * share
    closing = prior + total
    return {'period_quantity': total, 'gross': gross, 'earned': earned, 'closing_quantity': closing,
            'unit': scope['unit'], 'currency': scope['currency'], 'usage_ids': sorted(identifiers),
            'closing_state': {'scope': dict(scope), 'quantity': closing, 'unit': scope['unit']}}


def quantity_participation(data):
    """Return exact controls for the declared policy; no payment is executed."""
    try:
        return _calculate(data)
    except (KeyError, TypeError, ValueError, ZeroDivisionError) as exc:
        if isinstance(exc, QuantityOracleError):
            raise
        raise QuantityOracleError('MALFORMED_NEUTRAL_INPUT') from exc


def exact_json(value):
    if isinstance(value, Fraction):
        return str(value)
    if isinstance(value, dict):
        return {key: exact_json(item) for key, item in value.items()}
    if isinstance(value, list):
        return [exact_json(item) for item in value]
    return value
