#!/usr/bin/env python3
"""Read lists of names out of MiniMe's source with `ast` (patch P25). Standard library only.

Why this exists
  The architecture model (scripts/arch.py) wants some facts to be exact, not traced by an AI: which agents the registry
  knows, which roles map to which module, which agents each router tier runs. Those are plain literals in the code, so
  this module reads them with the `ast` module. It never imports or runs MiniMe code, and it never guesses: when the
  name is missing, assigned more than once, or not a plain literal, the answer is "not found" with the reason, and the
  flow that would have used it is written entirely by Copilot (the System page says so).

Where the text comes from
  From git, not from the working tree: `git show <rev>:<path>` in the MiniMe checkout, so Windows line endings or an
  uncommitted edit cannot change the answer. <rev> is the census commit (arch.py), or HEAD.

A spec (content/arch-flows.json, "extractors") looks like
  {"id": "registry", "file": "backend/eo/registry.py", "kind": "dict-keys", "name": "REGISTRY"}

  kind        reads                                                     items
  dict-keys   NAME = {"a": ..., "b": ...}  (every key a string)         ["a", "b"]              (source order)
  dict-map    NAME = {"a": "x", "b": "y"}  (keys and values strings)    [["a", "x"], ["b", "y"]]
  list        NAME = ["a", "b"]  (a list or tuple of strings)           ["a", "b"]
  nested      NAME = {0: {"field": ["a", "b"]}, 1: {...}}               [{"key": "0", "items": ["a", "b"]}, ...]
              (set "field"; a key that has no such list is skipped)

  An optional "flow" (a flow id) and "cross_check": true make arch.py compare the items with that flow's steps.

Usage (mostly a library; the command is for looking)
  python scripts/arch_extract.py --minime ../MiniMe            run every extractor of content/arch-flows.json
  python scripts/arch_extract.py --minime ../MiniMe --rev HEAD
"""
from __future__ import annotations

import argparse
import ast
import json
import subprocess
import sys
from pathlib import Path

sys.dont_write_bytecode = True      # no __pycache__ next to the scripts

ROOT = Path(__file__).resolve().parent.parent
KINDS = ("dict-keys", "dict-map", "list", "nested")


def read_git_text(repo, rev: str, path: str) -> str | None:
    """The text of `path` at `rev` in `repo` (LF line endings), or None when git cannot find it."""
    r = subprocess.run(["git", "-C", str(repo), "show", f"{rev}:{path}"], capture_output=True)
    if r.returncode:
        return None
    return r.stdout.decode("utf-8-sig", "replace").replace("\r\n", "\n").replace("\r", "\n")


def _str(node) -> str | None:
    return node.value if isinstance(node, ast.Constant) and isinstance(node.value, str) else None


def _key(node) -> str | None:
    """A dict key as text: a string or an integer literal. Anything else (a name, an expression) is not a literal key."""
    if isinstance(node, ast.Constant) and isinstance(node.value, (str, int)) and not isinstance(node.value, bool):
        return str(node.value)
    return None


def _assignments(tree: ast.Module, name: str) -> list[ast.AST]:
    out = []
    for n in tree.body:
        if isinstance(n, ast.Assign) and any(isinstance(t, ast.Name) and t.id == name for t in n.targets):
            out.append(n)
        elif isinstance(n, ast.AnnAssign) and isinstance(n.target, ast.Name) and n.target.id == name and n.value is not None:
            out.append(n)
    return out


def _str_items(node, what: str):
    """([strings], None) for a list/tuple of string literals, else (None, reason). A set is refused: its order is not defined."""
    if not isinstance(node, (ast.List, ast.Tuple)):
        return None, f"{what} is not a list or tuple literal"
    items = []
    for el in node.elts:
        s = _str(el)
        if s is None:
            return None, f"{what} has an element that is not a string literal (line {getattr(el, 'lineno', '?')})"
        items.append(s)
    return items, None


