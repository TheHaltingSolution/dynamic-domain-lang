"""Pinned readable policy provenance and bounded implementation consistency.

The policy registry is reviewed source, never inferred from a filename or title.
Its core signatures pin the *used expanded program*, not a bag of unused Bind
expressions. They deliberately recognize the three bounded policy versions,
not arbitrary mathematical equivalence or the truth of supplied evidence.
"""
from __future__ import annotations

from copy import deepcopy
import re
from pathlib import Path, PurePosixPath

from .codecs import DataError, digest, file_digest, read_json
from .parser import ParseError
from .readable import is_readable, parse_readable, readable_policy_dependencies


REGISTRY = "docs/spl/policies/manifest.json"
SIGNATURE_FORMAT = "spl-policy-core/1"
REVIEW_LIMITATION = (
    "Bounded expanded-AST signature comparison, not a proof of policy semantics, "
    "mathematical equivalence, supplied evidence, or contract interpretation. "
    "Display/phrase renames, whitespace and equivalent parentheses are accepted; "
    "changed executable structure, rates or methods require a revised policy. "
    "Core identifier renaming and general equivalent rewrites are not recognized."
)


def _error(code, message, *, pointer="", span=None):
    raise DataError(code, message, pointer, span)


def _without_spans(value):
    if isinstance(value, dict):
        return {key: _without_spans(item) for key, item in value.items() if key != 'span'}
    if isinstance(value, list):
        return [_without_spans(item) for item in value]
    return value


def _source(source, source_name):
    try:
        return readable_policy_dependencies(source, source_name), parse_readable(source, source_name)
    except ParseError as exc:
        _error('POLICY_SOURCE', str(exc), span=exc.span)


def _core_signatures(tree, dependencies):
    """Keep lexical order: assertion order and closing/output wiring matter."""
    expected_markers = {
        f'incorporated_policy_{i}': item['policy_id']
        for i, item in enumerate(dependencies['policies'])
    }
    seen_markers, declarations = set(), []
    for declaration in tree['declarations']:
        name = declaration.get('name')
        if name in expected_markers:
            expected = {
                'kind': 'define', 'name': name, 'type': {'name': 'Text', 'args': []},
                'expr': {'kind': 'text', 'value': expected_markers[name]},
                'citation': None, 'alias': None,
            }
            if name in seen_markers or _without_spans(declaration) != expected:
                _error('POLICY_CORE_MISMATCH', 'Policy provenance definition was overridden',
                       span=declaration.get('span'))
            seen_markers.add(name)
            continue
        declarations.append({
            'kind': declaration['kind'],
            'label': name or declaration.get('code') or declaration['kind'],
            'sha256': digest(_without_spans(declaration)),
        })
    if seen_markers != set(expected_markers):
        _error('POLICY_CORE_MISMATCH', 'Missing typed policy provenance definition')
    return {'format': SIGNATURE_FORMAT,
            **{key: tree[key] for key in ('language', 'core', 'schema')},
            'declarations': declarations}


def readable_core_signatures(source, source_name='<string>'):
    """Authoring helper for deliberate registry revisions; execution never repins."""
    dependencies, tree = _source(source, source_name)
    return _core_signatures(tree, dependencies)


def _path(repo_root, locator):
    if (not isinstance(locator, str) or '\\' in locator or ':' in locator or
            not locator.startswith('docs/spl/policies/') or
            any(part in {'', '.', '..'} for part in locator.split('/')) or
            PurePosixPath(locator).is_absolute()):
        _error('POLICY_LOCATOR', 'Policy locator must remain under docs/spl/policies')
    root = Path(repo_root).resolve()
    resolved = (root / locator).resolve()
    if not resolved.is_relative_to(root / 'docs/spl/policies'):
        _error('POLICY_LOCATOR', 'Policy locator resolves outside the policy directory')
    return resolved


def _registry(repo_root):
    path = _path(repo_root, REGISTRY)
    try:
        registry = read_json(path)
        if (not isinstance(registry, dict) or set(registry) != {'version', 'policies'} or
                registry['version'] != '1' or not isinstance(registry['policies'], dict)):
            _error('POLICY_REGISTRY', 'Unsupported policy registry structure/version')
        return registry, file_digest(path)
    except (DataError, OSError) as exc:
        if isinstance(exc, DataError) and exc.code.startswith('POLICY_'):
            raise
        _error('POLICY_REGISTRY', f'Cannot read strict pinned policy registry: {exc}')


