#!/usr/bin/env python3
"""
update_all.py -- bring the whole MiniMe Atlas up to date with the MiniMe repo in one command.

Do this first, in the MiniMe repo:

    1. commit your work            (the census and the graph both describe a commit)
    2. regenerate the graph        (give Copilot the "rebuild the graphify graph" prompt)

Then, from this repo:

    python scripts/update_all.py                      # refresh everything, show the result, change nothing in git
    python scripts/update_all.py --push               # ... and commit + push, so Vercel deploys it
    python scripts/update_all.py --minime D:\\code\\MiniMe   # MiniMe is not next to this repo
    python scripts/update_all.py --install-deps       # pip install tree-sitter tree-sitter-javascript pyyaml first

What it runs, in order, stopping at the first problem:

    1. checks MiniMe is a clean checkout and graphify-out/graph.json was built at its current commit
    2. refresh_atlas.py --census-from <MiniMe>   new census, then every census-driven page, the search index and
                                                 the sharded code data the Explorer reads (data/code/)
    3. refresh_graph.py --minime <MiniMe>        every Graphify-driven part (graph, hubs, Explore edges, API callers)
                                                 (the Overview, index.html, is a shell: both scripts write its numbers to data/index/vitals.json)
    4. notes.py ingest --minime <MiniMe>         the AI-written notes (MiniMe/graphify-out/atlas-notes, see UPDATING.md "Step 2b"):
                                                 validate, copy into data/notes/, fill symbol hashes, write data/index/notes.json.
                                                 A malformed note stops here; warnings and stale notes never do
    5. refresh_source.py --minime <MiniMe>       the source code itself, copied into data/src/ at the census commit (read from git, not
                                                 from the working tree) so the Explorer can show it next to the explanations.
                                                 Secret-scanned; a file that fails is refused and listed. Skipped with --no-embed-source
                                                 or when content/config.json says "embedSource": false
    6. refresh_protocol.py --minime <MiniMe>     the M2C contract (protocol/v1 schemas, tools, fixtures), the M2C package map and
                                                 the decision records, read from git at the census commit into data/code/protocol.json
    7. refresh_schema.py                         the data model (data/code/schema.json), read from the SQL that step 5 embedded. It runs after
                                                 the census and the source so it describes the same commit; without embedded source it falls
                                                 back to what the census recorded and says so. (infra.json is written by step 2.)
    8. arch.py ingest --minime <MiniMe>          the architecture model (P25, UPDATING.md "Step 2c"): the structure is derived from the census
                                                 and data/code/*.json (so it runs after steps 6 and 7, which write protocol.json and schema.json),
                                                 the flows Copilot wrote (MiniMe/graphify-out/atlas-arch) are validated, their evidence hashes
                                                 filled, and data/arch/ plus data/index/arch.json are rewritten. A malformed flow stops here;
                                                 stale, broken and unverified flows only warn
    9. both scripts with --check (refresh_atlas.py --check covers the search index, data/code/infra.json and the rest of data/code too),
       refresh_schema.py --check, notes.py ingest --check, notes.py validate, refresh_source.py --check, refresh_protocol.py --check,
       arch.py ingest --check, arch.py validate, and the unit tests, to prove nothing is left stale
   10. with --push: git add, commit and push

Standard library only (the census itself needs tree-sitter and PyYAML, see --install-deps).
"""
import argparse
import json
import os
import subprocess
import sys
from pathlib import Path

sys.dont_write_bytecode = True      # no __pycache__ next to the scripts (it is git-ignored, but there is no need to make it)

ROOT = Path(__file__).resolve().parent.parent
PY = sys.executable
DEPS = ["tree-sitter", "tree-sitter-javascript", "pyyaml"]


def run(*cmd, cwd=ROOT, check=True, capture=False):
    print("\n$", " ".join(str(c) for c in cmd), flush=True)
    r = subprocess.run([str(c) for c in cmd], cwd=cwd, text=True, capture_output=capture, env={**os.environ, "PYTHONDONTWRITEBYTECODE": "1"})
    if check and r.returncode:
        sys.exit(f"\nStopped: `{' '.join(str(c) for c in cmd)}` failed (exit {r.returncode}).")
    return r


def git(repo, *args):
    return subprocess.run(["git", "-C", str(repo), *args], text=True, capture_output=True)


def preflight(minime, allow_stale):
    if not (minime / "scripts" / "codebase_census.py").exists():
        sys.exit(f"{minime} does not look like a MiniMe checkout (scripts/codebase_census.py missing). Use --minime PATH.")
    if git(minime, "rev-parse", "HEAD").returncode:
        sys.exit(f"{minime} is not a git repository.")
    dirty = git(minime, "status", "--porcelain").stdout.strip()
    if dirty:
        sys.exit("MiniMe has uncommitted or untracked files, and the census would count them:\n" + dirty
                 + "\nCommit (or stash) them, regenerate the graph, then run this again.")
    head = git(minime, "rev-parse", "HEAD").stdout.strip()
    gpath = minime / "graphify-out" / "graph.json"
    if not gpath.exists():
        sys.exit(f"{gpath} not found. Regenerate the graph with Copilot first.")
    built = json.loads(gpath.read_text(encoding="utf-8")).get("built_at_commit", "")
    if built != head and not allow_stale:
        sys.exit(f"The graph was built at {built[:7] or 'an unknown commit'} but MiniMe is at {head[:7]}.\n"
                 "Regenerate the graph with Copilot (after committing), then run this again.\n"
                 "(--allow-stale-graph overrides this if you really want a mixed snapshot.)")
    print(f"MiniMe is clean at {head[:7]} and the graph was built at the same commit." if built == head
          else f"WARNING: graph is from {built[:7]}, MiniMe is at {head[:7]} (--allow-stale-graph).")
    return head


