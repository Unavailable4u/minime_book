// blocks.js of the Explorer (P14d): line ranges, anchor search, block alignment, which block / function a line is in, card stacking,
// and a run over every real note in data/notes against its embedded source.
//   node blocks.mjs
import assert from "node:assert/strict";
import fs from "node:fs";
import path from "node:path";
import { fileURLToPath } from "node:url";
import * as B from "../../assets/js/explorer/blocks.js";
import { splitLines } from "../../assets/js/explorer/model.js";

const ROOT = path.resolve(path.dirname(fileURLToPath(import.meta.url)), "..", "..");
let n = 0;
const t = async (name, f) => { try { await f(); n++; console.log(`ok: ${name}`); } catch (e) { console.log(`FAIL: ${name}\n  ${e.message}`); process.exitCode = 1; } };
const lines = (count, over = {}) => Array.from({ length: count }, (_, i) => over[i + 1] ?? `line ${i + 1}`);

await t("parseLineRange: ranges, single lines, en dash, junk", () => {
  assert.deepEqual(B.parseLineRange("628-735"), { start: 628, end: 735 });
  assert.deepEqual(B.parseLineRange(" 7 "), { start: 7, end: 7 });
  assert.deepEqual(B.parseLineRange("10–20"), { start: 10, end: 20 });
  assert.deepEqual(B.parseLineRange(42), { start: 42, end: 42 });
  for (const bad of ["", null, undefined, "0", "0-5", "20-10", "a-b", "1-2-3", "12,15", "-5"]) assert.equal(B.parseLineRange(bad), null, String(bad));
});

await t("findAnchor: the stated line wins, then the nearest starts-with, then the nearest contains", () => {
  const L = lines(300, { 100: "def run(x):", 110: "    def run(x):  # nested", 120: "x = run_things(y)", 103: "  def run(x):" });
  assert.deepEqual(B.findAnchor(L, 100, "def run(x):"), { line: 100, tier: 3 });
  assert.deepEqual(B.findAnchor(L, 100, "def run"), { line: 100, tier: 2 });
  assert.deepEqual(B.findAnchor(L, 101, "def run(x):"), { line: 100, tier: 3 }, "one line off: the nearest (here: 1 line back) wins");
  assert.deepEqual(B.findAnchor(L, 104, "def run(x):"), { line: 103, tier: 3 }, "whitespace is ignored, so the indented copy counts as the same text");
  assert.deepEqual(B.findAnchor(L, 118, "run_things"), { line: 120, tier: 1 }, "a bare name is found inside a longer line");
  assert.equal(B.findAnchor(L, 100, "run_things")?.line, 120, "contains-match is only used when nothing starts with the anchor... and here nothing near 100 does");
  assert.equal(B.findAnchor(L, 5, "def run(x):"), null, "beyond SEARCH lines there is no match");
  assert.equal(B.findAnchor(L, 100, ""), null);
  assert.equal(B.findAnchor(L, 100, "   "), null);
  assert.equal(B.findAnchor(L, 100, "def x"), null, "a text that is nowhere is not found");
  assert.equal(B.findAnchor(lines(10, { 5: "xx abc def" }), 5, "abc"), null, "anchors under 4 characters are never matched by 'contains'");
  assert.equal(B.findAnchor(lines(10, { 5: "xx abcd def" }), 5, "abcd")?.line, 5, "4 characters are enough");
});

await t("findAnchor: on a tie the line after the stated one wins", () => {
  const L = lines(50, { 20: "marker one", 24: "marker one" });
  assert.equal(B.findAnchor(L, 22, "marker one").line, 24);
});

await t("alignBlocks: ok, shifted, unverified, outside, bad; sorted by start; ids follow the note order", () => {
  const L = lines(150, { 10: "def run(x):  # c", 125: "def later():", 145: "tail" });
  const blocks = [
    { lines: "120-141", anchor: "def later():", title: "Later", text: "t3" },   // 5 lines off  -> shifted to 125-146
    { lines: "10-20", anchor: "def run(x):", title: "Run", text: " t1 " },    // right place -> ok
    { lines: "60-70", anchor: "nowhere at all", title: "Lost", text: "t2" },   // unverified
    { lines: "400-410", anchor: "x", title: "Past the end" },                  // outside
    { lines: "twenty", title: "Broken" },                                       // bad
    null,
    { lines: "140-200", title: "Runs off", anchor: "tail" },                   // anchor 5 lines further down; the end is clamped to the file
  ];
  const { items, skipped } = B.alignBlocks(blocks, L);
  assert.deepEqual(items.map((i) => [i.id, i.pos, i.start, i.end, i.state]), [
    ["b2", 0, 10, 20, "ok"], ["b3", 1, 60, 70, "unverified"], ["b1", 2, 125, 146, "shifted"], ["b7", 3, 145, 150, "shifted"],
  ]);
  assert.equal(items[0].text, "t1", "text is trimmed");
  assert.equal(items[2].shift, 5); assert.deepEqual(items[2].given, { start: 120, end: 141 });
  assert.deepEqual(skipped.map((s) => [s.index, s.why]), [[3, "outside"], [4, "lines"]]);
  assert.deepEqual(B.alignBlocks(undefined, L), { items: [], skipped: [] });
  assert.deepEqual(B.alignBlocks("nope", L), { items: [], skipped: [] });
});

