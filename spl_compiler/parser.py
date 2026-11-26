"""Closed SPL surface parser.

The parser preserves exact numeric spellings and source positions. It performs no
economic inference: recognized syntax is resolved and typed by ``checker``.
"""
from __future__ import annotations

from dataclasses import dataclass
import json
import re

from .model import SPLException


class ParseError(SPLException):
    """A stable syntax diagnostic with a precise source span."""

    def __init__(self, code: str, message: str, span: dict):
        super().__init__(code, message, span)


@dataclass(frozen=True)
class Token:
    kind: str
    value: str
    span: dict


_IDENTIFIER = re.compile(r"[A-Za-z_][A-Za-z_0-9]*")
_NUMBER = re.compile(r"[0-9]+(?:\.[0-9]+)?")
_RESERVED = frozenset("""schedule language core schema input opening from define
    citing require else closing emit if then choose unique when otherwise for each
    in yield and or not true false date""".split())


def lex(source: str, source_name: str = "<string>") -> list[Token]:
    """Tokenize UTF-8 source text without accepting host-language escapes."""
    tokens: list[Token] = []
    position = 0
    line, column = 1, 1

    def span(start: int, end: int) -> dict:
        return {"source": source_name, "line": line, "column": column,
                "start": start, "end": end}

    def advance(text: str) -> None:
        nonlocal position, line, column
        position += len(text)
        if "\n" in text:
            line += text.count("\n")
            column = len(text.rsplit("\n", 1)[1]) + 1
        else:
            column += len(text)

    while position < len(source):
        char = source[position]
        if char in " \t\r\n":
            advance(char)
            continue
        if source.startswith("//", position):
            end = source.find("\n", position)
            advance(source[position:len(source) if end < 0 else end])
            continue
        start = position
        if char == '"':
            end = start + 1
            while end < len(source):
                if source[end] == "\\":
                    end += 2
                elif source[end] == '"':
                    end += 1
                    break
                else:
                    end += 1
            raw = source[start:end]
            try:
                value = json.loads(raw)
                # Lone surrogate escape sequences cannot encode valid UTF-8.
                value.encode("utf-8", errors="strict")
            except (ValueError, UnicodeError) as exc:
                raise ParseError("INVALID_STRING", "Expected a valid JSON string", span(start, min(end, len(source)))) from exc
            tokens.append(Token("string", value, span(start, end)))
            advance(raw)
            continue
        match = _IDENTIFIER.match(source, position)
        if match:
            raw = match.group(0)
            tokens.append(Token("identifier", raw, span(start, match.end())))
            advance(raw)
            continue
        match = _NUMBER.match(source, position)
        if match:
            raw = match.group(0)
            tokens.append(Token("number", raw, span(start, match.end())))
            advance(raw)
            continue
        pair = source[position:position + 2]
        if pair in {"==", "!=", "<=", ">=", "=>"}:
            tokens.append(Token("symbol", pair, span(start, start + 2)))
            advance(pair)
            continue
        if char in "{}()[]:;,.<>+-*/=":
            tokens.append(Token("symbol", char, span(start, start + 1)))
            advance(char)
            continue
        raise ParseError("INVALID_CHARACTER", f"Unexpected character {char!r}", span(start, start + 1))
    tokens.append(Token("eof", "", span(position, position)))
    return tokens


