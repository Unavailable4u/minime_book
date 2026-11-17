#!/usr/bin/env python3
"""
refresh_source.py -- copy MiniMe's source into this site, at the audited commit (P12, plan section 6.4).

    python scripts/refresh_source.py --minime ../MiniMe           # write data/src/<path>.txt and data/src/manifest.json
    python scripts/refresh_source.py --minime ../MiniMe --check   # change nothing; exit 1 if data/src is out of date
    python scripts/refresh_source.py --check                      # no MiniMe here: only prove data/src matches its own manifest

Why: the Explorer shows the explanation next to the real lines. The lines must be the ones the census (and the notes)
describe, so every file is read FROM GIT AT THE CENSUS COMMIT (`git ls-tree` + `git cat-file`), never from the working
tree. That makes Windows CRLF checkouts irrelevant, and the blob id of each copy equals the blob id in a note.

Which files are copied: every tracked text file at that commit EXCEPT
    * files matching data/src-denylist.txt (lockfiles, *.jsonl fixtures, MiniMe's runtime data folder, ...)
    * files larger than 300 000 bytes, symlinks, submodules, binary files and files that are not UTF-8
    * files that fail the secret scan (see below), and always: a real .env (not .env.example), *.pem, *.key, *.p12, *.pfx
Everything skipped is listed in the manifest with its reason, so the Explorer can say why there is no source.

Secret scan: if `gitleaks` is on PATH it is run with MiniMe's own .gitleaks.toml; otherwise a small regex fallback is
used (private key blocks, AWS and GitHub tokens, long api_key = "..." assignments, ...). It judges CONTENT, never file
names. A hit under a tests/ or fixtures/ folder is only a WARNING and the file is still copied (m2c/tests/secret_handling
holds deliberately fake secrets); a hit anywhere else refuses the file. The report never prints the secret itself.

Only changed blobs are rewritten, so each update commit stays small. Files that are no longer in the commit are deleted.
Standard library only.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import re
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

sys.dont_write_bytecode = True      # no __pycache__ next to the scripts

HERE = Path(__file__).resolve().parent
if str(HERE) not in sys.path:
    sys.path.insert(0, str(HERE))
import build_code  # noqa: E402
import build_index  # noqa: E402
from notes import glob_match  # noqa: E402  (one glob dialect for the whole repo)

ROOT = HERE.parent
SCHEMA = 1
SCANNER_VERSION = 1                 # bump when the regex fallback changes, so every file is judged again
SRC_DIR = "data/src"
MANIFEST_NAME = "manifest.json"
DENYLIST_FILE = "data/src-denylist.txt"
CENSUS_FILE = "data/census.json"
MAX_BYTES = 300_000

# Skips that depend on the file's content (and so are remembered per blob), versus on its name or size only.
CONTENT_REASONS = {"binary", "not-utf8", "secret"}

SECRET_PATTERNS = [
    ("private key", re.compile(r"-----BEGIN [A-Z ]*PRIVATE KEY-----")),
    ("AWS access key", re.compile(r"\bAKIA[0-9A-Z]{16}\b")),
    ("GitHub token", re.compile(r"\bgh[pousr]_[A-Za-z0-9]{30,}\b")),
    ("API secret key (sk-...)", re.compile(r"\bsk-[A-Za-z0-9_-]{20,}")),
    ("Slack token", re.compile(r"\bxox[abprs]-[A-Za-z0-9-]{10,}")),
    ("JWT", re.compile(r"\beyJ[A-Za-z0-9_-]{15,}\.[A-Za-z0-9_-]{15,}\.[A-Za-z0-9_-]{10,}")),
    ("long credential assignment", re.compile(r"""(?i)\b(?:api[_-]?key|secret|token|password)\b\s*[:=]\s*["'][^"'\s]{16,}["']""")),
]
TEST_DIRS = {"tests", "test", "__tests__", "fixtures"}


# ----------------------------------------------------------------------------- git
def git(repo, *args, input: bytes | None = None) -> subprocess.CompletedProcess:
    return subprocess.run(["git", "-C", str(repo), *args], capture_output=True, input=input)


def commit_exists(repo, commit: str) -> bool:
    return git(repo, "cat-file", "-e", f"{commit}^{{commit}}").returncode == 0


def ls_tree(repo, rev: str) -> dict[str, tuple[str, str, int]]:
    """{path: (mode, blob id, size)} for every entry of `rev`, from ONE `git ls-tree -r -l`."""
    r = git(repo, "ls-tree", "-r", "-l", "-z", rev)
    if r.returncode:
        raise SystemExit(f"git ls-tree failed in {repo}: {r.stderr.decode('utf-8', 'replace').strip()}")
    out: dict[str, tuple[str, str, int]] = {}
    for rec in r.stdout.split(b"\0"):
        if not rec:
            continue
        meta, _, path = rec.partition(b"\t")
        parts = meta.split()
        if len(parts) != 4:
            continue
        mode, kind, blob, size = (p.decode("ascii") for p in parts)
        if kind in ("blob", "commit"):          # "commit" is a submodule entry
            out[path.decode("utf-8", "replace")] = (mode, blob, int(size) if size.isdigit() else 0)
    return out


def read_blobs(repo, blobs: list[str]) -> dict[str, bytes]:
    """Raw content of each blob, with ONE `git cat-file --batch` process. Missing blobs are left out."""
    wanted = sorted(set(blobs))
    if not wanted:
        return {}
    r = git(repo, "cat-file", "--batch", input=("\n".join(wanted) + "\n").encode("ascii"))
    if r.returncode:
        raise SystemExit(f"git cat-file failed in {repo}: {r.stderr.decode('utf-8', 'replace').strip()}")
    data, pos, out = r.stdout, 0, {}
    while pos < len(data):
        nl = data.index(b"\n", pos)
        head = data[pos:nl].split()
        pos = nl + 1
        if len(head) == 2 and head[1] == b"missing":
            continue
        size = int(head[2])
        out[head[0].decode("ascii")] = data[pos:pos + size]
        pos += size + 1                          # the newline git adds after each object
    return out


def git_blob_id(data: bytes) -> str:
    return hashlib.sha1(b"blob %d\0" % len(data) + data).hexdigest()


# ----------------------------------------------------------------------------- rules
def load_denylist(root: Path) -> list[str]:
    p = root / DENYLIST_FILE
    if not p.exists():
        return []
    out = []
    for line in build_index.read_lf(p).split("\n"):
        line = line.split(" #", 1)[0].strip()
        if line and not line.startswith("#"):
            out.append(line)
    return out


def always_refused(path: str) -> str | None:
    name = path.rsplit("/", 1)[-1].lower()
    if name == ".env" or (name.startswith(".env.") and not name.endswith((".example", ".sample", ".template", ".dist"))):
        return "env"
    if name.endswith((".pem", ".key", ".p12", ".pfx")):
        return "env"                              # same bucket: key material, never copied
    return None


def classify(path: str, mode: str, size: int, deny: list[str]) -> str | None:
    """Why this file is skipped using only its name, mode and size, or None when its content must be looked at."""
    if mode == "160000":
        return "submodule"
    if mode == "120000":
        return "symlink"
    if ":" in path or "\\" in path or ".." in path.split("/"):
        return "unsafe-path"
    why = always_refused(path)
    if why:
        return why
    if any(glob_match(g, path) for g in deny):
        return "denylist"
    if size > MAX_BYTES:
        return "too-large"
    return None


def decode_text(data: bytes) -> str | None:
    if b"\0" in data[:8000]:
        return None
    try:
        return data.decode("utf-8")
    except UnicodeDecodeError:
        return None


def in_tests(path: str) -> bool:
    parts = path.split("/")
    name = parts[-1]
    return any(p in TEST_DIRS for p in parts[:-1]) or name.startswith("test_") or name == "conftest.py" or ".test." in name or ".spec." in name


def regex_scan(text: str) -> list[str]:
    """Labels of the secret patterns that match, with the line number of the first hit. Never the matched text."""
    hits = []
    for label, rx in SECRET_PATTERNS:
        m = rx.search(text)
        if m:
            hits.append(f"{label} (line {text.count(chr(10), 0, m.start()) + 1})")
    return hits


def parse_gitleaks_report(report: str, stage: Path) -> dict[str, list[str]]:
    """{repo path: [finding labels]} from a gitleaks JSON report. Only rule ids and line numbers are kept."""
    try:
        findings = json.loads(report) if report.strip() else []
    except ValueError:
        raise RuntimeError("gitleaks wrote a report that is not JSON")
    out: dict[str, list[str]] = {}
    for f in findings or []:
        if not isinstance(f, dict) or not f.get("File"):
            continue
        p = Path(str(f["File"]))
        try:
            rel = p.relative_to(stage).as_posix()
        except ValueError:
            rel = p.as_posix().lstrip("./") if not p.is_absolute() else p.as_posix()
        out.setdefault(rel, []).append(f"{f.get('RuleID') or 'finding'} (line {f.get('StartLine') or '?'})")
    return out


def gitleaks_scan(exe: str, files: dict[str, bytes], config: Path | None) -> dict[str, list[str]]:
    """Run gitleaks over `files` (repo path -> bytes) staged in a temp folder that mirrors the repo layout, so the paths in
    MiniMe's .gitleaks.toml allow-list still match. Raises RuntimeError when gitleaks cannot be used."""
    tmp = Path(tempfile.mkdtemp(prefix="atlas-src-"))
    try:
        stage = tmp / "stage"
        for rel, data in files.items():
            dest = stage / rel
            dest.parent.mkdir(parents=True, exist_ok=True)
            dest.write_bytes(data)
        report = tmp / "report.json"
        cmd = [exe, "detect", "--no-git", "--source", str(stage), "--report-format", "json", "--report-path", str(report), "--exit-code", "0"]
        if config and config.exists():
            cmd += ["--config", str(config)]
        r = subprocess.run(cmd, capture_output=True, text=True)
        if r.returncode:
            raise RuntimeError(f"gitleaks exited with {r.returncode}: {(r.stderr or r.stdout).strip()[:200]}")
        return parse_gitleaks_report(report.read_text(encoding="utf-8") if report.exists() else "", stage)
    finally:
        shutil.rmtree(tmp, ignore_errors=True)


