#!/usr/bin/env python3
"""Chapter <-> code links, build half (patch P15). Standard library only; pure (reads and writes nothing itself).

`build_index.py` hands this module the chapter HTML, the census paths and symbols; it returns three documents that
`build_index.py` writes under data/index/:

  linkables.json    what the browser may turn into a link, looked up by the exact text of a <code> span:
                      {"links":    {text: target},                  one answer everywhere
                       "choices":  {text: [target, ...]},           several candidates; the reader picks
                       "sections": {"doc-x.html#heading-id": {text: target}}}   answers that depend on the section
                    target = "path[::qual][@start[-end]]" for a file / symbol / line range, "folder/" for a folder.
  mentions.json     the other direction, for the Explorer's "Discussed in the book":
                      {"chapters": [{"url", "title"}],
                       "mentions": {"path" | "path::qual": [{"c": chapter index, "id": heading id, "h": heading, "s": snippet, "n": count}]}}
  link-report.json  how much of each chapter resolved, and what did not (so aliases can be added where it matters).

Only text inside <code> is linked, never plain prose (too error-prone), and never a <pre> block. A span resolves by these
rules, first match wins:

  1. an alias from content/link-aliases.json (the reader's own phrase -> target)
  2. an exact path, optionally with :line, :start-end or #L10-L20; or an exact folder
  3. a unique path suffix            (m2c/tui/app.py -> m2c/src/m2c/tui/app.py)
  4. path::qualified.name
  5. a unique class / function name, or Class.method; when several share the name, the ones outside test files
     if exactly one remains, and otherwise the one that lives in a file the same section already named
  otherwise it is left alone; a name with several candidates is offered as a choice.

Tokens shorter than four characters, dunder names and common words are never linked."""
from __future__ import annotations

import re
from collections import Counter, defaultdict
from html.parser import HTMLParser

MIN_LEN = 4
MAX_CHOICES = 8
SNIPPET = 150
EXTS = {"py", "pyi", "js", "jsx", "mjs", "cjs", "ts", "tsx", "json", "jsonc", "md", "yml", "yaml", "sql", "toml", "txt", "sh", "html", "css", "ini",
        "cfg", "lock", "ps1", "env", "example", "xml", "svg", "dockerfile"}
COMMON = {
    "true", "false", "none", "null", "self", "this", "main", "init", "name", "type", "types", "data", "text", "list", "dict", "json", "path", "file", "files",
    "line", "lines", "code", "test", "tests", "args", "kwargs", "value", "values", "result", "results", "error", "errors", "state", "config", "item", "items",
    "user", "users", "status", "message", "messages", "content", "index", "count", "size", "time", "date", "start", "stop", "next", "read", "write", "open",
    "close", "load", "save", "call", "make", "name", "keys", "key", "mode", "kind", "step", "steps", "task", "tasks", "plan", "role", "base", "meta", "info",
    "host", "port", "link", "links", "node", "nodes", "edge", "edges", "tool", "tools", "run", "runs", "stage", "wave", "chat", "memory", "agent", "agents",
    "model", "models", "input", "output", "event", "events", "query", "token", "tokens", "title", "label", "level", "scope", "group", "table", "field",
    "fields", "build", "check", "parse", "split", "join", "sort", "find", "head", "tail", "body", "page", "pages", "home", "root", "docs", "doc", "note", "notes",
}
_PATHISH = re.compile(r"^(?P<path>[A-Za-z0-9_@.+\-/]+?)(?:(?::|#L)(?P<s>\d+)(?:-L?(?P<e>\d+))?)?$")
_LINE_SUFFIX = re.compile(r"(?::|#L)\d+(?:-L?\d+)?$")
_QUALIFIED = re.compile(r"^(?P<path>[A-Za-z0-9_@.+\-/]+)::(?P<qual>[A-Za-z_]\w*(?:\.[A-Za-z_]\w*)*)$")
_IDENT = re.compile(r"^[A-Za-z_]\w*(?:\.[A-Za-z_]\w*)*$")


# ------------------------------------------------------------------ chapter html: <code> spans and their section
_BLOCK = {"p", "li", "td", "th", "dd", "dt", "tr", "h1", "h2", "h3", "h4", "div", "section", "article", "ul", "ol", "table", "blockquote", "br",
          "pre", "header", "footer", "details", "summary", "figure", "figcaption"}


