#!/usr/bin/env python3
"""
Tests for scripts/check_backlog.py (the upgrade backlog, Appendix C). Standard library only.

    python scripts/test_check_backlog.py
    python -m unittest discover -s scripts

The first class runs the checker on the committed data/docs/upgrade_backlog.md. The others build tiny
documents in a temporary folder, so each rule is pinned on its own.
"""
import contextlib
import importlib.util
import io
import sys
import tempfile
import unittest
from pathlib import Path

sys.dont_write_bytecode = True      # scripts/__pycache__ is tracked; do not make it show as modified

ROOT = Path(__file__).resolve().parent.parent


def load(name):
    spec = importlib.util.spec_from_file_location(name, ROOT / "scripts" / f"{name}.py")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


cb = load("check_backlog")
DOT = " \u00b7 "
DASH = "\u2014"


def entry(n=1, title="A feature", size="M", short="One line.", product="MiniMe", source="my idea",
          status="candidate", depends=DASH, decision="none", evidence="[V]", notes=None, drop=()):
    meta = DOT.join([f"**Product** {product}", f"**Source** {source}", f"**Status** {status}",
                     f"**Depends** {depends}", f"**Decision** {decision}", f"**Evidence** {evidence}"])
    parts = {"What": "It does a thing.", "Why": "Because.", "Where": "In a file.", "How": "1. Do it.",
             "Done when": "A test passes."}
    if notes:
        parts["Notes"] = notes
    paras = [f"**{k}.** {v}" for k, v in parts.items() if k not in drop]
    head = [f"### UB-{n:03d}: {title} ({size})", ""]
    if short is not None:
        head += [f"> {short}", ""]
    return "\n".join(head + [meta, ""] + ["\n\n".join(paras), ""])


def batch(bid="B01", date="2026-11-24", title="First batch", entries=()):
    return f"## Batch {bid} ({date}): {title}\n\n" + "\n".join(entries)


SOURCES = ("## 7. Sources register\n\n| Source | Link | Reported licence | Verdict | Used in | Checked |\n|---|---|---|---|---|---|\n"
           f"| a-repo | {DASH} | MIT | LEARN | UB-001 | {DASH} |\n")
LOG = "## 8. Decision log\n\n| Date | ID | Change | Note |\n|---|---|---|---|\n"


def doc_text(batches=None, sources=SOURCES, log=LOG, middle="## 3. How to add\n\nText.\n"):
    if batches is None:
        batches = [batch(entries=[entry(1)])]
    return ("# Upgrade Backlog\n\nIntro.\n\n## 0. At a glance\n\nx\n\n## 1. Register\n\nx\n\n## 2. Batches\n\nx\n\n"
            + middle + "\n" + sources + "\n" + log + "\n" + "\n".join(batches))