# ----------------------------------------------------------------------------- the plan
def rules_id(deny: list[str], scanner: str) -> str:
    """Changes when anything that decides 'copy or not' changes, so remembered decisions are then re-made."""
    return hashlib.sha1(json.dumps([deny, MAX_BYTES, SCANNER_VERSION, scanner]).encode()).hexdigest()[:12]


def dest_of(root: Path, path: str) -> Path:
    return root / SRC_DIR / f"{path}.txt"


def on_disk_matches(dest: Path, blob: str) -> bool:
    """The copy exists and is the committed text (an LF checkout, or the same text with CRLF added by autocrlf)."""
    try:
        data = dest.read_bytes()
    except OSError:
        return False
    return git_blob_id(data) == blob or git_blob_id(data.replace(b"\r\n", b"\n")) == blob


def build_plan(minime: Path, commit: str, root: Path, prev: dict | None, scanner: str | None = None, force: bool = False,
               log=print) -> dict:
    """Decide, for every tracked file at `commit`, whether to copy it. Returns
       {manifest, writes: {path: bytes}, deletes: [paths], warnings: [...], refused: [...]}.
       Reads file content only for blobs that are new, changed, or whose copy is missing or damaged on disk."""
    deny = load_denylist(root)
    scanner = scanner or ("gitleaks" if shutil.which("gitleaks") else "regex")
    rid = rules_id(deny, scanner)
    tree = ls_tree(minime, commit)
    reuse = bool(prev) and prev.get("rules") == rid and not force
    prev_files = (prev or {}).get("files", {}) if reuse else {}
    prev_skipped = (prev or {}).get("skipped", {}) if reuse else {}
    prev_warned = (prev or {}).get("warned", {}) if reuse else {}

    files: dict[str, str] = {}
    skipped: dict[str, dict] = {}
    warned: dict[str, list[str]] = {}
    pending: list[str] = []
    for path, (mode, blob, size) in sorted(tree.items()):
        why = classify(path, mode, size, deny)
        if why:
            skipped[path] = {"blob": blob, "why": why}
        elif prev_files.get(path) == blob and on_disk_matches(dest_of(root, path), blob):
            files[path] = blob
            if path in prev_warned:
                warned[path] = prev_warned[path]
        elif prev_skipped.get(path, {}).get("blob") == blob and prev_skipped[path].get("why") in CONTENT_REASONS:
            skipped[path] = prev_skipped[path]
        else:
            pending.append(path)

    blobs = read_blobs(minime, [tree[p][1] for p in pending])
    candidates: dict[str, bytes] = {}
    for path in pending:
        blob = tree[path][1]
        data = blobs.get(blob)
        if data is None:
            skipped[path] = {"blob": blob, "why": "unreadable"}
        elif decode_text(data) is None:
            skipped[path] = {"blob": blob, "why": "binary" if b"\0" in data[:8000] else "not-utf8"}
        else:
            candidates[path] = data

    findings: dict[str, list[str]] = {}
    if scanner == "gitleaks" and candidates:
        try:
            findings = gitleaks_scan(shutil.which("gitleaks"), candidates, minime / ".gitleaks.toml")
        except (RuntimeError, OSError) as e:
            log(f"warning: gitleaks could not be used ({e}); using the regex scan instead.")
            scanner = "regex"
            rid = rules_id(deny, scanner)
    if scanner == "regex":
        findings = {p: h for p, d in candidates.items() if (h := regex_scan(decode_text(d) or ""))}

    writes: dict[str, bytes] = {}
    warnings: list[str] = []
    for path, data in sorted(candidates.items()):
        hits = findings.get(path)
        if hits and in_tests(path):
            warnings.append(f"{path}: looks like a secret ({'; '.join(hits[:3])}), copied because it is under a tests/fixtures folder")
            warned[path] = hits[:3]
        elif hits:
            skipped[path] = {"blob": tree[path][1], "why": "secret", "hits": hits[:3]}
            continue
        files[path] = tree[path][1]
        writes[path] = data

    # Refusals are reported on every run (not only the run that found them): a real .env or key file, or a secret-scan hit.
    refused = [f"{p}: {'; '.join(s['hits']) if s.get('hits') else 'a real .env or key file is tracked in MiniMe'}"
               for p, s in sorted(skipped.items()) if s["why"] in ("secret", "env")]
    existing = {p.relative_to(root / SRC_DIR).as_posix() for p in (root / SRC_DIR).rglob("*.txt")} if (root / SRC_DIR).exists() else set()
    keep = {f"{p}.txt" for p in files}
    deletes = sorted(p[:-4] for p in existing - keep)
    manifest = {"schema": SCHEMA, "commit": commit, "rules": rid, "scanner": scanner, "files": files, "skipped": skipped, "warned": warned}
    return {"manifest": manifest, "writes": writes, "deletes": deletes, "warnings": warnings, "refused": refused}


