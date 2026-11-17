#!/usr/bin/env python3
"""Vendor highlight.js for the Explorer's Source tab (patch P14b). Standard library only.

    python scripts/vendor_highlight.py            # download the pinned version into assets/vendor/highlight/
    python scripts/vendor_highlight.py --check    # is the vendored copy there, and is it the pinned one? (exit 1 if not)

Why: the site has no build step and no CDN dependency (plan, principle 5), so highlight.js is copied into the repo at one
exact version, like Mermaid (scripts/vendor_mermaid.py). assets/js/explorer/highlight.js loads the core and then only the
grammar a file needs, so opening a Python file fetches ~24 KB, not the whole library.

What it does: downloads @highlightjs/cdn-assets-<VERSION>.tgz from the npm registry (the package that carries the
pre-built browser ES modules; the plain `highlight.js` package only has CommonJS), checks it against the sha512 npm
publishes for that version (pinned below, so a changed or tampered tarball is refused), checks every file against its own
pinned sha256, and writes
    assets/vendor/highlight/core.min.js            the engine (ES module, default export = the hljs object)
    assets/vendor/highlight/languages/<id>.min.js  one grammar each (ES module, default export = the grammar function)
    assets/vendor/highlight/LICENSE                BSD-3-Clause
    assets/vendor/highlight/VERSION.txt            version, source URL and the hashes
check_site.py leaves assets/vendor/ out of its size budget.

To upgrade: change VERSION, run with --print-integrity to get the new hashes, paste them below, run again.
"""
import argparse
import base64
import hashlib
import io
import sys
import tarfile
import urllib.request
from pathlib import Path

sys.dont_write_bytecode = True

ROOT = Path(__file__).resolve().parent.parent
DEST = ROOT / "assets" / "vendor" / "highlight"

VERSION = "11.11.1"
PACKAGE = "@highlightjs/cdn-assets"
TARBALL_URL = f"https://registry.npmjs.org/{PACKAGE}/-/cdn-assets-{VERSION}.tgz"
TARBALL_INTEGRITY = "sha512-VEPdHzwelZ12hEX18BHduqxMZGolcUsrbeokHYxOUIm8X2+M7nx5QPtPeQgRxR9XjhdLv4/7DD5BWOlSrJ3k7Q=="   # npm's dist.integrity
LICENSE_SRC = "package/LICENSE"
PINS = {}   # destination -> sha256 of the file with LF endings; filled in at the bottom of this file

# The languages are the ones MiniMe has (py, js/jsx/mjs, json, sql, yaml, sh, ps1, css, svg, ini/toml, Dockerfile, md) plus
# typescript (planned, none in the repo today). xml is also what JSX and Markdown embed, so highlight.js needs it for them.
LANGUAGES = ["bash", "css", "dockerfile", "ini", "javascript", "json", "markdown", "powershell", "python", "sql", "typescript", "xml", "yaml"]


def lf(data: bytes) -> bytes:
    """Git on Windows may check text files out with CRLF; hashes are taken over LF so --check still passes there."""
    return data.replace(b"\r\n", b"\n")


def sha256_lf(data: bytes) -> str:
    return hashlib.sha256(lf(data)).hexdigest()


def npm_integrity(data: bytes) -> str:
    return "sha512-" + base64.b64encode(hashlib.sha512(data).digest()).decode("ascii")


def wanted() -> dict:
    """{destination relative to DEST: path inside the tarball}"""
    out = {"core.min.js": "package/es/core.min.js"}
    for lang in LANGUAGES:
        out[f"languages/{lang}.min.js"] = f"package/es/languages/{lang}.min.js"
    return out


def check() -> int:
    bad = []
    for rel in wanted():
        f = DEST / rel
        want = PINS.get(rel)
        if not f.is_file():
            bad.append(f"missing: {f.relative_to(ROOT).as_posix()}")
        elif sha256_lf(f.read_bytes()) != want:
            bad.append(f"{f.relative_to(ROOT).as_posix()} is not highlight.js {VERSION} (sha256 differs from the pin)")
    if bad:
        print("\n".join(bad) + "\nRun: python scripts/vendor_highlight.py")
        return 1
    print(f"highlight.js {VERSION} is vendored ({len(wanted())} files) and matches the pins.")
    return 0


def fetch(url: str) -> bytes:
    req = urllib.request.Request(url, headers={"User-Agent": "minime-book-vendor/1"})
    with urllib.request.urlopen(req, timeout=120) as r:
        return r.read()


