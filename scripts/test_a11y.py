"""P23 accessibility guards that need no browser: token contrast in both themes, the global CSS rules, the Paper overrides."""
import re
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
TOKENS = (ROOT / "assets/css/tokens.css").read_text(encoding="utf-8")
SHELL = (ROOT / "assets/css/shell.css").read_text(encoding="utf-8")


def theme_vars(name):
    m = re.search(r'\[data-theme="%s"\]\s*\{(.*?)\n\}' % name, TOKENS, re.S)
    return dict(re.findall(r"--([\w-]+):\s*(#[0-9a-fA-F]{6})", m.group(1)))


def lum(h):
    c = [int(h[i:i + 2], 16) / 255 for i in (1, 3, 5)]
    c = [x / 12.92 if x <= 0.03928 else ((x + 0.055) / 1.055) ** 2.4 for x in c]
    return 0.2126 * c[0] + 0.7152 * c[1] + 0.0722 * c[2]


def ratio(a, b):
    la, lb = sorted((lum(a), lum(b)), reverse=True)
    return (la + 0.05) / (lb + 0.05)


class TestContrast(unittest.TestCase):
    def test_text_tokens_aa_on_surfaces(self):
        for theme in ("dark", "paper"):
            v = theme_vars(theme)
            for ink in ("ink", "ink-dim", "brand", "flow", "gate", "ok", "graph", "pink"):
                for bg in ("bg", "panel", "panel-2"):
                    self.assertGreaterEqual(ratio(v[ink], v[bg]), 4.5, f"{theme}: {ink} on {bg}")

    def test_control_border_3_to_1(self):
        for theme in ("dark", "paper"):
            v = theme_vars(theme)
            for bg in ("bg", "panel"):
                self.assertGreaterEqual(ratio(v["line-strong"], v[bg]), 3.0, f"{theme}: line-strong on {bg}")


class TestShellRules(unittest.TestCase):
    def test_global_reduced_motion(self):
        m = re.search(r"@media \(prefers-reduced-motion: reduce\)\s*\{\s*\*", SHELL)
        self.assertTrue(m, "shell.css needs a reduced-motion block that applies to every page")

    def test_global_focus_ring(self):
        self.assertIn(":focus-visible { outline: 2px solid", SHELL)

    def test_print_hides_chrome(self):
        self.assertRegex(SHELL, r"@media print\s*\{[^}]*\.mm-sb")

    def test_paper_overrides_use_aa_tokens(self):
        v = theme_vars("paper")
        for tok in ("brand", "ok", "gate"):
            self.assertGreaterEqual(ratio(v[tok], v["panel"]), 4.5)
        for sel in (".pos", ".late", ".fail"):
            self.assertIn('html[data-theme="paper"] ' + sel, SHELL)


class Test404(unittest.TestCase):
    def test_404_is_self_contained(self):
        html = (ROOT / "404.html").read_text(encoding="utf-8")
        self.assertIn('lang="en"', html)
        self.assertIn("<main", html)
        for url in re.findall(r'(?:href|src)="([^"]+)"', html):
            self.assertTrue(url.startswith("/"), f"404 must use root-absolute URLs: {url}")


if __name__ == "__main__":
    unittest.main()
