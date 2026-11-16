#!/usr/bin/env python3
"""Vendor Mermaid for the figure layer (patch P06). Standard library only.

    python scripts/vendor_mermaid.py            # download the pinned version into assets/vendor/mermaid/
    python scripts/vendor_mermaid.py --check    # is the vendored copy there, and is it the pinned one? (exit 1 if not)

Why: the site has no build step and no CDN dependency (plan, principle 5), so Mermaid is copied into the repo at one
exact version. assets/js/figures.js loads it only on a chapter whose manifest has a `mermaid` figure; until one does, you
do not need to run this at all.

What it does: downloads mermaid-<VERSION>.tgz from the npm registry, checks it against the sha512 that npm publishes for
that version (pinned below, so a changed or tampered tarball is refused), and writes
    assets/vendor/mermaid/mermaid.min.js   the self-contained browser build (defines window.mermaid)
    assets/vendor/mermaid/LICENSE          MIT
    assets/vendor/mermaid/VERSION.txt      version, source URL and the hashes
The bundle is ~3.5 MB; check_site.py leaves assets/vendor/ out of its size budget, and Vercel serves it with the usual
cache header for /assets/vendor/.

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
DEST = ROOT / "assets" / "vendor" / "mermaid"

VERSION = "11.17.2"                                    # published 2026-08-25; the 11.x line, not the 12.x "latest"
TARBALL_URL = f"https://registry.npmjs.org/mermaid/-/mermaid-{VERSION}.tgz"
TARBALL_INTEGRITY = "sha512-V6K3C8EBdEsPFZXSKMJe6ppQOENxuHARr9GvHX4hh47lAbhMRD9qf4oEK7LoaRQxULMa80/qt5gHO73aCleBBg=="   # npm's dist.integrity
MIN_SHA256 = "581ed7d74bd9048d0e3a91363927d72ef22942d7722546b27f7cc29e35390eb8"   # of dist/mermaid.min.js, line endings normalised to LF
MIN_NAME, LICENSE_NAME = "package/dist/mermaid.min.js", "package/LICENSE"


def lf(data: bytes) -> bytes:
    """Git on Windows may check text files out with CRLF; the hash is taken over LF so --check still passes there."""
    return data.replace(b"\r\n", b"\n")


def sha256_lf(data: bytes) -> str:
    return hashlib.sha256(lf(data)).hexdigest()


def npm_integrity(data: bytes) -> str:
    return "sha512-" + base64.b64encode(hashlib.sha512(data).digest()).decode("ascii")


def check() -> int:
    f = DEST / "mermaid.min.js"
    if not f.is_file():
        print(f"missing: {f.relative_to(ROOT).as_posix()}  (run: python scripts/vendor_mermaid.py)")
        return 1
    got = sha256_lf(f.read_bytes())
    if got != MIN_SHA256:
        print(f"{f.relative_to(ROOT).as_posix()} is not mermaid {VERSION} (sha256 {got[:12]}..., expected {MIN_SHA256[:12]}...).\n"
              "Run: python scripts/vendor_mermaid.py")
        return 1
    print(f"mermaid {VERSION} is vendored and matches the pin.")
    return 0


def fetch(url: str) -> bytes:
    req = urllib.request.Request(url, headers={"User-Agent": "minime-book-vendor/1"})
    with urllib.request.urlopen(req, timeout=120) as r:
        return r.read()


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description="Vendor the pinned Mermaid build into assets/vendor/mermaid/.")
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
    try:
        with tarfile.open(fileobj=io.BytesIO(raw), mode="r:gz") as tf:
            js = tf.extractfile(MIN_NAME).read()
            lic = tf.extractfile(LICENSE_NAME).read()
    except (tarfile.TarError, KeyError, AttributeError) as e:
        sys.exit(f"The tarball does not have the expected files ({MIN_NAME}, {LICENSE_NAME}): {e}")

    if args.print_integrity:
        print(f"VERSION           = {VERSION}\nTARBALL_INTEGRITY = {npm_integrity(raw)}\nMIN_SHA256        = {sha256_lf(js)}")
        return 0
    if npm_integrity(raw) != TARBALL_INTEGRITY:
        sys.exit(f"Refusing to write anything: the tarball's integrity is {npm_integrity(raw)[:24]}..., the pin says {TARBALL_INTEGRITY[:24]}...")
    if sha256_lf(js) != MIN_SHA256:
        sys.exit("Refusing to write anything: mermaid.min.js does not match the pinned sha256.")

    DEST.mkdir(parents=True, exist_ok=True)
    (DEST / "mermaid.min.js").write_bytes(js)
    (DEST / "LICENSE").write_bytes(lic)
    (DEST / "VERSION.txt").write_text(
        f"mermaid {VERSION}\nsource {TARBALL_URL}\nintegrity {TARBALL_INTEGRITY}\nmermaid.min.js sha256 {MIN_SHA256} (LF)\n"
        "Written by scripts/vendor_mermaid.py; do not edit by hand.\n", encoding="utf-8", newline="\n")
    print(f"mermaid {VERSION} written to {DEST.relative_to(ROOT).as_posix()}/ ({len(js) // 1024} KB).")
    return 0


if __name__ == "__main__":
    sys.exit(main())