await t("alignBlocks: a shifted block never ends before it starts or after the file", () => {
  const L = lines(30, { 28: "anchor line" });
  const { items } = B.alignBlocks([{ lines: "20-22", anchor: "anchor line", title: "x" }], L);
  assert.deepEqual([items[0].start, items[0].end, items[0].state], [28, 30, "shifted"]);
});

await t("alignBlocks: equal starts keep the note order", () => {
  const { items } = B.alignBlocks([{ lines: "5-9", title: "first" }, { lines: "5-7", title: "second" }], lines(20));
  assert.deepEqual(items.map((i) => i.title), ["first", "second"]);
});

await t("blockAtLine: innermost start wins, none between blocks", () => {
  const { items } = B.alignBlocks([{ lines: "10-100", title: "outer" }, { lines: "40-60", title: "inner" }, { lines: "200-210", title: "far" }], lines(300));
  const at = (l) => B.blockAtLine(items, l)?.title ?? null;
  assert.deepEqual([5, 10, 39, 40, 60, 61, 100, 101, 150, 205].map(at), [null, "outer", "outer", "inner", "inner", "outer", "outer", null, null, "far"]);
  assert.equal(B.blockAtLine([], 5), null);
});

await t("symbolAtLine: the smallest symbol that contains the line", () => {
  const rows = [{ qual: "Agent", start: 25, end: 50, kind: "class" }, { qual: "Agent.step", start: 30, end: 40, kind: "method" }, { qual: "run", start: 10, end: 20, kind: "function" }];
  const at = (l) => B.symbolAtLine(rows, l)?.qual ?? null;
  assert.deepEqual([1, 10, 20, 21, 25, 30, 40, 41, 50, 51].map(at), [null, "run", "run", null, "Agent", "Agent.step", "Agent.step", "Agent", "Agent", null]);
  assert.equal(B.symbolAtLine(undefined, 3), null);
});

await t("layoutCards: cards keep their height, and are pushed down when they would overlap", () => {
  assert.deepEqual(B.layoutCards([{ top: 0, height: 50 }, { top: 200, height: 50 }]), [0, 200]);
  assert.deepEqual(B.layoutCards([{ top: 0, height: 50 }, { top: 10, height: 50 }, { top: 20, height: 30 }]), [0, 58, 116]);
  assert.deepEqual(B.layoutCards([{ top: 100, height: 40 }, { top: 148, height: 40 }], 8), [100, 148], "exactly the gap apart is not pushed");
  assert.deepEqual(B.layoutCards([{ top: 100, height: 40 }, { top: 147, height: 40 }], 8), [100, 148]);
  assert.deepEqual(B.layoutCards([]), []);
  assert.deepEqual(B.layoutCards([{ top: 5 }, { top: 6 }]), [5, 13], "an unmeasured card counts as height 0");
});

await t("nextBlock: n and p", () => {
  const { items } = B.alignBlocks([{ lines: "10-20", title: "a" }, { lines: "30-40", title: "b" }, { lines: "50-60", title: "c" }], lines(100));
  const nx = (l, d) => B.nextBlock(items, l, d)?.title ?? null;
  assert.deepEqual([1, 10, 25, 30, 55, 60].map((l) => nx(l, 1)), ["a", "b", "b", "c", null, null]);
  assert.deepEqual([1, 10, 11, 30, 31, 80].map((l) => nx(l, -1)), [null, null, "a", "a", "b", "c"]);
});

/* Every real note against its real embedded source: nothing may land outside the file, and few blocks may be unverified. */
await t("real notes: every block is placed inside its file; the anchors mostly hold", () => {
  const dir = path.join(ROOT, "data", "notes");
  let files = 0, total = 0, ok = 0, shifted = 0, unverified = 0, skipped = 0, bad = 0;
  for (const f of fs.readdirSync(dir).filter((x) => x.endsWith(".json")).sort()) {
    const note = JSON.parse(fs.readFileSync(path.join(dir, f), "utf8"));
    const src = path.join(ROOT, "data", "src", `${note.path}.txt`);
    if (!note.blocks || !note.blocks.length || !fs.existsSync(src)) continue;
    files++;
    const L = splitLines(fs.readFileSync(src, "utf8"));
    const r = B.alignBlocks(note.blocks, L);
    skipped += r.skipped.length;
    bad += r.skipped.filter((s) => s.why === "lines").length;
    for (const it of r.items) {
      total++;
      assert.ok(it.start >= 1 && it.start <= it.end && it.end <= L.length, `${note.path} ${it.id}: ${it.start}-${it.end} of ${L.length}`);
      if (it.state === "ok") ok++; else if (it.state === "shifted") shifted++; else unverified++;
    }
    assert.deepEqual(r.items.map((i) => i.start), r.items.map((i) => i.start).sort((a, b) => a - b), `${note.path}: sorted`);
  }
  console.log(`   ${files} files, ${total} blocks: ${ok} ok, ${shifted} moved, ${unverified} not checked, ${skipped} left out (${bad} with invalid lines)`);
  assert.ok(files > 0 && total > 0, "found notes with blocks");
  assert.equal(bad, 0, "no note has an invalid line range");
  assert.ok(unverified / total < 0.1, `fewer than 10 % of the blocks are unverified (${unverified}/${total})`);
  assert.ok(ok / total > 0.7, `most anchors are where the note says (${ok}/${total})`);
});

console.log(`${n} passed`);