def read_members(raw: bytes) -> dict:
    """{destination: bytes} for every wanted file plus LICENSE, or SystemExit when the tarball lacks one."""
    out = {}
    try:
        with tarfile.open(fileobj=io.BytesIO(raw), mode="r:gz") as tf:
            for rel, member in wanted().items():
                out[rel] = tf.extractfile(member).read()
            out["LICENSE"] = tf.extractfile(LICENSE_SRC).read()
    except (tarfile.TarError, KeyError, AttributeError) as e:
        sys.exit(f"The tarball does not have the expected files: {e}")
    return out


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description="Vendor the pinned highlight.js build into assets/vendor/highlight/.")
    ap.add_argument("--check", action="store_true", help="only verify the vendored copy")
    ap.add_argument("--print-integrity", action="store_true", help="download and print the hashes (for an upgrade), write nothing")
    ap.add_argument("--from-file", metavar="TGZ", help="use a tarball you already downloaded instead of the registry")
    args = ap.parse_args(argv)
    if args.check:
        return check()

    try:
        raw = Path(args.from_file).read_bytes() if args.from_file else fetch(TARBALL_URL)
    except OSError as e:
        sys.exit(f"Could not get {TARBALL_URL}: {e}\nIf the registry is blocked, download the tarball elsewhere and use --from-file.")
    members = read_members(raw)

    if args.print_integrity:
        print(f"VERSION           = {VERSION}\nTARBALL_INTEGRITY = {npm_integrity(raw)}\nPINS = {{")
        for rel in wanted():
            print(f'    "{rel}": "{sha256_lf(members[rel])}",')
        print("}")
        return 0
    if npm_integrity(raw) != TARBALL_INTEGRITY:
        sys.exit(f"Refusing to write anything: the tarball's integrity is {npm_integrity(raw)[:24]}..., the pin says {TARBALL_INTEGRITY[:24]}...")
    for rel in wanted():
        if sha256_lf(members[rel]) != PINS.get(rel):
            sys.exit(f"Refusing to write anything: {rel} does not match its pinned sha256.")

    for rel, data in members.items():
        out = DEST / rel
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_bytes(data)
    lines = [f"highlight.js {VERSION}", f"source {TARBALL_URL}", f"integrity {TARBALL_INTEGRITY}"]
    lines += [f"{rel} sha256 {PINS[rel]} (LF)" for rel in wanted()]
    lines.append("Written by scripts/vendor_highlight.py; do not edit by hand.")
    (DEST / "VERSION.txt").write_text("\n".join(lines) + "\n", encoding="utf-8", newline="\n")
    total = sum(len(members[r]) for r in wanted())
    print(f"highlight.js {VERSION} written to {DEST.relative_to(ROOT).as_posix()}/ ({len(wanted())} files, {total // 1024} KB).")
    return 0


# ---- pins (python scripts/vendor_highlight.py --print-integrity) ------------------------------------------------------
PINS.update({
    "core.min.js": "bfcca5550cb9d62482162e1d1fb90c822d2d35036b556544817441b795b7103c",
    "languages/bash.min.js": "d2290ecb0b7d522df0d91d54ee216c673e0c504decd48ef15197b3cab5cb7474",
    "languages/css.min.js": "8024c97edb80335f7aded04543de058770eab34939b9b2db8334fb8aa16f0e45",
    "languages/dockerfile.min.js": "bd40da2c7d1b727dcd4e76f197f176e3d45ed61d167ef5d82a1f15e38a929de5",
    "languages/ini.min.js": "a309557ec2ffe81630e3fbe94237d870b3db28275513303ea8d9e3a6863ad04e",
    "languages/javascript.min.js": "d893654be08f10fe656739ec83cf2cdeb7ea82a26b332b9fea88d4d215c00d89",
    "languages/json.min.js": "7dd0922802ac593d34da3466175377c9efb4612ee2ea97ddafa1fce618a510d9",
    "languages/markdown.min.js": "e8f544abc25490c51ff4bea5687a02ef4a65f1edc83dd208b6664d2672b3e3d5",
    "languages/powershell.min.js": "3d145a6083b7fcb2c0dc03323e975eb7cec499a1bce78e7e0013ac6a1cc39670",
    "languages/python.min.js": "4112a5c44dc7a4c56a772347bd318f246aa1ea51e0d6cb6aba78b25c3e60d524",
    "languages/sql.min.js": "eadde8cadf1c469031abc0c6afd9767dfa8aacf9a7f9ab739ee6edfe635e300e",
    "languages/typescript.min.js": "60f542a05921072df100b34ea9a20a765617c518f8ac11d1c2c238ae11d83fcc",
    "languages/xml.min.js": "2d843265c0bdd3e50f107e6473196b5f525c0ea68de83c40f9f30ffbbea6896f",
    "languages/yaml.min.js": "3d227e0d347021b99da5c7b8de86ec8ce647f2f15d3b97100b34f9d2507ec2e7",
})

if __name__ == "__main__":
    sys.exit(main())
