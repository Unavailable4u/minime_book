#!/usr/bin/env python3
"""
retire_legacy.py -- retire the hand-made archify diagrams in architecture/ once a generated view can replace them (P23).
Standard library only.

    python scripts/retire_legacy.py status            # legacy page -> view -> flow status -> ready?
    python scripts/retire_legacy.py --apply           # retire every page that is ready
    python scripts/retire_legacy.py --apply --dry-run # say what would change, change nothing
    python scripts/retire_legacy.py --check           # exit 1 if a page is ready but not retired yet

Why conditional. The eight diagrams in architecture/ were drawn once (2026-10-07) and never updated. Three views are
derived from the census alone (system, dataflow, api-surface), so they can replace their diagram at any time. The other
five (task-pipeline, task-sequence, taskrun-lifecycle, workspace-lifecycle, daemon-approval) are traced by Copilot
(UPDATING.md, Step 2c). Until their flow is written the view shows only boxes and "flow not written yet", and four of the
old diagrams are embedded in the book as figures, so they stay. Run this again after `python scripts/update_all.py` has
ingested a flow.

A page is READY when its view is in data/arch/model.json with a status other than "missing".

Retiring a page does five things (all idempotent):
  1. architecture/<x>.html becomes a thin redirect page to architecture.html#<view> (the URL stays valid)
  2. its entry moves from "pages" to "retired" in content/arch-legacy.json (the System page lists only "pages")
  3. figures of type "archify" that embed it become type "arch" (view=<view>) in content/figures/*.json
  4. "diagram" links in content/topology.json and content/system/*.json now point at architecture.html#<view>
  5. its "replaces" is dropped from content/arch-flows.json, and `scripts/arch.py build` refreshes data/arch/*
When the last page is retired the "archify" figure type is unused: delete it from assets/js/figures.js and scripts/test_figures.py.

Line endings are preserved (CRLF checkouts stay CRLF), like the other scripts.
"""
import argparse
import html as _html
import json
import subprocess
import sys
from pathlib import Path

sys.dont_write_bytecode = True      # the repo tracks scripts/__pycache__; do not make it show as modified

ROOT = Path(__file__).resolve().parent.parent
REGISTRY = "content/arch-legacy.json"
MODEL = "data/arch/model.json"
FLOWS_REGISTRY = "content/arch-flows.json"
FIGURES_DIR = "content/figures"
DIAGRAM_FILES = ("content/topology.json", "content/system")     # a file, or a folder of *.json
SUFFIX = "MiniMe Atlas"
PAGE_MAX_BYTES = 2048


def read_lf(path):
    """Read a text file as LF, remembering whether it used CRLF."""
    raw = Path(path).read_bytes().decode("utf-8-sig")
    return raw.replace("\r\n", "\n"), "\r\n" in raw


def to_native(text, crlf):
    return text.replace("\n", "\r\n") if crlf else text


def _indent_of(text, data):
    """The indent (1 or 2) that reproduces `text` from `data`; 2 when neither does."""
    for ind in (2, 1):
        if json.dumps(data, indent=ind, ensure_ascii=False) + "\n" == text:
            return ind
    return 2


def load_json(root, rel):
    text, crlf = read_lf(Path(root) / rel)
    data = json.loads(text)
    return data, _indent_of(text, data), crlf


def dump_json(root, rel, data, indent, crlf):
    text = json.dumps(data, indent=indent, ensure_ascii=False) + "\n"
    Path(root, rel).write_bytes(to_native(text, crlf).encode("utf-8"))


# ------------------------------------------------------------------ the facts
def view_status(root):
    """{view id: status} from data/arch/model.json ("derived", "missing", "fresh", "stale", ...)."""
    try:
        model = json.loads(Path(root, MODEL).read_bytes().decode("utf-8-sig"))
    except (OSError, ValueError):
        return {}
    return {v["id"]: v.get("status", "") for v in model.get("views", []) if isinstance(v, dict) and "id" in v}


def is_ready(entry, statuses):
    st = statuses.get(entry["view"])
    return st is not None and st != "missing"


def redirect_page(title, view):
    """The thin page that stands in for a retired diagram: no external resources, works without JavaScript."""
    target = f"../architecture.html#{view}"
    t = _html.escape(f"{title} · {SUFFIX}", quote=True)
    return (
        '<!doctype html>\n<html lang="en"><head><meta charset="utf-8">\n'
        '<meta name="viewport" content="width=device-width,initial-scale=1">\n'
        '<meta name="robots" content="noindex,nofollow">\n'
        f"<title>{t}</title>\n"
        f'<link rel="canonical" href="{target}">\n'
        f'<meta http-equiv="refresh" content="0; url={target}">\n'
        f"<script>location.replace({json.dumps(target)})</script>\n"
        "</head><body>\n"
        "<p>This hand-made diagram has been replaced by a diagram generated from the code.\n"
        f'<a href="{target}">Open it on the System page</a>.</p>\n'
        "</body></html>\n"
    )


# ------------------------------------------------------------------ the work
def _swap_figures(root, file, view, dry):
    changed = []
    base = Path(root, FIGURES_DIR)
    for p in sorted(base.glob("*.json")) if base.is_dir() else []:
        rel = p.relative_to(root).as_posix()
        data, ind, crlf = load_json(root, rel)
        hit = False
        for i, f in enumerate(data.get("figures", [])):
            if isinstance(f, dict) and f.get("type") == "archify" and f.get("src") == file:
                new = {}
                for k, v in f.items():
                    if k in ("src", "size"):
                        continue
                    new[k] = v
                    if k == "type":
                        new["type"], new["view"] = "arch", view
                data["figures"][i] = new
                hit = True
        if hit:
            changed.append(rel)
            if not dry:
                dump_json(root, rel, data, ind, crlf)
    return changed


