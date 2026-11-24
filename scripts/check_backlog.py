#!/usr/bin/env python3
"""
check_backlog.py -- keep data/docs/upgrade_backlog.md (Appendix C, the upgrade backlog) in its shape.
Standard library only.

    python scripts/check_backlog.py --check                        # validate; also prove the generated parts are current
    python scripts/check_backlog.py --write                        # regenerate sections 0, 1 and 2 from the entries
    python scripts/check_backlog.py --list [--status S] [--product P]
    python scripts/check_backlog.py --next-id                      # the next free feature id
    python scripts/check_backlog.py --set-status UB-007 accepted --note "why"

How the document is built
    The ENTRIES are the truth: one "### UB-nnn: Title (Size)" block per feature, grouped under
    "## Batch Bnn (YYYY-MM-DD): what this batch added" headings at the end of the file.
    Sections "0. At a glance", "1. Register" and "2. Batches" near the top are GENERATED from the entries by
    --write, so the top table can never disagree with the details. Everything else is written by hand.

An entry looks like this (the order of the paragraphs is free; the heading and the first two lines are fixed):

    ### UB-001: Short feature title (M)

    > One line for the register table (140 characters at most, no "|").

    **Product** MiniMe · **Source** a repo, a plan section or "my idea" · **Status** candidate · **Depends** — · **Decision** none · **Evidence** [V]

    **What.** ...   **Why.** ...   **Where.** ...   **How.** ...   **Done when.** ...   (optional) **Notes.** ...

    The fields on the metadata line are separated by " · " (a middle dot). Depends is "—" or feature ids.
    A parked or dropped feature must carry a **Notes.** paragraph that says why.

Errors (exit 1)
    shape        a required piece is missing or wrong: heading, short line, metadata field, paragraph, vocabulary
    id           a duplicate id, an id that does not increase, a Depends that points nowhere or loops, an unknown
                 UB-nnn mentioned anywhere in the document
    batch        an entry outside a batch, a batch without entries, bad or out-of-order batch id or date
    tables       the hand-written tables (sources register, decision log) have a bad row
    stale        sections 0-2 differ from what --write would produce (run --write)
    text         a carriage return anywhere in the file
"""
import argparse
import datetime
import re
import sys
from pathlib import Path

sys.dont_write_bytecode = True      # scripts/__pycache__ is tracked; do not make it show as modified

ROOT = Path(__file__).resolve().parent.parent
DOC = ROOT / "data" / "docs" / "upgrade_backlog.md"

PRODUCTS = ("MiniMe", "M2C", "Menux", "Shared", "Book")
STATUSES = ("candidate", "accepted", "building", "done", "parked", "dropped")
SIZES = ("XS", "S", "M", "L", "XL")
META_KEYS = ("Product", "Source", "Status", "Depends", "Decision", "Evidence")
PARAGRAPHS = ("What", "Why", "Where", "How", "Done when")        # required
OPTIONAL_PARAGRAPHS = ("Notes",)
SHORT_MAX = 140
DASH = "\u2014"

ENTRY_RE = re.compile(r"^### (UB-\d{3}): (.+) \((XS|S|M|L|XL)\)\s*$")
ENTRY_LIKE_RE = re.compile(r"^### UB-")
BATCH_RE = re.compile(r"^## Batch (B\d{2}) \((\d{4}-\d{2}-\d{2})\): (.+?)\s*$")
BATCH_LIKE_RE = re.compile(r"^## Batch\b")
ID_RE = re.compile(r"\bUB-\d{3}\b")
PARA_RE = re.compile(r"^\*\*(What|Why|Where|How|Done when|Notes)\.\*\*")
META_SPLIT_RE = re.compile(r"\s+\u00b7\s+(?=\*\*)")
META_FIELD_RE = re.compile(r"^\*\*([A-Za-z]+)\*\*\s*(.*)$")

GENERATED = (("0. At a glance", "glance"), ("1. Register", "register"), ("2. Batches", "batches"))
SOURCES_HEADING = "7. Sources register"
LOG_HEADING = "8. Decision log"
LOG_HEADER = "| Date | ID | Change | Note |"
GEN_NOTE = "*Generated from the entries by `python scripts/check_backlog.py --write`. Do not edit by hand.*"