class Case(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.path = Path(self.tmp.name) / "doc.md"

    def tearDown(self):
        self.tmp.cleanup()

    def put(self, text):
        with open(self.path, "w", encoding="utf-8", newline="\n") as fh:
            fh.write(text)

    def ready(self, text=None):
        """Write a document and bring sections 0-2 up to date."""
        self.put(text if text is not None else doc_text())
        doc, problems, _ = cb.write(self.path)
        self.assertEqual(problems, [], problems)
        return doc

    def problems(self, text):
        self.put(text)
        doc = cb.parse(cb.read_lines(self.path))
        return cb.validate(doc)

    def assertProblem(self, text, kind, fragment):
        found = self.problems(text)
        self.assertTrue(any(p.startswith(kind + ":") and fragment in p for p in found),
                        f"expected a {kind} problem containing {fragment!r}, got {found}")

    def read(self):
        return self.path.read_text(encoding="utf-8")


class Committed(unittest.TestCase):
    def test_the_committed_document_passes(self):
        self.assertTrue(cb.DOC.exists(), "data/docs/upgrade_backlog.md is missing")
        doc, problems = cb.check(cb.DOC)
        self.assertEqual(problems, [], "\n".join(problems))
        self.assertGreater(len(doc.entries), 0)

    def test_the_document_uses_lf_only(self):
        self.assertNotIn(b"\r", cb.DOC.read_bytes())

    def test_every_batch_has_a_row_in_the_generated_table(self):
        doc, _ = cb.check(cb.DOC)
        text = cb.DOC.read_text(encoding="utf-8")
        for b in doc.batches:
            self.assertIn(f"| {b.id} | {b.date} |", text)

    def test_the_vocabulary_in_the_document_matches_the_script(self):
        text = cb.DOC.read_text(encoding="utf-8")
        for word in cb.STATUSES + cb.PRODUCTS + cb.SIZES:
            self.assertIn(word, text, f"{word} is not explained in the document")


class Shape(Case):
    def test_a_minimal_document_is_valid(self):
        self.ready()
        doc, problems = cb.check(self.path)
        self.assertEqual(problems, [])
        self.assertEqual([e.id for e in doc.entries], ["UB-001"])

    def test_short_line_is_required(self):
        self.assertProblem(doc_text([batch(entries=[entry(1, short=None)])]), "shape", "one-line summary")

    def test_short_line_length_limit(self):
        self.assertProblem(doc_text([batch(entries=[entry(1, short="x" * 141)])]), "shape", "141 characters")

    def test_short_line_cannot_hold_a_pipe(self):
        self.assertProblem(doc_text([batch(entries=[entry(1, short="a | b")])]), "shape", "cannot contain")

    def test_title_cannot_hold_a_pipe(self):
        self.assertProblem(doc_text([batch(entries=[entry(1, title="a | b")])]), "shape", "title cannot contain")

    def test_bad_entry_heading(self):
        text = doc_text([batch(entries=[entry(1), "### UB-2: Wrong id (M)\n\nx\n"])])
        self.assertProblem(text, "shape", "entry heading must read")

    def test_bad_size_in_heading(self):
        text = doc_text([batch(entries=[entry(1), "### UB-002: Odd size (XXL)\n\nx\n"])])
        self.assertProblem(text, "shape", "entry heading must read")

    def test_missing_metadata_line(self):
        e = entry(1).replace("**Product**", "**Prod**")
        self.assertProblem(doc_text([batch(entries=[e])]), "shape", "metadata line")

    def test_missing_metadata_field(self):
        e = entry(1).replace(DOT + "**Evidence** [V]", "")
        self.assertProblem(doc_text([batch(entries=[e])]), "shape", "Evidence is missing")

    def test_unknown_metadata_field(self):
        e = entry(1).replace("**Evidence** [V]", "**Evidence** [V]" + DOT + "**Owner** me")
        self.assertProblem(doc_text([batch(entries=[e])]), "shape", "unknown metadata field Owner")

    def test_bad_product(self):
        self.assertProblem(doc_text([batch(entries=[entry(1, product="Robots")])]), "shape", "Product")

    def test_bad_status(self):
        self.assertProblem(doc_text([batch(entries=[entry(1, status="maybe")])]), "shape", "Status")

    def test_every_status_and_product_is_accepted(self):
        for s in cb.STATUSES:
            notes = "Because." if s in ("parked", "dropped") else None
            self.assertEqual(self.problems(doc_text([batch(entries=[entry(1, status=s, notes=notes)])])), [], s)
        for p in cb.PRODUCTS:
            self.assertEqual(self.problems(doc_text([batch(entries=[entry(1, product=p)])])), [], p)

    def test_missing_paragraph(self):
        for name in cb.PARAGRAPHS:
            self.assertProblem(doc_text([batch(entries=[entry(1, drop=(name,))])]), "shape", f"**{name}.**")

    def test_parked_and_dropped_need_a_reason(self):
        for s in ("parked", "dropped"):
            self.assertProblem(doc_text([batch(entries=[entry(1, status=s)])]), "shape", "needs a **Notes.**")

    def test_a_paragraph_may_span_lines_and_lists(self):
        e = entry(1).replace("**How.** 1. Do it.", "**How.**\n\n1. Do it.\n2. Then this.\n")
        self.assertEqual(self.problems(doc_text([batch(entries=[e])])), [])

    def test_a_code_fence_is_not_structure(self):
        example = ("## 3. How to add\n\n````markdown\n### UB-nnn: Example (M)\n\n## Batch Bnn (date): x\n\n"
                   "Depends on UB-777.\n````\n")
        self.assertEqual(self.problems(doc_text(middle=example)), [])

    def test_an_unclosed_fence_hides_the_rest_but_a_closed_one_does_not(self):
        example = "## 3. How to add\n\n```\ncode\n```\n\nUB-777 is mentioned here.\n"
        self.assertProblem(doc_text(middle=example), "id", "UB-777")

    def test_carriage_return_is_refused(self):
        self.put(doc_text().replace("\n", "\r\n"))
        doc = cb.parse(cb.read_lines(self.path))
        self.assertTrue(any(p.startswith("text:") for p in doc.problems))


class Ids(Case):
    def test_duplicate_id(self):
        self.assertProblem(doc_text([batch(entries=[entry(1), entry(1, title="Again")])]), "id", "used twice")

    def test_ids_must_increase(self):
        self.assertProblem(doc_text([batch(entries=[entry(2), entry(1, title="Late")])]), "id", "must be higher")

    def test_gaps_are_allowed(self):
        self.assertEqual(self.problems(doc_text([batch(entries=[entry(1), entry(7, title="Later")])])), [])

    def test_depends_on_a_missing_entry(self):
        self.assertProblem(doc_text([batch(entries=[entry(1, depends="UB-009")])]), "id", "does not exist")

    def test_depends_on_itself(self):
        self.assertProblem(doc_text([batch(entries=[entry(1, depends="UB-001")])]), "id", "depends on itself")

    def test_depends_loop(self):
        text = doc_text([batch(entries=[entry(1, depends="UB-002"), entry(2, title="B", depends="UB-001")])])
        self.assertProblem(text, "id", "Depends loop")

    def test_depends_on_several(self):
        text = doc_text([batch(entries=[entry(1), entry(2, title="B"), entry(3, title="C", depends="UB-001, UB-002")])])
        self.assertEqual(self.problems(text), [])

    def test_depends_must_be_ids(self):
        self.assertProblem(doc_text([batch(entries=[entry(1, depends="later")])]), "id", "not a feature id")

    def test_unknown_id_mentioned_in_prose(self):
        text = doc_text(middle="## 3. How to add\n\nSee UB-042 for an example.\n")
        self.assertProblem(text, "id", "UB-042 is mentioned")

    def test_an_id_with_fewer_digits_is_not_a_reference(self):
        self.assertEqual(self.problems(doc_text(middle="## 3. How to add\n\nUse UB-nnn or UB-12.\n")), [])


class Batches(Case):
    def test_entry_outside_a_batch(self):
        text = doc_text([entry(1)])
        self.assertProblem(text, "batch", "not inside a batch")

    def test_entry_after_another_section_is_outside_a_batch(self):
        text = doc_text([batch(entries=[entry(1)]), "## 9. Appendix\n\n" + entry(2, title="Stray")])
        self.assertProblem(text, "batch", "not inside a batch")

    def test_batch_without_entries(self):
        self.assertProblem(doc_text([batch(entries=[entry(1)]), batch("B02", "2026-11-25", "Empty", [])]),
                           "batch", "has no entries")

    def test_batch_ids_ascend(self):
        text = doc_text([batch("B02", entries=[entry(1)]), batch("B01", "2026-11-25", "B", [entry(2, title="B")])])
        self.assertProblem(text, "batch", "must be higher")

    def test_duplicate_batch(self):
        text = doc_text([batch(entries=[entry(1)]), batch("B01", "2026-11-25", "B", [entry(2, title="B")])])
        self.assertProblem(text, "batch", "appears twice")

    def test_bad_date(self):
        self.assertProblem(doc_text([batch(date="2026-13-40", entries=[entry(1)])]), "batch", "not a real date")

    def test_dates_do_not_go_backwards(self):
        text = doc_text([batch(entries=[entry(1)]), batch("B02", "2026-11-01", "B", [entry(2, title="B")])])
        self.assertProblem(text, "batch", "dated before")

    def test_malformed_batch_heading(self):
        self.assertProblem(doc_text([batch(entries=[entry(1)]), "## Batch two\n\nx\n"]), "batch", "must read")

    def test_two_batches_are_fine(self):
        text = doc_text([batch(entries=[entry(1)]), batch("B02", "2026-11-25", "B", [entry(2, title="B")])])
        self.assertEqual(self.problems(text), [])


class Tables(Case):
    def test_sources_row_needs_six_cells(self):
        bad = SOURCES + "| x | y |\n"
        self.assertProblem(doc_text(sources=bad), "tables", "6 cells")

    def test_sources_duplicate(self):
        bad = SOURCES + f"| A-Repo | {DASH} | MIT | LEARN | {DASH} | {DASH} |\n"
        self.assertProblem(doc_text(sources=bad), "tables", "listed twice")

    def test_sources_empty_checked(self):
        bad = SOURCES + f"| b | {DASH} | MIT | LEARN | {DASH} |  |\n"
        self.assertProblem(doc_text(sources=bad), "tables", "empty Checked")

    def test_sources_unknown_feature(self):
        bad = SOURCES + f"| b | {DASH} | MIT | LEARN | UB-099 | {DASH} |\n"
        self.assertProblem(doc_text(sources=bad), "id", "UB-099 is mentioned")

    def test_sources_section_is_required(self):
        self.assertProblem(doc_text(sources=""), "tables", "Sources register")

    def test_log_row_checks(self):
        self.assertProblem(doc_text(log=LOG + "| yesterday | UB-001 | x | y |\n"), "tables", "not a date")
        self.assertProblem(doc_text(log=LOG + "| 2026-11-24 | UB-001 | x |\n"), "tables", "4 cells")
        self.assertProblem(doc_text(log=LOG + f"| 2026-11-24 | {DASH} |  | y |\n"), "tables", "empty Change")

    def test_log_general_decision_uses_a_dash(self):
        self.assertEqual(self.problems(doc_text(log=LOG + f"| 2026-11-24 | {DASH} | D-1 decided | option a |\n")), [])

    def test_log_header_must_match(self):
        bad = LOG.replace("| Date | ID | Change | Note |", "| When | ID | Change | Note |")
        self.assertProblem(doc_text(log=bad), "tables", "header must be exactly")


class Generation(Case):
    def test_write_is_idempotent(self):
        self.ready()
        first = self.read()
        doc, problems, changed = cb.write(self.path)
        self.assertEqual(problems, [])
        self.assertFalse(changed)
        self.assertEqual(self.read(), first)

    def test_check_reports_stale_sections(self):
        self.ready()
        self.put(self.read().replace("**Status** candidate", "**Status** accepted"))
        _, problems = cb.check(self.path)
        self.assertTrue(any(p.startswith("stale:") for p in problems), problems)
        cb.write(self.path)
        _, problems = cb.check(self.path)
        self.assertEqual(problems, [])

    def test_write_refuses_an_invalid_document(self):
        self.put(doc_text([batch(entries=[entry(1, status="maybe")])]))
        before = self.read()
        _, problems, _ = cb.write(self.path)
        self.assertTrue(problems)
        self.assertEqual(self.read(), before)

    def test_a_missing_generated_section_is_reported(self):
        self.put(doc_text().replace("## 1. Register", "## 1. Table"))
        _, problems = cb.check(self.path)
        self.assertTrue(any("1. Register" in p for p in problems), problems)

    def test_register_row_carries_every_field(self):
        self.ready(doc_text([batch(entries=[entry(1, title="Alpha", size="L", short="Does alpha.", product="M2C",
                                                  source="repo-x", status="accepted")])]))
        self.assertIn("| UB-001 | Alpha | Does alpha. | M2C | repo-x | L | accepted | B01 |", self.read())

    def test_register_is_sorted_by_id(self):
        self.ready(doc_text([batch(entries=[entry(1, title="One"), entry(2, title="Two")])]))
        text = self.read()
        self.assertLess(text.index("| UB-001 | One"), text.index("| UB-002 | Two"))

    def test_counts(self):
        self.ready(doc_text([batch(entries=[
            entry(1, product="MiniMe", status="candidate"), entry(2, title="B", product="MiniMe", status="accepted"),
            entry(3, title="C", product="M2C", status="candidate")])]))
        text = self.read()
        self.assertIn("**3 features** in 1 batch: 2 candidate \u00b7 1 accepted \u00b7 0 building", text)
        self.assertIn("| MiniMe | 1 | 1 | 0 | 0 | 0 | 0 | 2 |", text)
        self.assertIn("| M2C | 1 | 0 | 0 | 0 | 0 | 0 | 1 |", text)
        self.assertIn("| **All** | **2** | **1** | **0** | **0** | **0** | **0** | **3** |", text)

    def test_batch_table(self):
        self.ready(doc_text([batch(entries=[entry(1), entry(2, title="B")]),
                             batch("B02", "2026-11-25", "Second", [entry(5, title="C")])]))
        text = self.read()
        self.assertIn("| B01 | 2026-11-24 | First batch | 2 | UB-001 to UB-002 |", text)
        self.assertIn("| B02 | 2026-11-25 | Second | 1 | UB-005 |", text)

    def test_hand_written_parts_are_untouched(self):
        self.ready()
        text = self.read()
        self.assertIn("## 3. How to add\n\nText.\n", text)
        self.assertIn("| a-repo |", text)

    def test_adding_a_batch_changes_only_what_it_should(self):
        self.ready()
        before = self.read()
        self.put(before + "\n" + batch("B02", "2026-11-25", "Second", [entry(2, title="Next")]))
        cb.write(self.path)
        after = self.read()
        self.assertEqual(cb.check(self.path)[1], [])
        self.assertIn("UB-002", after)
        self.assertIn("| a-repo |", after)


class SetStatus(Case):
    def test_changes_status_logs_it_and_regenerates(self):
        self.ready()
        self.assertEqual(cb.set_status(self.path, "UB-001", "accepted", "go ahead", "2026-11-26"), [])
        text = self.read()
        self.assertIn("**Status** accepted", text)
        self.assertIn("| 2026-11-26 | UB-001 | candidate -> accepted | go ahead |", text)
        self.assertIn("| UB-001 | A feature | One line. | MiniMe | my idea | M | accepted | B01 |", text)
        self.assertEqual(cb.check(self.path)[1], [])

    def test_same_status_is_refused(self):
        self.ready()
        self.assertTrue(cb.set_status(self.path, "UB-001", "candidate"))

    def test_unknown_id_and_status(self):
        self.ready()
        self.assertTrue(cb.set_status(self.path, "UB-009", "accepted"))
        self.assertTrue(cb.set_status(self.path, "UB-001", "maybe"))

    def test_dropping_needs_a_reason_and_keeps_the_shape(self):
        self.ready()
        self.assertTrue(cb.set_status(self.path, "UB-001", "dropped"))
        self.assertEqual(cb.set_status(self.path, "UB-001", "dropped", "licence does not fit", "2026-11-26"), [])
        self.assertIn("**Notes.** licence does not fit", self.read())
        self.assertEqual(cb.check(self.path)[1], [])

    def test_pipe_in_note_is_made_safe(self):
        self.ready()
        self.assertEqual(cb.set_status(self.path, "UB-001", "accepted", "a | b", "2026-11-26"), [])
        self.assertEqual(cb.check(self.path)[1], [])

    def test_refuses_an_invalid_document(self):
        self.put(doc_text([batch(entries=[entry(1, status="maybe")])]))
        self.assertTrue(cb.set_status(self.path, "UB-001", "accepted"))


class Cli(Case):
    def run_cli(self, *args):
        out = io.StringIO()
        with contextlib.redirect_stdout(out):
            code = cb.main(["--doc", str(self.path), *args])
        return code, out.getvalue()

    def test_check_passes_and_fails(self):
        self.ready()
        self.assertEqual(self.run_cli("--check")[0], 0)
        self.assertEqual(self.run_cli()[0], 0)
        self.put(self.read().replace("**Status** candidate", "**Status** nope"))
        code, out = self.run_cli("--check")
        self.assertEqual(code, 1)
        self.assertIn("Status", out)

    def test_write_command(self):
        self.put(doc_text())
        code, out = self.run_cli("--write")
        self.assertEqual(code, 0)
        self.assertIn("rewritten", out)
        self.assertIn("already current", self.run_cli("--write")[1])

    def test_next_id(self):
        self.ready(doc_text([batch(entries=[entry(1), entry(4, title="B")])]))
        self.assertEqual(self.run_cli("--next-id")[1].strip(), "UB-005")

    def test_list_and_filters(self):
        self.ready(doc_text([batch(entries=[entry(1, product="M2C"), entry(2, title="B", status="accepted")])]))
        code, out = self.run_cli("--list")
        self.assertEqual(code, 0)
        self.assertEqual(len(out.strip().splitlines()), 2)
        self.assertEqual(len(self.run_cli("--list", "--status", "accepted")[1].strip().splitlines()), 1)
        self.assertEqual(len(self.run_cli("--list", "--product", "M2C")[1].strip().splitlines()), 1)

    def test_set_status_command(self):
        self.ready()
        code, out = self.run_cli("--set-status", "UB-001", "accepted", "--note", "yes", "--date", "2026-11-26")
        self.assertEqual(code, 0, out)
        self.assertEqual(self.run_cli("--check")[0], 0)

    def test_missing_file(self):
        self.path.unlink(missing_ok=True)
        self.assertEqual(self.run_cli("--check")[0], 1)


if __name__ == "__main__":
    unittest.main()
