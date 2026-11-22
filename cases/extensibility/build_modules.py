"""Register the explicit supplied-date baseline and, later, derived-date method."""
from copy import deepcopy
from datetime import date, timedelta
from pathlib import Path

from cases.r1.build_modules import ROOT, _descriptor, _package
from spl_compiler.codecs import canonical, read_json

FOLDER = Path(__file__).resolve().parent


def register_deadline(derived=False):
    name = 'calendar-derived' if derived else 'calendar-supplied'
    reference = _descriptor(name, 'calendar-months-demand.spl' if derived else 'supplied-deadline.spl', 'policy.md',
        {'cutoff': 'parameter', 'reserve_ledger': 'result', **({'months': 'parameter', 'invalid_day_policy': 'parameter'} if derived else {})},
        state=[{'opening': 'reserve', 'closing': 'reserve', 'purpose': 'return_reserve', 'unit': 'USD',
                'key_fields': ['agreement_id', 'participant_id', 'pool_id', 'purpose', 'vintage_id'],
                'movement_kinds': ['net_change'], 'history_required': False}],
        domains={'months': {'minimum': '0'}, 'invalid_day_policy': {'choices': ['clamp_day', 'reject_invalid_day'], 'methodology': True}} if derived else {},
        folder=FOLDER, capabilities=['spl.calendar-months/1'] if derived else [])
    return reference


def deadline_package(fixture=None, *, derived=False, reference=None):
    fixture = deepcopy(fixture or read_json(ROOT / 'cases/r1/supplied-due-reserve.json'))
    reference = reference or register_deadline(derived)
    vintage = fixture['vintage']
    participant = 'synthetic-reserve-holder'
    if fixture['policy'] != 'inclusive_supplied_due_date' or vintage['currency'] != 'USD':
        raise ValueError('DYN_SELECTED_POLICY_REQUIRED')
    if any(vintage[key] != fixture['scope'][key] for key in ['contract_id', 'pool_id', 'currency']):
        raise ValueError('DYN_VINTAGE_SCOPE')
    evidence = {row['id']: row for row in fixture['evidence']}
    observed = evidence[vintage['evidence_id']]['observed_date'] + 'T00:00:00Z'
    cutoff = (date.fromisoformat(fixture['observed_through']) + timedelta(days=1)).isoformat() + 'T00:00:00Z'
    scope = {'agreement_id': fixture['scope']['contract_id'], 'participant_id': participant,
             'pool_id': fixture['scope']['pool_id'], 'period': deepcopy(fixture['period'])}
    inputs = {'scope': scope, 'vintage_id': vintage['id'], 'creation_date': vintage['creation_date'],
              'close_date': fixture['close_date'], 'observed_at': observed}
    parameters = {'cutoff': cutoff}
    if derived:
        parameters.update(months=str(fixture['months']), invalid_day_policy=fixture['invalid_day_policy'])
    else:
        inputs['supplied_due_date'] = vintage['supplied_due_date']
    state_scope = {key: scope[key] for key in ['agreement_id', 'participant_id', 'pool_id']}
    state_scope['vintage_id'] = vintage['id']
    cell = {'state_key': canonical({**state_scope, 'purpose': 'return_reserve'}), 'opening_port': 'reserve',
            'purpose': 'return_reserve', 'unit': 'USD', 'scope': state_scope, 'boundary': fixture['period']['start'],
            'quantity': vintage['available_balance'], 'provenance_ref': vintage['evidence_id'], 'scenario_id': fixture['case_id']}
    return _package(fixture, reference, inputs, parameters, {}, [participant], [], [cell])