class Entry:
    def __init__(self, uid, title, size, line):
        self.id = uid
        self.title = title
        self.size = size
        self.line = line            # 1-based line of the heading
        self.batch = None
        self.short = ""
        self.meta = {}
        self.meta_line = None       # 0-based index of the metadata line in the file
        self.paragraphs = {}
        self.lines = []             # the entry's body lines (without the heading)

    @property
    def number(self):
        return int(self.id[3:])

    @property
    def depends(self):
        raw = self.meta.get("Depends", "").strip()
        if raw in ("", DASH, "-", "none"):
            return []
        return [p for p in re.split(r"[,\s]+", raw) if p]


class Batch:
    def __init__(self, bid, date, title, line):
        self.id, self.date, self.title, self.line = bid, date, title, line
        self.entries = []


class Doc:
    def __init__(self, lines):
        self.lines = lines
        self.entries = []
        self.batches = []
        self.problems = []

    def problem(self, kind, line, message):
        where = f"line {line}" if line else "document"
        self.problems.append(f"{kind}: {where}: {message}")


def read_lines(path):
    # raw bytes, not read_text(): text mode would turn CRLF into LF and hide a Windows line ending
    text = Path(path).read_bytes().decode("utf-8")
    return text.split("\n")


FENCE_RE = re.compile(r"^(`{3,}|~{3,})")


def fenced(lines):
    """Indexes of the lines inside a fenced code block (the fence lines included). Headings, ids and tables in a
    code example are not part of the document's structure."""
    mask = set()
    marker = None
    for i, ln in enumerate(lines):
        m = FENCE_RE.match(ln)
        if marker is None:
            if m:
                marker = m.group(1)[0] * len(m.group(1))
                mask.add(i)
        else:
            mask.add(i)
            if m and m.group(1)[0] == marker[0] and len(m.group(1)) >= len(marker) and ln.strip() == m.group(1):
                marker = None
    return mask


def clean_cell(text):
    return text.replace("|", "/").strip()


def parse(lines):
    """Read the document into a Doc. Collects problems; never raises on a malformed document."""
    doc = Doc(lines)
    if any("\r" in ln for ln in lines):
        doc.problem("text", None, "carriage return found (the file must use LF line endings)")
        lines = [ln.replace("\r", "") for ln in lines]
        doc.lines = lines
    if not lines or not lines[0].startswith("# "):
        doc.problem("shape", 1, "the first line must be the document title (\"# ...\")")

    current_batch = None
    current = None
    skip = fenced(lines)
    for i, ln in enumerate(lines):
        n = i + 1
        if i in skip:
            if current is not None:
                current.lines.append((i, ln))
            continue
        if ln.startswith("## "):
            current = None
            m = BATCH_RE.match(ln)
            if m:
                bid, date, title = m.groups()
                try:
                    datetime.date.fromisoformat(date)
                except ValueError:
                    doc.problem("batch", n, f"{bid}: \"{date}\" is not a real date")
                current_batch = Batch(bid, date, title, n)
                doc.batches.append(current_batch)
            elif BATCH_LIKE_RE.match(ln):
                doc.problem("batch", n, "a batch heading must read \"## Batch B01 (YYYY-MM-DD): what it added\"")
                current_batch = None
            else:
                # any other level-2 heading ends the entries of the batch above it
                if current_batch is not None and not ln.startswith("## Batch"):
                    current_batch = None
            continue
        if ln.startswith("### "):
            current = None
            m = ENTRY_RE.match(ln)
            if m:
                uid, title, size = m.groups()
                e = Entry(uid, title.strip(), size, n)
                if current_batch is None:
                    doc.problem("batch", n, f"{uid} is not inside a batch (\"## Batch Bnn (date): ...\")")
                else:
                    e.batch = current_batch.id
                    current_batch.entries.append(e)
                doc.entries.append(e)
                current = e
            elif ENTRY_LIKE_RE.match(ln):
                doc.problem("shape", n, "an entry heading must read \"### UB-001: Title (XS|S|M|L|XL)\"")
            continue
        if current is not None:
            current.lines.append((i, ln))

    for e in doc.entries:
        read_entry(doc, e)
    return doc


