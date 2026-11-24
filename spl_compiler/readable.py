"""Independent controlled readable SPL expansion into the closed SPL grammar.

Bindings are explicit source declarations, never case-name or file templates.
Every expanded syntax node is mapped back to its authored statement line.
"""
from __future__ import annotations

from dataclasses import dataclass
import json
import re

from .parser import ParseError, lex, parse


@dataclass(frozen=True)
class Line:
    text: str
    indent: int
    span: dict


@dataclass(frozen=True)
class Expansion:
    source: str
    origins: tuple[dict, ...]
    policies: tuple[dict, ...]
    bindings: dict[str, str]
    iterations: dict[str, tuple[str, str, str]]
    settlements: dict[str, str]
    support_spans: dict[str, dict[str, dict]]


def is_readable(source: str) -> bool:
    return source.lstrip().startswith("Participation Schedule for ")


def _error(line: Line, message: str, code: str = "READABLE_SYNTAX_ERROR"):
    raise ParseError(code, message, line.span)


def _lines(source: str, name: str) -> list[Line]:
    if len(source) > 1_000_000:
        raise ParseError("RESOURCE_LIMIT", "Source exceeds 1000000 Unicode scalars", {})
    result, offset = [], 0
    for number, raw in enumerate(source.split("\n"), 1):
        clean = raw.rstrip("\r")
        if "\t" in clean:
            raise ParseError("READABLE_INDENTATION", "Use spaces, not tabs", {"source": name, "line": number, "column": 1, "start": offset, "end": offset + len(clean)})
        indent = len(clean) - len(clean.lstrip(" "))
        text = clean.strip()
        if text and not text.startswith("//"):
            result.append(Line(text, indent, {"source": name, "line": number, "column": indent + 1, "start": offset + indent, "end": offset + len(clean)}))
        offset += len(raw) + 1
    return result


def _settlement_roles(source, roles, origins):
    """Rewrite only parsed name references, preserving fields and string data."""
    try:
        schedule = parse(source)
    except ParseError as error:
        span = origins[min(max(error.span.get('line', 1) - 1, 0), len(origins) - 1)]
        raise ParseError(error.code, error.message, span) from None
    edits = []
    marker = 'settlement_participant'

    def fail(node, message):
        line = node.get('span', {}).get('line', 1) - 1
        raise ParseError('READABLE_SETTLEMENT_ROLE', message, origins[min(max(line, 0), len(origins)-1)])

    def visit(node):
        if isinstance(node, list):
            for value in node: visit(value)
        elif isinstance(node, dict):
            kind = node.get('kind')
            if kind in {'input', 'opening', 'define'} and node.get('name') == marker:
                fail(node, 'The settlement role marker cannot be declared explicitly with multiple headings')
            if kind == 'lambda' and node.get('name') == marker:
                fail(node, 'A local binder cannot shadow the settlement role marker')
            if kind == 'for' and node.get('name') == marker:
                fail(node, 'A local binder cannot shadow the settlement role marker')
            if kind == 'fold' and marker in (node.get('state'), node.get('event')):
                fail(node, 'A local binder cannot shadow the settlement role marker')
            if kind == 'fold' and node.get('order') and marker in (node['order']['key_binder'], node['order']['id_binder']):
                fail(node, 'A local binder cannot shadow the settlement role marker')
            if kind == 'name' and node.get('name') == marker:
                span = node['span']; role = roles[span['line']-1]
                if role is None: fail(node, 'A settlement role requires an enclosing heading with multiple settlements')
                edits.append((span['start'], span['end'], role))
            for key, value in node.items():
                if key not in {'span', '_type'}: visit(value)
    visit(schedule)
    parts, cursor = [], 0
    for start, end, replacement in sorted(edits):
        parts.extend((source[cursor:start], replacement)); cursor = end
    parts.append(source[cursor:])
    return ''.join(parts)