def _value(package, path):
    if not isinstance(path, str) or not re.fullmatch(r'[A-Za-z_][A-Za-z_0-9]*(?:\.[A-Za-z_][A-Za-z_0-9]*)*', path):
        _error('POLICY_REGISTRY', 'Invalid policy parameter path')
    value = package
    for key in path.split('.'):
        if not isinstance(value, dict) or key not in value:
            _error('POLICY_PARAMETER', f'Missing required policy data: {path}', pointer='/' + path.replace('.', '/'))
        value = value[key]
    return deepcopy(value)


def _validate_entry(entry, policy_id):
    fields = {'profile', 'document', 'bindings', 'iterations', 'settlements', 'parameter_paths', 'core_signatures'}
    if not isinstance(entry, dict) or set(entry) != fields:
        _error('POLICY_REGISTRY', f'Incomplete or unsupported policy entry {policy_id}')
    for key in ('profile', 'document'):
        if not isinstance(entry[key], str) or not entry[key]:
            _error('POLICY_REGISTRY', f'Policy {key} must be a nonempty string')
    for key in ('bindings', 'settlements'):
        if (not isinstance(entry[key], dict) or
                not all(isinstance(label, str) and label and isinstance(value, str) and value
                        for label, value in entry[key].items())):
            _error('POLICY_REGISTRY', f'Policy {key} must map labels to nonempty expressions')
    iterations = entry['iterations']
    if (not isinstance(iterations, dict) or
            not all(isinstance(label, str) and label and isinstance(value, dict) and
                    set(value) == {'item', 'collection', 'target'} and
                    all(isinstance(item, str) and item for item in value.values())
                    for label, value in iterations.items())):
        _error('POLICY_REGISTRY', 'Invalid policy iteration registration')
    paths = entry['parameter_paths']
    if (not isinstance(paths, list) or not all(isinstance(path, str) for path in paths) or
            len(set(paths)) != len(paths)):
        _error('POLICY_REGISTRY', 'Policy parameter paths must be a unique string list')
    signatures = entry['core_signatures']
    if (not isinstance(signatures, dict) or
            set(signatures) != {'format', 'language', 'core', 'schema', 'declarations'} or
            signatures['format'] != SIGNATURE_FORMAT or
            not all(isinstance(signatures[key], str) for key in ('language', 'core', 'schema')) or
            not isinstance(signatures['declarations'], list) or
            not all(isinstance(item, dict) and set(item) == {'kind', 'label', 'sha256'} and
                    all(isinstance(item[key], str) and item[key] for key in ('kind', 'label', 'sha256')) and
                    re.fullmatch('[0-9a-f]{64}', item['sha256'])
                    for item in signatures['declarations'])):
        _error('POLICY_REGISTRY', 'Invalid bounded core signature specification')


def _resolved(source, source_name, package, repo_root):
    if not is_readable(source):
        return [], None, None, {}
    dependencies, tree = _source(source, source_name)
    if not dependencies['policies']:
        _error('POLICY_REQUIRED', 'Canonical readable execution requires an incorporated versioned policy')
    registry, registry_sha256 = _registry(repo_root)
    actual = _core_signatures(tree, dependencies)
    entries, records = [], {}
    for incorporation in dependencies['policies']:
        policy_id = incorporation['policy_id']
        entry = registry['policies'].get(policy_id)
        if not isinstance(entry, dict):
            _error('POLICY_UNKNOWN', f'Unresolved incorporated policy {policy_id}', span=incorporation['span'])
        _validate_entry(entry, policy_id)
        if entry['profile'] != package.get('profile'):
            _error('POLICY_PROFILE', f'{policy_id} does not authorize profile {package.get("profile")}', span=incorporation['span'])
        if entry['core_signatures'] != actual:
            expected = entry['core_signatures']
            mismatch = None
            if isinstance(expected, dict):
                for index, (want, got) in enumerate(zip(expected.get('declarations', []), actual['declarations'])):
                    if want != got:
                        candidates = [d for d in tree['declarations'] if d.get('name') not in {
                            f'incorporated_policy_{i}' for i in range(len(dependencies['policies']))}]
                        mismatch = candidates[index].get('span')
                        break
            _error('POLICY_CORE_MISMATCH',
                   f'Executable declarations disagree with pinned policy {policy_id}; revise the policy explicitly for a changed method',
                   span=mismatch or incorporation['span'])
        for path in entry['parameter_paths']:
            _value(package, path)
        document = _path(repo_root, entry['document'])
        if document.suffix != '.md':
            _error('POLICY_LOCATOR', 'Readable policy must be a Markdown document')
        try:
            document_sha256 = file_digest(document)
            document.read_text(encoding='utf-8', errors='strict')
        except (OSError, UnicodeError) as exc:
            _error('POLICY_DOCUMENT', f'Cannot read incorporated policy {policy_id}: {exc}')
        entries.append({'policy_id': policy_id, 'profile': entry['profile'],
                        'document': {'locator': entry['document'], 'sha256': document_sha256},
                        'registry': {'locator': REGISTRY, 'sha256': registry_sha256, 'entry_sha256': digest(entry)}})
        records[policy_id] = entry
    return entries, dependencies, tree, records