def read_entry(doc, e):
    body = e.lines
    # short line: the first "> " line
    for i, ln in body:
        if ln.startswith("> "):
            e.short = ln[2:].strip()
            break
    # metadata line
    for i, ln in body:
        if ln.startswith("**Product**"):
            e.meta_line = i
            for part in META_SPLIT_RE.split(ln.strip()):
                m = META_FIELD_RE.match(part.strip())
                if not m:
                    doc.problem("shape", i + 1, f"{e.id}: cannot read the metadata field \"{part[:40]}\"")
                    continue
                key, value = m.group(1), m.group(2).strip()
                if key in e.meta:
                    doc.problem("shape", i + 1, f"{e.id}: the metadata field {key} appears twice")
                e.meta[key] = value
            break
    # paragraphs
    name = None
    buf = []
    for i, ln in body:
        m = PARA_RE.match(ln)
        if m:
            if name is not None:
                e.paragraphs[name] = "\n".join(buf).strip()
            name = m.group(1)
            if name in e.paragraphs:
                doc.problem("shape", i + 1, f"{e.id}: the paragraph {name} appears twice")
            buf = [ln[m.end():]]
        elif name is not None:
            buf.append(ln)
    if name is not None:
        e.paragraphs[name] = "\n".join(buf).strip()


def validate(doc):
    P = doc.problem
    ids = {}
    last_number = 0
    for e in doc.entries:
        if e.id in ids:
            P("id", e.line, f"{e.id} is used twice (first at line {ids[e.id].line}); ids are never reused")
        else:
            ids[e.id] = e
            if e.number <= last_number:
                P("id", e.line, f"{e.id} must be higher than the id above it (UB-{last_number:03d}); entries stay in id order")
        last_number = max(last_number, e.number)

        for field, value in (("title", e.title),):
            if "|" in value:
                P("shape", e.line, f"{e.id}: the title cannot contain \"|\"")
        if not e.short:
            P("shape", e.line, f"{e.id}: the line \"> one-line summary\" is missing")
        elif len(e.short) > SHORT_MAX:
            P("shape", e.line, f"{e.id}: the one-line summary is {len(e.short)} characters (limit {SHORT_MAX})")
        elif "|" in e.short:
            P("shape", e.line, f"{e.id}: the one-line summary cannot contain \"|\"")

        if e.meta_line is None:
            P("shape", e.line, f"{e.id}: the metadata line (starting with **Product**) is missing")
        else:
            for key in META_KEYS:
                if not e.meta.get(key):
                    P("shape", e.meta_line + 1, f"{e.id}: metadata field {key} is missing or empty")
            for key in e.meta:
                if key not in META_KEYS:
                    P("shape", e.meta_line + 1, f"{e.id}: unknown metadata field {key}")
            if e.meta.get("Product") and e.meta["Product"] not in PRODUCTS:
                P("shape", e.meta_line + 1, f"{e.id}: Product \"{e.meta['Product']}\" is not one of {', '.join(PRODUCTS)}")
            if e.meta.get("Status") and e.meta["Status"] not in STATUSES:
                P("shape", e.meta_line + 1, f"{e.id}: Status \"{e.meta['Status']}\" is not one of {', '.join(STATUSES)}")
            if "|" in e.meta.get("Source", ""):
                P("shape", e.meta_line + 1, f"{e.id}: Source cannot contain \"|\"")

        for name in PARAGRAPHS:
            if not e.paragraphs.get(name):
                P("shape", e.line, f"{e.id}: the paragraph **{name}.** is missing or empty")
        if e.meta.get("Status") in ("parked", "dropped") and not e.paragraphs.get("Notes"):
            P("shape", e.line, f"{e.id}: a {e.meta['Status']} feature needs a **Notes.** paragraph that says why")

    for e in doc.entries:
        for dep in e.depends:
            if not re.fullmatch(r"UB-\d{3}", dep):
                P("id", e.line, f"{e.id}: Depends \"{dep}\" is not a feature id")
            elif dep not in ids:
                P("id", e.line, f"{e.id}: Depends on {dep}, which does not exist")
            elif dep == e.id:
                P("id", e.line, f"{e.id}: depends on itself")
    # cycles
    graph = {e.id: [d for d in e.depends if d in ids and d != e.id] for e in doc.entries}
    state = {}

    def visit(node, path):
        state[node] = 1
        for nxt in graph.get(node, []):
            if state.get(nxt) == 1:
                P("id", ids[node].line, "Depends loop: " + " -> ".join(path + [node, nxt]))
            elif nxt not in state:
                visit(nxt, path + [node])
        state[node] = 2

    for node in list(graph):
        if node not in state:
            visit(node, [])

    # unknown ids mentioned anywhere
    skip = fenced(doc.lines)
    for i, ln in enumerate(doc.lines):
        if i in skip:
            continue
        for m in ID_RE.finditer(ln):
            if m.group(0) not in ids and not ENTRY_LIKE_RE.match(ln):
                P("id", i + 1, f"{m.group(0)} is mentioned but there is no such entry")

    # batches
    seen = set()
    last_date = None
    last_bnum = 0
    for b in doc.batches:
        if b.id in seen:
            P("batch", b.line, f"{b.id} appears twice")
        seen.add(b.id)
        bnum = int(b.id[1:])
        if bnum <= last_bnum:
            P("batch", b.line, f"{b.id} must be higher than the batch above it (B{last_bnum:02d})")
        last_bnum = max(last_bnum, bnum)
        try:
            d = datetime.date.fromisoformat(b.date)
            if last_date and d < last_date:
                P("batch", b.line, f"{b.id} is dated before the batch above it")
            last_date = d
        except ValueError:
            pass
        if not b.entries:
            P("batch", b.line, f"{b.id} has no entries")

    validate_tables(doc, ids)
    return doc.problems