def expand_readable(source: str, source_name: str = "<string>") -> Expansion:
    lines = _lines(source, source_name)
    if not lines or not lines[0].text.startswith("Participation Schedule for "):
        raise ParseError("READABLE_SYNTAX_ERROR", "Expected Participation Schedule for <title>", lines[0].span if lines else {})
    footers = [i for i, line in enumerate(lines) if line.text == "Bindings:"]
    if len(footers) != 1:
        _error(lines[0], "Exactly one explicit Bindings: footer is required")
    split = footers[0]
    rules = lines[1:split]
    bindings = lines[split + 1:]
    aliases, iterations, fields, settlements, declarations = {}, {}, {}, {}, []
    support_spans = {'bindings': {}, 'iterations': {}, 'settlements': {}}
    schedule = metadata = None

    def phrase_value(line, raw):
        try:
            value = json.loads(raw)
            value.encode("utf-8", errors="strict")
            return value
        except (ValueError, UnicodeError) as exc:
            raise ParseError("INVALID_STRING", "Expected a valid JSON binding phrase", line.span) from exc

    for line in bindings:
        text = line.text
        if text.startswith(("Bind ", "Settle ", "Field ", "Iterate ")):
            try:
                lex(text, source_name)
            except ParseError as exc:
                raise ParseError(exc.code, str(exc), line.span) from exc
        if text.startswith("Schedule ") and text.endswith("."):
            if schedule is not None:
                _error(line, "Duplicate Schedule declaration")
            schedule = text[9:-1]
        elif text.startswith("Using ") and text.endswith("."):
            if metadata is not None:
                _error(line, "Duplicate Using declaration")
            metadata = text[6:-1]
        elif text.startswith("Bind "):
            match = re.fullmatch(r'Bind ("(?:[^"\\]|\\.)*") to (.+)\.', text)
            if not match:
                _error(line, 'Expected Bind "phrase" to <core expression>.')
            phrase, expression = phrase_value(line, match[1]), match[2]
            if not phrase or phrase in aliases:
                _error(line, "Binding phrases must be nonempty and unique")
            aliases[phrase] = expression
            support_spans['bindings'][phrase] = dict(line.span)
        elif text.startswith("Settle "):
            match = re.fullmatch(r'Settle ("(?:[^"\\]|\\.)*") with (.+)\.', text)
            if not match:
                _error(line, 'Expected Settle "party" with participant_expression.')
            phrase = phrase_value(line, match[1])
            if not phrase or phrase in settlements:
                _error(line, "Settlement labels must be nonempty and unique")
            settlements[phrase] = match[2]
            support_spans['settlements'][phrase] = dict(line.span)
        elif text.startswith("Field "):
            match = re.fullmatch(r'Field ("(?:[^"\\]|\\.)*") as ([A-Za-z_][A-Za-z_0-9]*)\.', text)
            if not match:
                _error(line, 'Expected Field "phrase" as record_field.')
            phrase = phrase_value(line, match[1])
            if phrase in fields:
                _error(line, "Duplicate report field phrase")
            fields[phrase] = match[2]
        elif text.startswith("Iterate "):
            match = re.fullmatch(r'Iterate ("(?:[^"\\]|\\.)*") as ([A-Za-z_][A-Za-z_0-9]*) in (.+) into ([A-Za-z_][A-Za-z_0-9]*)\.', text)
            if not match:
                _error(line, 'Expected Iterate "phrase" as item in collection into result.')
            phrase = phrase_value(line, match[1])
            if not phrase or phrase in iterations:
                _error(line, "Iteration phrases must be nonempty and unique")
            iterations[phrase] = (match[2], match[3], match[4])
            support_spans['iterations'][phrase] = dict(line.span)
        elif text.endswith(";") and text.split(" ", 1)[0] in {"input", "opening", "require", "define"}:
            declarations.append((text, line.span))
        else:
            _error(line, "Unsupported supporting declaration")
    if schedule is None or metadata is None:
        _error(lines[split], "Bindings must explicitly declare Schedule and Using versions")
    if not re.fullmatch(r"[A-Za-z_][A-Za-z_0-9]*", schedule):
        _error(lines[split], "Schedule must be a core identifier")
    ordered = sorted(aliases, key=len, reverse=True)
    alias_pattern = re.compile(r'"(?:[^"\\]|\\.)*"|' + "|".join(r"(?<![A-Za-z_0-9])" + re.escape(k) + r"(?![A-Za-z_0-9])" for k in ordered)) if ordered else None

    def names(text, grouped=False):
        def replacement(match):
            if match[0] not in aliases:
                return match[0]
            value = aliases[match[0]]
            return "(" + value + ")" if grouped else value
        return alias_pattern.sub(replacement, text) if alias_pattern else text

    def expression(text):
        text = names(text, grouped=True)
        if text.startswith("the lesser of ") or text.startswith("the greater of "):
            prefix = "the lesser of " if text.startswith("the lesser of ") else "the greater of "
            parts = text[len(prefix):].split(" and ")
            if len(parts) != 2:
                return text  # closed parser rejects unsupported phrase/ambiguity
            return ("min" if "lesser" in prefix else "max") + "(" + expression(parts[0]) + ", " + expression(parts[1]) + ")"
        # Rewrite only unquoted text; numeric spellings remain exact, including 7.5%.
        parts = re.split(r'("(?:[^"\\]|\\.)*")', text)
        for i in range(0, len(parts), 2):
            part = re.sub(r"([0-9]+(?:\.[0-9]+)?)%", lambda m: "(" + m[1] + ("" if "." in m[1] else ".0") + " / 100)", parts[i])
            for a, b in [(" less ", " - "), (" plus ", " + "), (" of ", " * ")]:
                part = part.replace(a, b)
            parts[i] = part
        return "".join(parts)

    def report(text, line):
        if "," not in text or text.startswith("{"):
            return expression(text)
        parts = [x.strip() for x in text.split(",")]
        if any(x not in fields for x in parts):
            _error(line, "Every report-list name needs an explicit Field binding")
        return "{ " + ", ".join(fields[x] + ": " + expression(x) for x in parts) + " }"

    def definition(line):
        text = line.text
        if not text.endswith("."):
            _error(line, "Readable statements must end with a period")
        body = text[:-1]
        match = re.fullmatch(r"(.+?) (?:is|are) (.+)", body)
        if not match:
            _error(line, "Expected <name> is/are <expression>.")
        target, rhs = names(match[1]), match[2]
        if not re.fullmatch(r"[A-Za-z_][A-Za-z_0-9]*", target):
            _error(line, "Definition name needs an explicit identifier binding")
        citation = ""
        if ' citing ' in rhs:
            rhs, cited = rhs.rsplit(' citing ', 1)
            citation = " citing " + cited
        return target, expression(rhs), citation

    output = [(f"schedule {schedule} {metadata} {{", lines[0].span), *declarations]
    role_contexts = [None] * len(output)
    multiple_settlements = sum(line.text.startswith('For settlement with ') and line.text.endswith(':') for line in rules) > 1
    # Include authored references, not just declarations, so a formerly unknown
    # identifier cannot accidentally become a generated role binding.
    authored_names = set(re.findall(r'[A-Za-z_][A-Za-z_0-9]*', source))
    active_role, next_role = None, 0
    policies = []

    def emit(text, line):
        output.append((text, line.span))
        role_contexts.append(active_role)

    def branch(index, parent):
        values = []
        level = rules[index].indent if index < len(rules) else parent
        while index < len(rules) and rules[index].indent > parent:
            line = rules[index]
            if line.indent != level:
                _error(line, "Statements in a block must share indentation", "READABLE_INDENTATION")
            target, rhs, citation = definition(line)
            values.append((target, rhs, citation, line))
            index += 1
        if not values:
            _error(rules[index - 1], "Conditional branch must define at least one value")
        return values, index

    def block(index, parent=-1, depth=0):
        nonlocal active_role, next_role
        if depth > 64:
            _error(rules[index], "Readable block nesting exceeds 64", "RESOURCE_LIMIT")
        level = rules[index].indent if index < len(rules) else parent
        while index < len(rules) and rules[index].indent > parent:
            line = rules[index]
            if line.indent != level:
                _error(line, "Statements in a block must share indentation", "READABLE_INDENTATION")
            text = line.text
            if text.startswith("Incorporate "):
                match = re.fullmatch(r'Incorporate policy ("(?:[^"\\]|\\.)*")\.', text)
                if not match or line.indent != 0:
                    _error(line, 'Expected top-level Incorporate policy "identifier@version".')
                policy_id = phrase_value(line, match[1])
                if not re.fullmatch(r'[A-Za-z0-9][A-Za-z0-9._/\-]*@[A-Za-z0-9][A-Za-z0-9._\-]*', policy_id):
                    _error(line, 'Policy identity must be an explicit identifier@version')
                if any(p['policy_id'] == policy_id for p in policies):
                    _error(line, 'Duplicate incorporated policy')
                emit(f'define incorporated_policy_{len(policies)} : Text = {json.dumps(policy_id)};', line)
                policies.append({'policy_id': policy_id, 'span': dict(line.span)})
                index += 1
                continue
            if text.startswith("For each ") and text.endswith(":"):
                phrase = text[9:-1]
                if phrase not in iterations:
                    _error(line, "For each requires an explicit Iterate binding")
                item, collection, target = iterations[phrase]
                emit(f"define {target} = for each {item} in {collection} {{", line)
                next_index = block(index + 1, line.indent, depth + 1)
                if next_index == index + 1 or not rules[next_index - 1].text.startswith("Report by "):
                    _error(line, "For each must end with Report by <label>: <expression>.")
                emit("};", line)
                index = next_index
                continue
            if text.startswith("For settlement with ") and text.endswith(":"):
                party = text[20:-1]
                if party not in settlements:
                    _error(line, "Settlement party requires an explicit Settle binding")
                role = 'settlement_participant'
                if multiple_settlements:
                    while True:
                        role = 'readable_settlement_participant_' + str(next_role)
                        next_role += 1
                        if role not in authored_names: break
                    authored_names.add(role)
                emit("define " + role + " : Id<Participant> = " + settlements[party] + ";", line)
                previous_role = active_role
                if multiple_settlements: active_role = role
                next_index = block(index + 1, line.indent, depth + 1)
                active_role = previous_role
                if next_index == index + 1:
                    _error(line, "Settlement block must contain statements")
                index = next_index
                continue
            if text.startswith("If ") and text.endswith(":"):
                yes, next_index = branch(index + 1, line.indent)
                if next_index >= len(rules) or rules[next_index].text != "Otherwise:" or rules[next_index].indent != line.indent:
                    _error(line, "If requires Otherwise: at the same indentation")
                no, index = branch(next_index + 1, line.indent)
                if [x[0] for x in yes] != [x[0] for x in no] or len({x[0] for x in yes}) != len(yes):
                    _error(line, "Both branches must define the same unique bound names in the same order")
                otherwise = rules[next_index]
                for (target, a, cite, origin), (_, b, other_cite, other_origin) in zip(yes, no):
                    if cite != other_cite:
                        _error(line, "Merged branch citations must agree")
                    emit(f"define {target} = if {expression(text[3:-1])} then (", line)
                    emit(a, origin)
                    emit(") else (", otherwise)
                    emit(b, other_origin)
                    emit(")" + cite + ";", origin)
                continue
            if text.startswith("Account for each ") and text.endswith("."):
                phrase = text[17:-1]
                if phrase != "calendar quarter" or phrase not in aliases:
                    _error(line, "Account for each calendar quarter requires an explicit calendar quarter binding")
                emit("define accounting_period = " + expression(phrase) + ";", line)
                emit('require is_calendar_quarter(accounting_period) else "READABLE_CALENDAR_QUARTER_REQUIRED";', line)
            elif text.startswith("Require ") and text.endswith("."):
                parts = text[8:-1].rsplit(" or fail ", 1)
                if len(parts) != 2:
                    _error(line, 'Require needs or fail "DIAGNOSTIC".')
                emit("require " + expression(parts[0]) + " else " + parts[1] + ";", line)
            elif text.startswith("Report by ") and text.endswith("."):
                parts = text[:-1].split(": ", 1)
                if len(parts) != 2:
                    _error(line, "Report by needs a label and expression")
                emit("yield " + report(parts[1], line) + ";", line)
            elif text.startswith("Report ") and text.endswith("."):
                parts = text[7:-1].split(": ", 1)
                if len(parts) != 2:
                    _error(line, 'Report needs "port": expression.')
                emit("emit " + parts[0] + " = " + report(parts[1], line) + ";", line)
            elif text.startswith("Closing "):
                target, rhs, citation = definition(Line(text[8:], line.indent, line.span))
                if citation:
                    _error(line, "Closing citation belongs on the movement definition")
                emit(f"closing {target} = {rhs};", line)
            elif text == "Otherwise:":
                _error(line, "Otherwise without If")
            else:
                target, rhs, citation = definition(line)
                emit(f"define {target} = {rhs}{citation};", line)
            index += 1
        return index

    if not rules:
        _error(lines[0], "At least one readable rule is required")
    if rules[0].indent != 0:
        _error(rules[0], "Top-level rules must start in column one", "READABLE_INDENTATION")
    block(0)
    output.append(("}", lines[-1].span))
    role_contexts.append(None)
    expanded = "\n".join(x[0] for x in output)
    if multiple_settlements: expanded = _settlement_roles(expanded, role_contexts, [x[1] for x in output])
    return Expansion(expanded, tuple(x[1] for x in output),
                     tuple(policies), dict(aliases), dict(iterations), dict(settlements), support_spans)


