"""Private bounded subprocess entrypoints for canonical compact publication."""
from pathlib import Path
import sys
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))


def main():
    from spl_compiler import lean_tools
    assert lean_tools.ROOT == ROOT
    from spl_compiler.trace_transport import canonical_json, loads
    from spl_compiler.native_trace import read_compact
    command, *args = sys.argv[1:]
    if command == "validate" and len(args) == 1:
        result = read_compact(args[0])
    elif command == "v1-carry" and len(args) == 1:
        from spl_compiler.v1_carry import _load_v1_inline
        result = _load_v1_inline(args[0])
    elif command == "load" and len(args) == 1:
        from spl_compiler.audited_artifacts import _load_completed_inline
        result = _load_completed_inline(args[0])
    elif command == "publish" and len(args) == 2:
        from spl_compiler.audited_artifacts import AuditedPublication, FORMAT
        from spl_compiler.artifacts import _strict_json, _read_bounded, MAX_MANIFEST_BYTES, MAX_RESULT_BYTES
        import re
        destination, invocation = args
        root = Path(destination).resolve()
        if not re.fullmatch(r"[a-z0-9_-]{1,32}", invocation):
            raise ValueError("PUBLICATION_PATH")
        work = root / ".runs" / invocation
        if work.resolve() != work or work.is_symlink():
            raise ValueError("PUBLICATION_PATH")
        running = _read_bounded(root / "completion.json", MAX_MANIFEST_BYTES)
        if _strict_json(running) != {"format": FORMAT, "status": "running", "invocation_id": invocation}:
            raise ValueError("PUBLICATION_INVOCATION_CHANGED")
        request = _strict_json(_read_bounded(work / "publication-request.json", MAX_RESULT_BYTES))
        if type(request) is not dict or set(request) != {"result", "fields"}:
            raise ValueError("PUBLICATION_REQUEST")
        publication = AuditedPublication.__new__(AuditedPublication)
        publication.root, publication.work = root, work
        publication.invocation_id, publication.running, publication.closed = invocation, running, False
        publication._finish_inline(request["result"], request["fields"])
        result = {"status": "completed"}
    elif command == "reference":
        from spl_compiler.checker import check_schedule
        from spl_compiler.parser import parse
        from spl_compiler.readable import is_readable, parse_readable
        from spl_compiler.linker import link_schedule
        from spl_compiler.evaluator import evaluate
        from spl_compiler.model import encode_value
        source, bindings, *rest = args
        text = Path(source).read_text(encoding="utf-8")
        schedule = parse_readable(text) if is_readable(text) else parse(text)
        if rest:
            if len(rest) != 2 or rest[0] != "--link":
                raise ValueError("USAGE")
            schedule = link_schedule(schedule, loads(Path(rest[1]).read_bytes()))
        checked = check_schedule(schedule)
        supplied = loads(Path(bindings).read_bytes())
        observed = evaluate(checked, supplied["inputs"], supplied["openings"])
        # Never duplicate or serialize the reference audit array. This worker
        # remains memory-bounded while evaluating its own complete semantics.
        result = {"status": observed.status, "emissions": encode_value(observed.emissions),
                  "closing": encode_value(observed.closing), "diagnostics": observed.diagnostics}
    else:
        raise ValueError("USAGE")
    from hashlib import sha256
    import json
    origins = {}
    for name, module in sorted(sys.modules.items()):
        if name == "spl_compiler" or name.startswith(("spl_compiler.", "cases.", "scripts.")):
            location = getattr(module, "__file__", None)
            if location:
                path = Path(location).resolve()
                if not path.is_relative_to(ROOT):
                    raise ValueError("AUDIT_WORKER_IMPORT_ROOT")
                origins[name] = {"path": str(path), "sha256": sha256(path.read_bytes()).hexdigest()}
    print(json.dumps({"format": "spl-audit-worker-origin/1", "root": str(ROOT),
                      "build_root": str(lean_tools.ROOT), "modules": origins}, sort_keys=True), file=sys.stderr)
    if command == "v1-carry":
        print(json.dumps(result, ensure_ascii=False, sort_keys=True, allow_nan=False, separators=(",", ":")))
    else:
        print(canonical_json(result))


if __name__ == "__main__":
    main()