def section_bounds(lines, heading):
    """(start, end) line indexes of the H2 section whose heading text starts with `heading`; end is exclusive.
    start is the heading line itself. None when the section is missing."""
    skip = fenced(lines)
    start = None
    for i, ln in enumerate(lines):
        if i not in skip and ln.startswith("## ") and ln[3:].startswith(heading):
            start = i
            break
    if start is None:
        return None
    end = len(lines)
    for j in range(start + 1, len(lines)):
        if j not in skip and lines[j].startswith("## "):
            end = j
            break
    return start, end


def table_rows(lines, start, end):
    """Rows (list of cells) of the first table found between start and end; header and separator skipped."""
    rows = []
    in_table = False
    for i in range(start, end):
        ln = lines[i]
        if ln.startswith("|"):
            in_table = True
            cells = [c.strip() for c in ln.strip().strip("|").split("|")]
            rows.append((i + 1, cells))
        elif in_table:
            break
    return rows[2:] if len(rows) >= 2 else []


def validate_tables(doc, ids):
    P = doc.problem
    b = section_bounds(doc.lines, SOURCES_HEADING)
    if b is None:
        P("tables", None, f"the section \"## {SOURCES_HEADING}\" is missing")
    else:
        names = set()
        for n, cells in table_rows(doc.lines, *b):
            if len(cells) != 6:
                P("tables", n, f"a sources row needs 6 cells (Source, Link, Reported licence, Verdict, Used in, Checked); found {len(cells)}")
                continue
            name, _link, _lic, _verdict, used, checked = cells
            if not name:
                P("tables", n, "a sources row has no source name")
            if name.lower() in names:
                P("tables", n, f"the source \"{name}\" is listed twice")
            names.add(name.lower())
            if not checked:
                P("tables", n, f"the source \"{name}\" has an empty Checked cell (write \"{DASH}\" if you have not looked yet)")
            if not used:
                P("tables", n, f"the source \"{name}\" has an empty Used in cell (write \"{DASH}\" if no feature uses it)")
    b = section_bounds(doc.lines, LOG_HEADING)
    if b is None:
        P("tables", None, f"the section \"## {LOG_HEADING}\" is missing")
    else:
        if LOG_HEADER not in doc.lines[b[0]:b[1]]:
            P("tables", b[0] + 1, f"the decision log table header must be exactly: {LOG_HEADER}")
        for n, cells in table_rows(doc.lines, *b):
            if len(cells) != 4:
                P("tables", n, f"a decision log row needs 4 cells (Date, ID, Change, Note); found {len(cells)}")
                continue
            date, uid, change, _note = cells
            try:
                datetime.date.fromisoformat(date)
            except ValueError:
                P("tables", n, f"\"{date}\" is not a date (YYYY-MM-DD)")
            if uid != DASH and uid not in ids:
                P("tables", n, f"the decision log names {uid}, which does not exist (use \"{DASH}\" for a general decision)")
            if not change:
                P("tables", n, "a decision log row has an empty Change cell")