def apply_plan(root: Path, plan: dict) -> None:
    for path, data in plan["writes"].items():
        dest = dest_of(root, path)
        dest.parent.mkdir(parents=True, exist_ok=True)
        dest.write_bytes(data)                    # exactly the committed bytes, never re-encoded
    for path in plan["deletes"]:
        dest_of(root, path).unlink(missing_ok=True)
    base = root / SRC_DIR
    if base.exists():
        for d in sorted((p for p in base.rglob("*") if p.is_dir()), key=lambda p: len(p.parts), reverse=True):
            try:
                d.rmdir()                         # only succeeds when empty
            except OSError:
                pass
    base.mkdir(parents=True, exist_ok=True)
    (base / MANIFEST_NAME).write_text(build_index.dumps(plan["manifest"]), encoding="utf-8", newline="\n")


def load_manifest(root: Path) -> dict | None:
    m = build_index.load_json(root / SRC_DIR / MANIFEST_NAME, None)
    return m if isinstance(m, dict) and m.get("schema") == SCHEMA else None


def census_commit(root: Path) -> str:
    census = build_index.load_json(root / CENSUS_FILE, None)
    if not isinstance(census, dict):
        raise SystemExit(f"{root / CENSUS_FILE} not found. Run scripts/refresh_atlas.py --census-from <MiniMe> first.")
    commit = build_code.commit_of(census)
    if not re.fullmatch(r"[0-9a-f]{40}", commit or ""):
        raise SystemExit("the census has no full commit id (git.head_full). Regenerate it with MiniMe's codebase_census.py.")
    return commit