class _Spans(HTMLParser):
    """The text of every <code> that is not inside <pre>, the id of the h2/h3 section it sits in, and a snippet of its block."""

    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.spans: list[dict] = []
        self.heading_text: dict[str, str] = {}
        self._skip = 0
        self._pre = 0
        self._code: list[str] | None = None
        self._section = ""
        self._head: tuple[str, list[str]] | None = None
        self._block: list[str] = []
        self._pending: list[tuple[int, str, str]] = []                    # (offset in block text, span text, section)

    def _flush(self) -> None:
        if self._pending:
            raw = "".join(self._block)
            for off, text, section in self._pending:
                self.spans[off]["snippet"] = _window(raw, text)
        self._block, self._pending = [], []

    def handle_starttag(self, tag, attrs):
        if tag in ("script", "style", "nav"):
            self._skip += 1
            return
        if self._skip:
            return
        if tag in _BLOCK:
            self._flush()
        if tag == "pre":
            self._pre += 1
        elif tag in ("h2", "h3") and self._head is None:
            hid = dict(attrs).get("id") or ""
            if hid:
                self._section = hid
            self._head = (hid, [])
        elif tag == "code" and not self._pre and self._code is None:
            self._code = []

    def handle_endtag(self, tag):
        if tag in ("script", "style", "nav"):
            self._skip = max(0, self._skip - 1)
            return
        if self._skip:
            return
        if tag == "code" and self._code is not None:
            text = "".join(self._code).strip()
            self._code = None
            if text:
                self.spans.append({"text": text, "section": self._section, "snippet": ""})
                self._pending.append((len(self.spans) - 1, text, self._section))
        elif tag == "pre":
            self._pre = max(0, self._pre - 1)
        elif tag in ("h2", "h3") and self._head is not None:
            hid, parts = self._head
            self._head = None
            if hid:
                self.heading_text.setdefault(hid, re.sub(r"\s*[#¶§]$", "", " ".join("".join(parts).split())))
        if tag in _BLOCK:
            self._flush()

    def handle_data(self, data):
        if self._skip:
            return
        if self._code is not None:
            self._code.append(data)
        if self._head is not None:
            self._head[1].append(data)
        if not self._pre:
            self._block.append(data)

    def close(self):
        super().close()
        self._flush()