def counts(doc):
    by = {p: {s: 0 for s in STATUSES} for p in PRODUCTS}
    for e in doc.entries:
        p, s = e.meta.get("Product"), e.meta.get("Status")
        if p in by and s in by[p]:
            by[p][s] += 1
    return by


def gen_glance(doc):
    by = counts(doc)
    total = sum(sum(v.values()) for v in by.values())
    per_status = {s: sum(by[p][s] for p in PRODUCTS) for s in STATUSES}
    lines = [GEN_NOTE, ""]
    batches = len(doc.batches)
    lines.append(f"**{total} features** in {batches} batch{'es' if batches != 1 else ''}: "
                 + " \u00b7 ".join(f"{per_status[s]} {s}" for s in STATUSES) + ".")
    lines.append("")
    lines.append("| Product | " + " | ".join(STATUSES) + " | Total |")
    lines.append("|---|" + "---|" * (len(STATUSES) + 1))
    for p in PRODUCTS:
        row = by[p]
        lines.append(f"| {p} | " + " | ".join(str(row[s]) for s in STATUSES) + f" | {sum(row.values())} |")
    lines.append("| **All** | " + " | ".join(f"**{per_status[s]}**" for s in STATUSES) + f" | **{total}** |")
    return lines


def gen_register(doc):
    lines = [GEN_NOTE, "",
             "| ID | Feature | In short | Product | Source | Size | Status | Batch |",
             "|---|---|---|---|---|---|---|---|"]
    for e in sorted(doc.entries, key=lambda x: x.number):
        lines.append("| " + " | ".join([
            e.id, clean_cell(e.title), clean_cell(e.short), clean_cell(e.meta.get("Product", "")),
            clean_cell(e.meta.get("Source", "")), e.size, clean_cell(e.meta.get("Status", "")), e.batch or DASH]) + " |")
    return lines


def gen_batches(doc):
    lines = [GEN_NOTE, "", "| Batch | Date | What it added | Features | IDs |", "|---|---|---|---|---|"]
    for b in doc.batches:
        ids = sorted(e.number for e in b.entries)
        if not ids:
            span = DASH
        elif len(ids) == 1:
            span = f"UB-{ids[0]:03d}"
        else:
            span = f"UB-{ids[0]:03d} to UB-{ids[-1]:03d}"
        lines.append(f"| {b.id} | {b.date} | {clean_cell(b.title)} | {len(b.entries)} | {span} |")
    return lines


GENERATORS = {"glance": gen_glance, "register": gen_register, "batches": gen_batches}


def regenerate(doc):
    """The document's lines with sections 0-2 rewritten from the entries. Returns None when a section is missing."""
    lines = list(doc.lines)
    for heading, key in GENERATED:
        b = section_bounds(lines, heading)
        if b is None:
            return None
        start, end = b
        new = ["", *GENERATORS[key](doc), ""]
        lines[start + 1:end] = new
    return lines


def check(path):
    doc = parse(read_lines(path))
    problems = validate(doc)
    for heading, _ in GENERATED:
        if section_bounds(doc.lines, heading) is None:
            problems.append(f"shape: document: the generated section \"## {heading}\" is missing")
    if not problems:
        fresh = regenerate(doc)
        if fresh != doc.lines:
            problems.append("stale: sections 0, 1 and 2 are out of date; run: python scripts/check_backlog.py --write")
    return doc, problems


def write(path):
    doc = parse(read_lines(path))
    problems = validate(doc)
    for heading, _ in GENERATED:
        if section_bounds(doc.lines, heading) is None:
            problems.append(f"shape: document: the generated section \"## {heading}\" is missing")
    if problems:
        return doc, problems, False
    fresh = regenerate(doc)
    changed = fresh != doc.lines
    if changed:
        with open(path, "w", encoding="utf-8", newline="\n") as fh:
            fh.write("\n".join(fresh))
    return doc, [], changed