def _retarget(node, file, to):
    """Replace every "diagram": <file> in a JSON tree; returns the number of replacements."""
    n = 0
    if isinstance(node, dict):
        for k, v in node.items():
            if k == "diagram" and v == file:
                node[k] = to
                n += 1
            else:
                n += _retarget(v, file, to)
    elif isinstance(node, list):
        for v in node:
            n += _retarget(v, file, to)
    return n


def _retarget_links(root, file, view, dry):
    changed = []
    paths = []
    for rel in DIAGRAM_FILES:
        p = Path(root, rel)
        paths += sorted(p.glob("*.json")) if p.is_dir() else ([p] if p.is_file() else [])
    for p in paths:
        rel = p.relative_to(root).as_posix()
        data, ind, crlf = load_json(root, rel)
        if _retarget(data, file, f"architecture.html#{view}"):
            changed.append(rel)
            if not dry:
                dump_json(root, rel, data, ind, crlf)
    return changed


def _drop_replaces(root, file, dry):
    if not Path(root, FLOWS_REGISTRY).is_file():
        return []
    data, ind, crlf = load_json(root, FLOWS_REGISTRY)
    hit = False
    for key in ("flows", "views"):
        for x in data.get(key, []):
            if isinstance(x, dict) and x.get("replaces") == file:
                del x["replaces"]
                hit = True
    if hit and not dry:
        dump_json(root, FLOWS_REGISTRY, data, ind, crlf)
    return [FLOWS_REGISTRY] if hit else []


def retire(root, dry=False):
    """Retire every ready page. Returns (retired entries, touched files). Idempotent."""
    root = Path(root)
    reg, ind, crlf = load_json(root, REGISTRY)
    statuses = view_status(root)
    done, touched = [], []
    for entry in list(reg.get("pages", [])):
        if not is_ready(entry, statuses):
            continue
        f, view = entry["file"], entry["view"]
        done.append(entry)
        touched.append(f)
        touched += _swap_figures(root, f, view, dry)
        touched += _retarget_links(root, f, view, dry)
        touched += _drop_replaces(root, f, dry)
        if not dry:
            Path(root, f).write_bytes(to_native(redirect_page(entry["title"], view), crlf_of(root, f)).encode("utf-8"))
    if done and not dry:
        gone = {e["file"] for e in done}
        reg["pages"] = [e for e in reg["pages"] if e["file"] not in gone]
        reg.setdefault("retired", []).extend(done)
        reg["retired"].sort(key=lambda e: e["file"])
        dump_json(root, REGISTRY, reg, ind, crlf)
        touched.append(REGISTRY)
    return done, sorted(set(touched))


def crlf_of(root, rel):
    """Whether the existing file used CRLF (the redirect page keeps the checkout's line endings)."""
    try:
        return b"\r\n" in Path(root, rel).read_bytes()[:4096]
    except OSError:
        return False


def rebuild_model(root):
    r = subprocess.run([sys.executable, str(Path(root, "scripts", "arch.py")), "build"], cwd=str(root), capture_output=True, text=True)
    return r.returncode, (r.stdout + r.stderr).strip()


def status_lines(root):
    reg, _, _ = load_json(root, REGISTRY)
    st = view_status(root)
    lines = []
    for e in reg.get("pages", []):
        s = st.get(e["view"], "no such view")
        lines.append(f"{e['file']:<42} -> {e['view']:<20} {s:<10} {'READY' if is_ready(e, st) else 'waiting for its flow'}")
    for e in reg.get("retired", []):
        lines.append(f"{e['file']:<42} -> {e['view']:<20} {'':<10} retired")
    return lines


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("command", nargs="?", choices=["status"], help="status: list every legacy page")
    ap.add_argument("--root", default=str(ROOT))
    ap.add_argument("--apply", action="store_true", help="retire every page that is ready")
    ap.add_argument("--dry-run", action="store_true", help="with --apply: change nothing")
    ap.add_argument("--check", action="store_true", help="exit 1 if a ready page is not retired yet")
    args = ap.parse_args(argv)
    root = Path(args.root)

    if args.check:
        reg, _, _ = load_json(root, REGISTRY)
        st = view_status(root)
        late = [e["file"] for e in reg.get("pages", []) if is_ready(e, st)]
        for f in late:
            print(f"ready but not retired: {f}  (run: python scripts/retire_legacy.py --apply)")
        if not late:
            print("no legacy diagram is ready to retire")
        return 1 if late else 0
    if args.apply:
        done, touched = retire(root, dry=args.dry_run)
        verb = "would retire" if args.dry_run else "retired"
        for e in done:
            print(f"{verb}: {e['file']} -> architecture.html#{e['view']}")
        for t in touched:
            print(f"  {'would change' if args.dry_run else 'changed'}: {t}")
        if not done:
            print("nothing is ready to retire")
            return 0
        if not args.dry_run:
            code, out = rebuild_model(root)
            print("arch.py build:", "ok" if code == 0 else f"FAILED\n{out}")
            if code:
                return 1
        reg, _, _ = load_json(root, REGISTRY)
        if not reg.get("pages") and not args.dry_run:
            print('every legacy diagram is retired: the "archify" figure type is unused; remove it from assets/js/figures.js and scripts/test_figures.py')
        return 0
    for line in status_lines(root):
        print(line)
    return 0


if __name__ == "__main__":
    sys.exit(main())
