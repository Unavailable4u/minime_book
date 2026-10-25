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
    2. refresh_atlas.py --census-from <MiniMe>   new census, then every census-driven page
    3. refresh_graph.py --minime <MiniMe>        every Graphify-driven part (graph, hubs, Explore edges, API callers)
    4. both scripts with --check, and the unit tests, to prove nothing is left stale
    5. with --push: git add, commit and push

Standard library only (the census itself needs tree-sitter and PyYAML, see --install-deps).
"""
import argparse
import json
import os
import subprocess
import sys
from pathlib import Path

sys.dont_write_bytecode = True      # the repo tracks scripts/__pycache__; do not make it show as modified

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


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("--minime", default=str(ROOT.parent / "MiniMe"), help="the MiniMe checkout (default: ../MiniMe)")
    ap.add_argument("--push", action="store_true", help="commit and push the result when everything passed")
    ap.add_argument("--install-deps", action="store_true", help="pip install tree-sitter tree-sitter-javascript pyyaml first")
    ap.add_argument("--allow-stale-graph", action="store_true", help="accept a graph built at a different commit than MiniMe's HEAD")
    ap.add_argument("--force-census", action="store_true", help="pass --force to the census step (accept a census that failed validation)")
    args = ap.parse_args(argv)
    minime = Path(args.minime).resolve()

    head = preflight(minime, args.allow_stale_graph)
    if args.install_deps:
        run(PY, "-m", "pip", "install", *DEPS)

    census = [PY, "scripts/refresh_atlas.py", "--census-from", minime]
    run(*(census + (["--force"] if args.force_census else [])))
    graph = [PY, "scripts/refresh_graph.py", "--minime", minime]
    run(*(graph + (["--allow-stale-graph"] if args.allow_stale_graph else [])))

    print("\n== Verifying nothing is stale ==")
    run(PY, "scripts/refresh_atlas.py", "--check")
    run(*(graph + ["--check"] + (["--allow-stale-graph"] if args.allow_stale_graph else [])))
    run(PY, "scripts/test_refresh_atlas.py")
    run(PY, "scripts/test_refresh_graph.py")

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