def readable_policy_dependencies(source: str, source_name: str = "<string>") -> dict:
    """Expose authored policy provenance and support for canonical policy checks.

    Incorporation is a checked provenance declaration. It does not itself certify
    an external policy: canonical execution resolves and pins the policy document
    and verifies its registered implementation requirements before finalization.
    """
    expanded = expand_readable(source, source_name)
    return {'policies': list(expanded.policies), 'bindings': expanded.bindings,
            'iterations': {phrase: dict(zip(('item', 'collection', 'target'), values))
                           for phrase, values in expanded.iterations.items()},
            'settlements': expanded.settlements,
            'binding_spans': expanded.support_spans['bindings'],
            'iteration_spans': expanded.support_spans['iterations'],
            'settlement_spans': expanded.support_spans['settlements']}


def parse_readable(source: str, source_name: str = "<string>") -> dict:
    expanded = expand_readable(source, source_name)

    def remap(value):
        if isinstance(value, list):
            return [remap(x) for x in value]
        if isinstance(value, dict):
            result = {k: remap(v) for k, v in value.items()}
            if "span" in result:
                span = result["span"]
                result["span"] = dict(expanded.origins[min(max(span.get("line", 1) - 1, 0), len(expanded.origins) - 1)])
            return result
        return value

    try:
        result = remap(parse(expanded.source, source_name))
        result["span"] = {"source": source_name, "start": 0, "end": len(source), "line": 1, "column": 1}
        return result
    except ParseError as exc:
        span = expanded.origins[min(max(exc.span.get("line", 1) - 1, 0), len(expanded.origins) - 1)]
        raise ParseError(exc.code, str(exc), dict(span)) from exc