def embed_source_enabled(root=ROOT):
    """content/config.json `embedSource` (default true). Unreadable config counts as the default."""
    try:
        cfg = json.loads((Path(root) / "content" / "config.json").read_bytes().decode("utf-8-sig"))
    except (OSError, ValueError):
        return True
    return not (isinstance(cfg, dict) and cfg.get("embedSource") is False)


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("--minime", default=str(ROOT.parent / "MiniMe"), help="the MiniMe checkout (default: ../MiniMe)")
    ap.add_argument("--push", action="store_true", help="commit and push the result when everything passed")
    ap.add_argument("--install-deps", action="store_true", help="pip install tree-sitter tree-sitter-javascript pyyaml first")
    ap.add_argument("--allow-stale-graph", action="store_true", help="accept a graph built at a different commit than MiniMe's HEAD")
    ap.add_argument("--force-census", action="store_true", help="pass --force to the census step (accept a census that failed validation)")
    ap.add_argument("--no-embed-source", action="store_true", help="do not copy MiniMe's source into data/src (also off when content/config.json has embedSource false)")
    args = ap.parse_args(argv)
    minime = Path(args.minime).resolve()

    head = preflight(minime, args.allow_stale_graph)
    if args.install_deps:
        run(PY, "-m", "pip", "install", *DEPS)

    census = [PY, "scripts/refresh_atlas.py", "--census-from", minime]
    run(*(census + (["--force"] if args.force_census else [])))
    graph = [PY, "scripts/refresh_graph.py", "--minime", minime]
    run(*(graph + (["--allow-stale-graph"] if args.allow_stale_graph else [])))

    notes = [PY, "scripts/notes.py", "ingest", "--minime", minime]
    run(*notes)

    embed = embed_source_enabled() and not args.no_embed_source
    source = [PY, "scripts/refresh_source.py", "--minime", minime]
    if embed:
        run(*source)                       # refused (secret-scan) files are printed as REFUSED; add --strict by hand to make them fatal
    else:
        print("\n(source embedding is off: data/src is not touched)")

    protocol = [PY, "scripts/refresh_protocol.py", "--minime", minime]
    run(*protocol)                         # fails (and says why) if MiniMe has no protocol/v1 at the census commit
    run(PY, "scripts/refresh_schema.py")   # P18: the data model; reads data/src (or the census when the source is not embedded)

    arch = [PY, "scripts/arch.py", "ingest", "--minime", minime]
    run(*arch)                             # P25: after the census, protocol.json and schema.json it reads; a malformed flow stops here

    print("\n== Verifying nothing is stale ==")
    run(PY, "scripts/refresh_atlas.py", "--check")
    run(PY, "scripts/refresh_schema.py", "--check")
    run(*(graph + ["--check"] + (["--allow-stale-graph"] if args.allow_stale_graph else [])))
    run(*(notes + ["--check"]))
    run(PY, "scripts/notes.py", "validate")
    if embed:
        run(*(source + ["--check"]))
    run(*(protocol + ["--check"]))
    run(*(arch + ["--check"]))
    run(PY, "scripts/arch.py", "validate")
    run(PY, "scripts/test_refresh_atlas.py")
    run(PY, "scripts/test_refresh_graph.py")
    run(PY, "scripts/test_build_index.py")
    run(PY, "scripts/test_palette.py")
    run(PY, "scripts/test_reader.py")
    run(PY, "scripts/test_library.py")
    run(PY, "scripts/test_figures.py")
    run(PY, "scripts/test_overview.py")
    run(PY, "scripts/test_build_code.py")
    run(PY, "scripts/test_topology.py")
    run(PY, "scripts/test_notes.py")
    run(PY, "scripts/test_arch.py")
    run(PY, "scripts/test_refresh_source.py")
    run(PY, "scripts/test_links.py")
    run(PY, "scripts/test_chapter_links.py")
    run(PY, "scripts/test_codepages.py")
    run(PY, "scripts/test_refresh_protocol.py")
    run(PY, "scripts/test_dataviews.py")
    run(PY, "scripts/test_refresh_schema.py")
    run(PY, "scripts/test_todo_api.py")

    print("\n== Result ==")
    run("git", "status", "--short")
    run("git", "diff", "--stat", check=False)
    if not args.push:
        print("\nNothing was committed. To publish:  git add -A && git commit -m \"Atlas: full refresh from MiniMe "
              f"{head[:7]}\" && git push\n(or run this again with --push)")
        return 0
    if not git(ROOT, "status", "--porcelain").stdout.strip():
        print("\nAlready up to date; nothing to commit.")
        return 0
    run("git", "add", "-A")
    run("git", "commit", "-m", f"Atlas: full refresh from MiniMe {head[:7]} (census + graph)")
    run("git", "pull", "--rebase")
    run("git", "push")
    print("\nPushed. Vercel will deploy it in about a minute.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