def policy_closure(source, source_name, package, repo_root):
    """Resolve/check authored policy IDs; return deterministic logical pins.

    Existing nonreadable source has no incorporated policy dependency. Readable
    canonical execution must incorporate a registered policy matching its actual
    expanded program and package profile. No issued package is silently repinned.
    """
    return sorted(_resolved(source, source_name, package, repo_root)[0], key=lambda entry: entry['policy_id'])


def policy_review(source, source_name, package, repo_root):
    """Material rule origins, footer origins and actual required policy values."""
    pins, dependencies, tree, records = _resolved(source, source_name, package, repo_root)
    if dependencies is None:
        return {'format': 'spl-policy-review/1', 'policies': [], 'rules': [], 'limitation': REVIEW_LIMITATION}
    supports = []
    for label, expression in dependencies['bindings'].items():
        supports.append({'kind': 'binding', 'label': label, 'expression': expression,
                         'span': dependencies['binding_spans'][label]})
    for label, expression in dependencies['iterations'].items():
        supports.append({'kind': 'iteration', 'label': label, 'expression': expression,
                         'span': dependencies['iteration_spans'][label]})
    for label, expression in dependencies['settlements'].items():
        supports.append({'kind': 'settlement', 'label': label, 'expression': expression,
                         'span': dependencies['settlement_spans'][label]})
    supports.sort(key=lambda item: (item['span']['line'], item['kind'], item['label']))
    # Rules retain both the main financial statement and any matching footer
    # expression. A lexical link is audit navigation, not an interpretation proof.
    rules, offset = [], 0
    for number, raw in enumerate(source.split('\n'), 1):
        text = raw.rstrip('\r')
        if text.strip() == 'Bindings:':
            break
        if number > 1 and text.strip() and not text.strip().startswith('//'):
            unquoted = re.sub(r'"(?:[^"\\]|\\.)*"', '""', text)
            linked = [item for item in supports if re.search(
                r'(?<![A-Za-z_0-9])' + re.escape(item['label']) + r'(?![A-Za-z_0-9])', unquoted)]
            indent = len(text) - len(text.lstrip(' '))
            rules.append({'text': text.strip(),
                          'span': {'source': source_name, 'line': number, 'column': indent + 1,
                                   'start': offset + indent, 'end': offset + len(text)},
                          'supporting_expressions': deepcopy(linked)})
        offset += len(raw) + 1
    by_id = {item['policy_id']: item for item in dependencies['policies']}
    policies = []
    for pin in sorted(pins, key=lambda item: item['policy_id']):
        entry = records[pin['policy_id']]
        policies.append({**pin, 'incorporation_span': by_id[pin['policy_id']]['span'],
                         'parameters': [{'path': path, 'value': _value(package, path)} for path in entry['parameter_paths']],
                         'supporting_expressions': deepcopy(supports),
                         'core_signatures': deepcopy(entry['core_signatures'])})
    return {'format': 'spl-policy-review/1', 'policies': policies, 'rules': rules, 'limitation': REVIEW_LIMITATION}