class Parser:
    def __init__(self, source: str, source_name: str):
        self.tokens = lex(source, source_name)
        self.position = 0

    @property
    def current(self) -> Token:
        return self.tokens[self.position]

    def take(self) -> Token:
        token = self.current
        self.position += 1
        return token

    def at(self, value: str) -> bool:
        return self.current.value == value and self.current.kind != "eof"

    def accept(self, value: str) -> bool:
        if self.at(value):
            self.take()
            return True
        return False

    def fail(self, message: str, code: str = "SYNTAX_ERROR", token: Token | None = None):
        raise ParseError(code, message, (token or self.current).span)

    def expect(self, value: str) -> Token:
        if not self.at(value):
            self.fail(f"Expected {value!r}, found {self.current.value!r}")
        return self.take()

    def identifier(self) -> Token:
        if self.current.kind != "identifier" or self.current.value in _RESERVED:
            self.fail("Expected an identifier")
        return self.take()

    def string(self) -> Token:
        if self.current.kind != "string":
            self.fail("Expected a JSON string")
        return self.take()

    def node(self, kind: str, start: Token, **fields) -> dict:
        node_span = dict(start.span)
        node_span["end"] = self.tokens[self.position - 1].span["end"]
        return {"kind": kind, **fields, "span": node_span}

    def schedule(self) -> dict:
        start = self.expect("schedule")
        name = self.identifier().value
        self.expect("language")
        language = self.string().value
        self.expect("core")
        core = self.string().value
        self.expect("schema")
        schema = self.string().value
        features = []
        while self.accept("uses"):
            features.append(self.string().value)
        self.expect("{")
        declarations = []
        while not self.at("}"):
            if self.current.kind == "eof":
                self.fail("Unterminated schedule")
            declarations.append(self.declaration())
        self.expect("}")
        if self.current.kind != "eof":
            self.fail("Trailing content after schedule", "TRAILING_CONTENT")
        result = self.node("schedule", start, name=name, language=language,
                           core=core, schema=schema, declarations=declarations)
        if features:
            result["features"] = features
        return result

    def type(self) -> dict:
        if self.accept("{"):
            fields = []
            if not self.accept("}"):
                while True:
                    name = self.identifier().value
                    self.expect(":")
                    fields.append((name, self.type()))
                    if not self.accept(","):
                        break
                self.expect("}")
            return {"name": "Record", "args": [], "fields": fields}
        name = self.identifier().value
        args = []
        if self.accept("<"):
            args.append(self.type())
            while self.accept(","):
                args.append(self.type())
            self.expect(">")
        return {"name": name, "args": args}

    def declaration(self, local: bool = False) -> dict:
        start = self.current
        kind = self.current.value
        allowed = {"define", "require"} if local else {"input", "opening", "define", "require", "closing", "emit"}
        if kind not in allowed:
            self.fail("Expected a supported declaration", "UNSUPPORTED_DECLARATION")
        self.take()
        if kind == "require":
            expr = self.expression()
            self.expect("else")
            code = self.string().value
            self.expect(";")
            return self.node(kind, start, expr=expr, code=code)
        name = self.string().value if kind == "emit" else self.identifier().value
        declared_type = None
        alias = None
        citation = None
        expr = None
        if kind in {"input", "opening"}:
            self.expect(":")
            declared_type = self.type()
            if kind == "opening":
                self.expect("from")
                alias = self.string().value
        else:
            if kind == "define" and self.accept(":"):
                declared_type = self.type()
            self.expect("=")
            expr = self.expression()
            if kind == "define" and self.accept("citing"):
                citation = self.string().value
        self.expect(";")
        return self.node(kind, start, name=name, type=declared_type, expr=expr,
                         citation=citation, alias=alias)

    def expression(self) -> dict:
        start = self.current
        if self.at("fold") or self.at("ordered_fold"):
            ordered = self.take().value == "ordered_fold"
            source = self.expression()
            self.expect("from")
            initial = self.expression()
            order = None
            if ordered:
                self.expect("by")
                key_binder = self.identifier().value
                self.expect("=>")
                key = self.expression()
                self.expect("identified")
                self.expect("by")
                id_binder = self.identifier().value
                self.expect("=>")
                identity = self.expression()
                if not self.accept("ties"):
                    self.fail("Ordered fold requires an explicit tie policy", "UNRESOLVED_EVENT_ORDER")
                order = dict(key_binder=key_binder,key=key,id_binder=id_binder,identity=identity,ties=self.string().value)
            self.expect("with")
            state = self.identifier().value
            self.expect(",")
            event = self.identifier().value
            self.expect("{")
            declarations = []
            while not self.at("yield"):
                declarations.append(self.declaration(local=True))
            self.expect("yield")
            body = self.expression()
            self.expect(";")
            self.expect("}")
            return self.node("fold",start,source=source,initial=initial,state=state,event=event,
                             order=order,declarations=declarations,body=body)
        if self.accept("if"):
            condition = self.expression()
            self.expect("then")
            then = self.expression()
            self.expect("else")
            otherwise = self.expression()
            return self.node("if", start, condition=condition, then=then, **{"else": otherwise})
        if self.accept("choose"):
            if self.at("priority") or self.at("registered"):
                priority_mode = self.accept("priority")
                if not priority_mode:
                    self.expect("registered")
                    self.expect("unique")
                self.expect("{")
                arms = []
                while self.accept("rule"):
                    rule_id = self.string().value
                    rank = 0
                    if priority_mode:
                        self.expect("priority")
                        negative = self.accept("-")
                        token = self.take()
                        if token.kind != "number" or not token.value.isascii() or not token.value.isdigit():
                            self.fail("Priority requires an integer", token=token)
                        rank = int(token.value) * (-1 if negative else 1)
                    self.expect("when")
                    predicate = self.expression()
                    self.expect("=>")
                    body = self.expression()
                    self.expect(";")
                    arms.append(dict(rule_id=rule_id, priority=rank, predicate=predicate, body=body))
                otherwise = None
                if self.accept("otherwise"):
                    rule_id = self.string().value
                    self.expect("=>")
                    otherwise = dict(rule_id=rule_id, body=self.expression())
                    self.expect(";")
                self.expect("}")
                return self.node("select_rules", start, priority_mode=priority_mode, arms=arms, otherwise=otherwise)
            self.expect("unique")
            self.expect("{")
            arms = []
            while self.accept("when"):
                condition = self.expression()
                self.expect("=>")
                body = self.expression()
                self.expect(";")
                arms.append([condition, body])
            if not arms:
                self.fail("choose unique requires at least one when arm")
            otherwise = None
            if self.accept("otherwise"):
                self.expect("=>")
                otherwise = self.expression()
                self.expect(";")
            self.expect("}")
            return self.node("choose", start, arms=arms, otherwise=otherwise)
        if self.accept("for"):
            self.expect("each")
            name = self.identifier().value
            self.expect("in")
            source = self.expression()
            self.expect("{")
            declarations = []
            while not self.at("yield"):
                declarations.append(self.declaration(local=True))
            self.expect("yield")
            result = self.expression()
            self.expect(";")
            self.expect("}")
            return self.node("for", start, name=name, source=source,
                             declarations=declarations, **{"yield": result})
        return self.binary(0)

    _PRECEDENCE = (("or",), ("and",), ("==", "!="), ("<", "<=", ">", ">="), ("+", "-"), ("*", "/"))

    def binary(self, level: int) -> dict:
        if level == len(self._PRECEDENCE):
            return self.unary()
        start = self.current
        left = self.binary(level + 1)
        ops = self._PRECEDENCE[level]
        count = 0
        while self.current.value in ops and self.current.kind != "eof":
            if level in {2, 3} and count:
                self.fail("Equality and comparison operators cannot be chained")
            op = self.take().value
            right = self.binary(level + 1)
            left = self.node("binary", start, op=op, left=left, right=right)
            count += 1
        return left

    def unary(self) -> dict:
        if self.current.value in {"-", "not"}:
            start = self.take()
            return self.node("unary", start, op=start.value, expr=self.postfix())
        return self.postfix()

    def postfix(self) -> dict:
        start = self.current
        expr = self.atom()
        while True:
            if self.accept("."):
                expr = self.node("field", start, expr=expr, name=self.identifier().value)
            elif self.accept("("):
                if expr["kind"] != "name":
                    self.fail("Only a named published built-in may be called", "UNSUPPORTED_CALL", start)
                args = []
                if not self.at(")"):
                    args.append(self.argument())
                    while self.accept(","):
                        args.append(self.argument())
                self.expect(")")
                expr = self.node("call", start, name=expr["name"], args=args)
            else:
                return expr

    def argument(self) -> dict:
        if self.current.kind == "identifier" and self.tokens[self.position + 1].value == "=>":
            start = self.identifier()
            self.expect("=>")
            body = self.expression()
            return self.node("lambda", start, name=start.value, body=body)
        return self.expression()

    def atom(self) -> dict:
        start = self.current
        if start.kind == "number":
            self.take()
            return self.node("number", start, value=start.value)
        if start.kind == "string":
            self.take()
            return self.node("text", start, value=start.value)
        if self.accept("true"):
            return self.node("bool", start, value=True)
        if self.accept("false"):
            return self.node("bool", start, value=False)
        if self.accept("date"):
            value = self.string().value
            return self.node("date", start, value=value)
        if start.kind == "identifier" and start.value == "USD":
            self.take()
            if self.current.kind != "number":
                self.fail("Money literals require an unsigned decimal after their currency")
            value = self.take().value
            return self.node("money", start, currency="USD", value=value)
        if self.accept("("):
            expr = self.expression()
            self.expect(")")
            return expr
        if self.accept("["):
            items = []
            if not self.at("]"):
                items.append(self.expression())
                while self.accept(","):
                    items.append(self.expression())
            self.expect("]")
            return self.node("list", start, items=items)
        if self.accept("{"):
            fields = []
            seen = set()
            if not self.at("}"):
                while True:
                    field = self.identifier()
                    if field.value in seen:
                        self.fail(f"Duplicate record field {field.value!r}", "DUPLICATE_FIELD", field)
                    seen.add(field.value)
                    self.expect(":")
                    fields.append([field.value, self.expression()])
                    if not self.accept(","):
                        break
            self.expect("}")
            return self.node("record", start, fields=fields)
        if start.kind == "identifier" and start.value not in _RESERVED:
            self.take()
            return self.node("name", start, name=start.value)
        self.fail("Expected an expression")


def parse(source: str, source_name: str = "<string>") -> dict:
    """Parse one complete schedule; reject all trailing content."""
    return Parser(source, source_name).schedule()