def set_status(path, uid, status, note="", date=None):
    if status not in STATUSES:
        return [f"shape: status \"{status}\" is not one of {', '.join(STATUSES)}"]
    doc = parse(read_lines(path))
    problems = validate(doc)
    if problems:
        return problems
    entry = next((e for e in doc.entries if e.id == uid), None)
    if entry is None:
        return [f"id: {uid} does not exist"]
    old = entry.meta["Status"]
    if old == status:
        return [f"shape: {uid} is already {status}"]
    if status in ("parked", "dropped") and not entry.paragraphs.get("Notes") and not note:
        return [f"shape: say why with --note (a {status} feature needs a reason)"]
    lines = list(doc.lines)
    ml = lines[entry.meta_line]
    lines[entry.meta_line] = re.sub(r"(\*\*Status\*\*\s+)\S+", lambda m: m.group(1) + status, ml, count=1)
    if status in ("parked", "dropped") and not entry.paragraphs.get("Notes"):
        # add a Notes paragraph at the end of the entry body so the shape stays valid
        last = max(i for i, _ in entry.lines)
        while last > entry.line - 1 and not lines[last].strip():
            last -= 1
        lines[last + 1:last + 1] = ["", f"**Notes.** {note.strip()}"]
    date = date or datetime.date.today().isoformat()
    try:
        datetime.date.fromisoformat(date)
    except ValueError:
        return [f"shape: \"{date}\" is not a date (YYYY-MM-DD)"]
    b = section_bounds(lines, LOG_HEADING)
    if b is None:
        return [f"tables: the section \"## {LOG_HEADING}\" is missing"]
    start, end = b
    last_row = None
    for i in range(start, end):
        if lines[i].startswith("|"):
            last_row = i
    if last_row is None:
        return [f"tables: the decision log has no table"]
    lines.insert(last_row + 1, f"| {date} | {uid} | {old} -> {status} | {clean_cell(note) or DASH} |")
    with open(path, "w", encoding="utf-8", newline="\n") as fh:
        fh.write("\n".join(lines))
    doc2, problems, _ = write(path)
    return problems


def next_id(doc):
    return f"UB-{max([e.number for e in doc.entries] or [0]) + 1:03d}"


def main(argv=None):
    ap = argparse.ArgumentParser(description="Validate and regenerate data/docs/upgrade_backlog.md.")
    ap.add_argument("--doc", default=str(DOC), help="path of the backlog document (default: data/docs/upgrade_backlog.md)")
    mode = ap.add_mutually_exclusive_group()
    mode.add_argument("--check", action="store_true", help="validate and prove the generated sections are current (default)")
    mode.add_argument("--write", action="store_true", help="regenerate sections 0, 1 and 2 from the entries")
    mode.add_argument("--list", action="store_true", help="print the register in the terminal")
    mode.add_argument("--next-id", action="store_true", help="print the next free feature id")
    mode.add_argument("--set-status", nargs=2, metavar=("ID", "STATUS"), help="change a feature's status and log it")
    ap.add_argument("--status", help="with --list: only this status")
    ap.add_argument("--product", help="with --list: only this product")
    ap.add_argument("--note", default="", help="with --set-status: the reason, written into the decision log")
    ap.add_argument("--date", help="with --set-status: the date of the decision (default: today)")
    args = ap.parse_args(argv)

    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    path = Path(args.doc)
    if not path.exists():
        print(f"check_backlog: {path} does not exist")
        return 1

    if args.write:
        doc, problems, changed = write(path)
        if problems:
            print("\n".join(problems))
            print(f"check_backlog: not written, {len(problems)} problem(s)")
            return 1
        print(f"check_backlog: {len(doc.entries)} features, sections 0-2 " + ("rewritten" if changed else "already current"))
        return 0

    if args.set_status:
        uid, status = args.set_status
        problems = set_status(path, uid, status, args.note, args.date)
        if problems:
            print("\n".join(problems))
            return 1
        print(f"check_backlog: {uid} is now {status}; decision logged and sections 0-2 regenerated")
        return 0

    doc = parse(read_lines(path))
    if args.next_id:
        print(next_id(doc))
        return 0
    if args.list:
        for e in sorted(doc.entries, key=lambda x: x.number):
            if args.status and e.meta.get("Status") != args.status:
                continue
            if args.product and e.meta.get("Product") != args.product:
                continue
            print(f"{e.id}  {e.size:<2}  {e.meta.get('Status', '?'):<9}  {e.meta.get('Product', '?'):<6}  {e.title}")
        return 0

    doc, problems = check(path)
    if problems:
        print("\n".join(problems))
        print(f"check_backlog: {len(problems)} problem(s)")
        return 1
    print(f"check_backlog: {len(doc.entries)} features in {len(doc.batches)} batch(es) -> 0 problems")
    return 0


if __name__ == "__main__":
    sys.exit(main())