def check_offline(root: Path, commit: str, log=print) -> int:
    """No MiniMe here: prove data/src agrees with its own manifest and with the census commit."""
    m = load_manifest(root)
    if not m:
        log("source: data/src/manifest.json is missing. Run: python scripts/refresh_source.py --minime ../MiniMe")
        return 1
    problems = []
    if m.get("commit") != commit:
        problems.append(f"manifest is for {str(m.get('commit'))[:7]}, the census is at {commit[:7]}")
    for path, blob in m.get("files", {}).items():
        if not on_disk_matches(dest_of(root, path), blob):
            problems.append(f"{path}: missing or different from the manifest")
    base = root / SRC_DIR
    extra = {p.relative_to(base).as_posix()[:-4] for p in base.rglob("*.txt")} - set(m.get("files", {}))
    problems += [f"{p}: not in the manifest" for p in sorted(extra)]
    for p in problems[:20]:
        log(f"source: {p}")
    if len(problems) > 20:
        log(f"source: ... and {len(problems) - 20} more")
    if problems:
        log("source: data/src is out of date. Run: python scripts/refresh_source.py --minime ../MiniMe")
    return 1 if problems else 0


def summarize(plan: dict, prev: dict | None) -> str:
    m = plan["manifest"]
    old = (prev or {}).get("files", {})
    new = [p for p in plan["writes"] if p not in old]
    changed = [p for p in plan["writes"] if p in old]
    reasons: dict[str, int] = {}
    for s in m["skipped"].values():
        reasons[s["why"]] = reasons.get(s["why"], 0) + 1
    why = ", ".join(f"{n} {k}" for k, n in sorted(reasons.items())) or "none"
    return (f"source: {len(m['files'])} file(s) embedded at {m['commit'][:7]} ({len(new)} new, {len(changed)} changed, "
            f"{len(plan['deletes'])} removed, {len(m['files']) - len(plan['writes'])} unchanged); skipped: {why}; scanner: {m['scanner']}")


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description="Copy MiniMe's source into data/src at the census commit.")
    ap.add_argument("--minime", default=None, help="the MiniMe checkout (default: ../MiniMe when it exists)")
    ap.add_argument("--root", default=str(ROOT), help="the minime_book checkout (default: this repo)")
    ap.add_argument("--check", action="store_true", help="change nothing; exit 1 if data/src is out of date")
    ap.add_argument("--force", action="store_true", help="judge every file again (ignore remembered decisions)")
    ap.add_argument("--strict", action="store_true", help="exit 1 when a file was refused by the secret scan")
    args = ap.parse_args(argv)

    root = Path(args.root).resolve()
    commit = census_commit(root)
    minime = Path(args.minime).resolve() if args.minime else (ROOT.parent / "MiniMe")
    have_minime = minime.exists() and git(minime, "rev-parse", "--git-dir").returncode == 0

    if args.check and not have_minime and not args.minime:
        return check_offline(root, commit)
    if not have_minime:
        print(f"{minime} is not a git checkout. Use --minime PATH.", file=sys.stderr)
        return 2
    if not commit_exists(minime, commit):
        print(f"MiniMe has no commit {commit[:7]} (the census commit). Fetch it, or refresh the census from this checkout.", file=sys.stderr)
        return 2

    prev = load_manifest(root)
    plan = build_plan(minime, commit, root, prev, force=args.force)
    for w in plan["warnings"]:
        print(f"warning: {w}")
    for r in plan["refused"]:
        print(f"REFUSED (not copied): {r}")
    print(summarize(plan, prev))

    new_manifest_text = build_index.dumps(plan["manifest"])
    manifest_path = root / SRC_DIR / MANIFEST_NAME
    stale = bool(plan["writes"] or plan["deletes"]) or not manifest_path.exists() or build_index.read_lf(manifest_path) != new_manifest_text
    if args.check:
        if stale:
            print("source: data/src is out of date. Run: python scripts/refresh_source.py --minime ../MiniMe")
        return 1 if stale else 0
    if stale:
        apply_plan(root, plan)
        print(f"source: wrote {len(plan['writes'])} file(s), removed {len(plan['deletes'])}.")
    else:
        print("source: already up to date.")
    return 1 if (args.strict and plan["refused"]) else 0


if __name__ == "__main__":
    sys.exit(main())