def extract_one(spec: dict, text: str | None) -> dict:
    """Run one extractor spec against source text. Pure. Always returns a dict with "found" (bool); never raises on bad source."""
    res = {"id": spec.get("id", ""), "file": spec.get("file", ""), "name": spec.get("name", ""), "kind": spec.get("kind", ""),
           "found": False, "items": [], "line": None, "reason": None}
    if spec.get("kind") not in KINDS:
        res["reason"] = f"unknown kind {spec.get('kind')!r} (use {', '.join(KINDS)})"
        return res
    if text is None:
        res["reason"] = f"{spec.get('file')} is not in git at that commit"
        return res
    try:
        tree = ast.parse(text)
    except SyntaxError as e:
        res["reason"] = f"{spec.get('file')} does not parse (line {e.lineno})"
        return res
    found = _assignments(tree, spec.get("name", ""))
    if not found:
        res["reason"] = f"{spec.get('name')} is not assigned at module level"
        return res
    if len(found) > 1:
        res["reason"] = f"{spec.get('name')} is assigned {len(found)} times (lines {', '.join(str(n.lineno) for n in found)}); not guessing which one counts"
        return res
    node = found[0].value
    res["line"] = found[0].lineno
    kind = spec["kind"]
    if kind in ("dict-keys", "dict-map", "nested"):
        if not isinstance(node, ast.Dict):
            res["reason"] = f"{spec['name']} is not a dict literal"
            return res
        items = []
        for k, v in zip(node.keys, node.values):
            if k is None:
                res["reason"] = f"{spec['name']} unpacks another dict with ** (line {node.lineno}); the keys are not all literal"
                return res
            key = _key(k)
            if key is None or (kind != "nested" and not isinstance(k.value, str)):
                res["reason"] = f"{spec['name']} has a key that is not a literal (line {getattr(k, 'lineno', '?')})"
                return res
            if kind == "dict-keys":
                items.append(key)
            elif kind == "dict-map":
                val = _str(v)
                if val is None:
                    res["reason"] = f"{spec['name']}[{key!r}] is not a string literal (line {getattr(v, 'lineno', '?')})"
                    return res
                items.append([key, val])
            else:
                field = spec.get("field")
                if not field:
                    res["reason"] = 'kind "nested" needs "field"'
                    return res
                if not isinstance(v, ast.Dict):
                    continue
                for fk, fv in zip(v.keys, v.values):
                    if fk is not None and _str(fk) == field:
                        lst, why = _str_items(fv, f"{spec['name']}[{key}][{field!r}]")
                        if why:
                            res["reason"] = why
                            return res
                        items.append({"key": key, "items": lst})
        res["items"] = items
    else:
        lst, why = _str_items(node, spec["name"])
        if why:
            res["reason"] = why
            return res
        res["items"] = lst
    res["found"] = True
    return res


def extract_all(minime, rev: str, specs: list[dict], reader=read_git_text) -> list[dict]:
    """Run every spec. `reader(minime, rev, path)` returns the file text (tests pass their own)."""
    cache: dict[str, str | None] = {}
    out = []
    for spec in specs:
        path = spec.get("file", "")
        if path not in cache:
            cache[path] = reader(minime, rev, path)
        out.append(extract_one(spec, cache[path]))
    return out


def stage_names(result: dict) -> list[str]:
    """The flat list of names an extractor found (for the 'every stage has a step' cross-check)."""
    if not result.get("found"):
        return []
    names: list[str] = []
    for it in result["items"]:
        if isinstance(it, str):
            names.append(it)
        elif isinstance(it, list):
            names.append(it[0])
        elif isinstance(it, dict):
            names.extend(it.get("items", []))
    seen: set[str] = set()
    return [n for n in names if not (n in seen or seen.add(n))]


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("--minime", required=True, help="the MiniMe checkout")
    ap.add_argument("--rev", default="HEAD", help="the commit to read (default HEAD)")
    ap.add_argument("--registry", default=str(ROOT / "content" / "arch-flows.json"))
    args = ap.parse_args(argv)
    reg = json.loads(Path(args.registry).read_text(encoding="utf-8"))
    specs = [dict(x, flow=f.get("id")) for f in reg.get("flows", []) for x in f.get("extractors", [])] + list(reg.get("extractors", []))
    for r in extract_all(args.minime, args.rev, specs):
        state = f"{len(stage_names(r))} name(s)" if r["found"] else f"not found: {r['reason']}"
        print(f"{r['id']:<22} {r['file']}::{r['name']}  ->  {state}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