def _window(raw: str, text: str) -> str:
    flat = " ".join(raw.split())
    i = flat.find(text)
    if i < 0:
        return flat[:SNIPPET]
    start = max(0, i - SNIPPET // 3)
    end = min(len(flat), start + SNIPPET)
    start = max(0, end - SNIPPET)
    out = flat[start:end].strip()
    return ("…" if start > 0 else "") + out + ("…" if end < len(flat) else "")


def parse_spans(html: str) -> _Spans:
    p = _Spans()
    p.feed(html)
    p.close()
    return p


# ------------------------------------------------------------------ the census side
def _is_test(path: str) -> bool:
    parts = path.split("/")
    name = parts[-1]
    return "tests" in parts[:-1] or "test" in parts[:-1] or name.startswith("test_") or name.endswith(("_test.py", ".test.js", ".test.ts", ".spec.js", ".spec.ts"))


class Index:
    """Paths, folders and symbols of the census, ready for lookups."""

    def __init__(self, paths: list[str], symbols: list[list]) -> None:
        self.paths = set(paths)
        self.dirs: set[str] = set()
        self.path_suffix: dict[str, list[str]] = defaultdict(list)
        self.dir_suffix: dict[str, list[str]] = defaultdict(list)
        for p in sorted(self.paths):
            parts = p.split("/")
            for i in range(len(parts)):
                self.path_suffix["/".join(parts[i:])].append(p)
            for i in range(1, len(parts)):
                d = "/".join(parts[:i])
                if d not in self.dirs:
                    self.dirs.add(d)
        for d in sorted(self.dirs):
            parts = d.split("/")
            for i in range(len(parts)):
                self.dir_suffix["/".join(parts[i:])].append(d)
        self.by_qual: dict[str, list[tuple[str, str]]] = defaultdict(list)
        self.by_name: dict[str, list[tuple[str, str]]] = defaultdict(list)
        self.quals: dict[str, set[str]] = defaultdict(set)
        for row in symbols:
            qual, path = row[0], row[1]
            if (path, qual) in self.quals.get(path, ()):
                continue
            self.quals[path].add(qual)
            self.by_qual[qual].append((path, qual))
            self.by_name[qual.rsplit(".", 1)[-1]].append((path, qual))


def _target(path: str, qual: str = "", start: str | None = None, end: str | None = None) -> str:
    out = path + (f"::{qual}" if qual else "")
    if start:
        out += f"@{start}" + (f"-{end}" if end and int(end) > int(start) else "")
    return out


def _linkable_word(word: str) -> bool:
    low = word.lower()
    return len(word) >= MIN_LEN and low not in COMMON and not word.startswith("__")


def _prefer_source(cands: list[tuple[str, str]]) -> list[tuple[str, str]]:
    src = [c for c in cands if not _is_test(c[0])]
    return src if len(src) == 1 else cands


# resolution result: ("link", target) | ("choices", [targets]) | ("name", [(path, qual)]) | ("skip", "") | ("none", "")
def resolve(text: str, ix: Index, aliases: dict[str, str]) -> tuple[str, object]:
    raw = text.strip()
    if raw.lower() in aliases:
        return "link", aliases[raw.lower()]
    word = raw[:-2] if raw.endswith("()") else raw
    if not word or " " in word or len(word) < MIN_LEN:
        return "skip", ""
    m = _QUALIFIED.match(word)
    if m:
        paths = _file_candidates(m["path"], ix)
        hits = [p for p in paths if m["qual"] in ix.quals.get(p, ())]
        if len(hits) == 1:
            return "link", _target(hits[0], m["qual"])
        return ("choices", sorted(_target(p, m["qual"]) for p in hits)[:MAX_CHOICES]) if hits else ("none", "")
    bare = _LINE_SUFFIX.sub("", word)                      # "deps.py:12-20" is a file with lines, whatever follows the last dot
    looks_path = "/" in word or (("." in bare) and bare.rsplit(".", 1)[-1].lower() in EXTS)
    if looks_path:
        pm = _PATHISH.match(word)
        if pm:
            p = pm["path"]
            if p.endswith("/") and p.rstrip("/") in ix.dirs:
                return "link", p.rstrip("/") + "/"
            p = p[2:] if p.startswith("./") else p
            if p.endswith("/"):
                ds = ix.dir_suffix.get(p.rstrip("/"), []) if p.count("/") >= 2 else []
                return ("link", ds[0] + "/") if len(ds) == 1 else ("none", "")
            cands = _file_candidates(p, ix)
            if len(cands) == 1:
                return "link", _target(cands[0], "", pm["s"], pm["e"])
            if len(cands) > 1:
                return "choices", sorted(_target(c, "", pm["s"], pm["e"]) for c in cands)[:MAX_CHOICES]
            if p in ix.dirs:
                return "link", p + "/"
            ds = ix.dir_suffix.get(p, []) if p.count("/") >= 1 else []
            if len(ds) == 1:
                return "link", ds[0] + "/"
            return "none", ""
    if not _IDENT.match(word):
        return "skip", ""
    last = word.rsplit(".", 1)[-1]
    if "." not in word:
        if not _linkable_word(word):
            return "skip", ""
        cands = list(dict.fromkeys(ix.by_name.get(word, [])))
    else:
        if not _linkable_word(last) and word not in ix.by_qual:
            return "skip", ""
        cands = list(dict.fromkeys(ix.by_qual.get(word, [])))
    if not cands:
        return "none", ""
    cands = _prefer_source(cands)
    return ("link", _target(*cands[0])) if len(cands) == 1 else ("name", cands)


def _file_candidates(p: str, ix: Index) -> list[str]:
    p = p[2:] if p.startswith("./") else p
    if p in ix.paths:
        return [p]
    return list(ix.path_suffix.get(p, []))


def load_aliases(raw, ix: Index) -> tuple[dict[str, str], list[str]]:
    """content/link-aliases.json: {"aliases": {phrase: target}} or the bare map. Targets that do not exist are reported, not linked."""
    table = raw.get("aliases") if isinstance(raw, dict) and isinstance(raw.get("aliases"), dict) else raw
    out: dict[str, str] = {}
    problems: list[str] = []
    if not isinstance(table, dict):
        return out, problems
    for phrase, target in sorted(table.items()):
        if phrase.startswith("_") or not isinstance(target, str):
            continue
        t = target.strip()
        base, _, qual = t.partition("::")
        base = re.sub(r"@\d+(?:-\d+)?$", "", base)
        ok = (base.rstrip("/") in ix.dirs) if base.endswith("/") else (base in ix.paths and (not qual or qual in ix.quals.get(base, ())))
        if ok:
            out[phrase.strip().lower()] = t
        else:
            problems.append(f'alias "{phrase}" points at {t}, which is not in the census')
    return out, problems


# ------------------------------------------------------------------ the whole thing
def _file_of(target: str) -> str:
    return re.sub(r"@\d+(?:-\d+)?$", "", target.split("::", 1)[0]) if not target.endswith("/") else ""


def collect_links(chapters: list[dict], paths: list[str], symbols: list[list], aliases_raw=None) -> dict[str, dict]:
    """chapters: [{"url", "title", "html"}]. Returns {"linkables": ..., "mentions": ..., "report": ...} (plain dicts)."""
    ix = Index(paths, symbols)
    aliases, alias_problems = load_aliases(aliases_raw, ix)
    links: dict[str, str] = {}
    choices: dict[str, list[str]] = {}
    sections: dict[str, dict[str, str]] = defaultdict(dict)
    mentions: dict[str, dict[tuple[int, str], dict]] = defaultdict(dict)
    report_chapters: list[dict] = []
    unresolved_all: Counter = Counter()

    for ci, ch in enumerate(chapters):
        parsed = parse_spans(ch["html"])
        spans = parsed.spans
        results = [resolve(s["text"], ix, aliases) for s in spans]
        # files a section has already named: they decide between several symbols of the same name
        named: dict[str, set[str]] = defaultdict(set)
        for s, (kind, val) in zip(spans, results):
            if kind == "link" and not str(val).endswith("/"):
                named[s["section"]].add(_file_of(str(val)))
            elif kind == "choices" and len({_file_of(v) for v in val}) == 1:
                named[s["section"]].add(_file_of(val[0]))
        stats = Counter()
        unresolved: Counter = Counter()
        for s, (kind, val) in zip(spans, results):
            stats["spans"] += 1
            text, sect = s["text"], s["section"]
            target = None
            if kind == "link":
                target = str(val)
                if text in links and links[text] != target:      # the same text, two different answers: do not guess
                    choices.setdefault(text, [])
                    choices[text] = sorted({links.pop(text), target} | set(choices[text]))[:MAX_CHOICES]
                    target = None
                elif text not in choices:
                    links[text] = target
                else:
                    target = None
            elif kind == "name":
                here = [c for c in val if c[0] in named.get(sect, ())]
                if len(here) == 1:
                    target = _target(*here[0])
                    sections[f"{ch['url']}#{sect}"][text] = target
                else:
                    choices[text] = sorted({_target(*c) for c in val})[:MAX_CHOICES]
                    stats["ambiguous"] += 1
                    continue
            elif kind == "choices":
                choices[text] = list(val)
                stats["ambiguous"] += 1
                continue
            elif kind == "skip":
                stats["skipped"] += 1
                continue
            else:
                stats["unresolved"] += 1
                unresolved[text] += 1
                unresolved_all[text] += 1
                continue
            if target is None:
                stats["ambiguous"] += 1
                continue
            stats["resolved"] += 1
            if not target.endswith("/"):
                path, _, qual = _file_of(target), "", ""
                key = target.split("@")[0] if "::" in target else path
                slot = mentions[key].setdefault((ci, sect), {"c": ci, "id": sect, "h": parsed.heading_text.get(sect, ""), "s": s["snippet"], "n": 0})
                slot["n"] += 1
        cand = stats["spans"] - stats["skipped"]
        report_chapters.append({
            "chapter": ch["url"], "title": ch["title"], "spans": stats["spans"], "resolved": stats["resolved"], "ambiguous": stats["ambiguous"],
            "unresolved": stats["unresolved"], "skipped": stats["skipped"],
            "pct": round(100 * stats["resolved"] / stats["spans"], 1) if stats["spans"] else 0.0,
            "pctOfCandidates": round(100 * stats["resolved"] / cand, 1) if cand else 0.0,
            "top_unresolved": [{"text": t, "n": n} for t, n in sorted(unresolved.items(), key=lambda kv: (-kv[1], kv[0]))[:15]],
        })

    for text in list(links):                                   # a text that is also a choice somewhere else is a choice everywhere
        if text in choices:
            choices[text] = sorted(set(choices[text]) | {links.pop(text)})[:MAX_CHOICES]
    total = Counter()
    for r in report_chapters:
        for k in ("spans", "resolved", "ambiguous", "unresolved", "skipped"):
            total[k] += r[k]
    cand_total = total["spans"] - total["skipped"]
    return {
        "linkables": {"links": dict(sorted(links.items())), "choices": dict(sorted(choices.items())),
                      "sections": {k: dict(sorted(v.items())) for k, v in sorted(sections.items())}},
        "mentions": {"chapters": [{"url": c["url"], "title": c["title"]} for c in chapters],
                     "mentions": {k: sorted(v.values(), key=lambda m: (m["c"], m["id"])) for k, v in sorted(mentions.items())}},
        "report": {
            "summary": {**{k: total[k] for k in ("spans", "resolved", "ambiguous", "unresolved", "skipped")},
                        "pct": round(100 * total["resolved"] / total["spans"], 1) if total["spans"] else 0.0,
                        "pctOfCandidates": round(100 * total["resolved"] / cand_total, 1) if cand_total else 0.0},
            "chapters": report_chapters,
            "unresolved": [{"text": t, "n": n} for t, n in sorted(unresolved_all.items(), key=lambda kv: (-kv[1], kv[0]))[:80]],
            "aliasProblems": alias_problems,
        },
    }
