---
name: epub-digest-embed
description: >-
  Embed per-chapter summaries directly INTO an .epub file and register them in the
  book's table of contents, so any e-reader shows the digests inline and in its
  navigation. ALWAYS use this skill when the user wants to bake summaries into a
  book file itself — phrasings like "вшей конспект в книгу", "встрой саммари в
  epub", "сделай epub с выжимками по главам", "добавь конспекты в содержание
  книги", "embed chapter summaries into this epub", "put summaries before each
  chapter and in the TOC". This is DIFFERENT from just answering with a summary in
  chat (that's the book-chapter-digest skill): here the deliverable is a modified
  .epub. This skill REUSES book-chapter-digest for the actual summary content and
  adds the segmentation, injection, and TOC-patching on top.
---

# EPUB Digest Embed

Produce a new `.epub` that is the original book plus auto-generated chapter
digests, placed both as a "Конспект по главам" section near the front and inline
before each chapter, with matching entries added to the table of contents (NCX +
EPUB3 nav) so e-readers can navigate to them.

## The one rule that defines this skill

**The summary content is NOT owned here.** Wording, length, structure, the
grounding discipline, the verdict line — all of that belongs to the
`book-chapter-digest` skill. This skill only decides *how the book is segmented
into units*, then *mechanically embeds* whatever digests that skill produces.

So for every summary unit you must **read `book-chapter-digest`'s `SKILL.md` and
follow it verbatim** to write the digest. Do **not** restate, paraphrase, or
re-invent its template here. If that skill's format changes later, this skill
must pick up the change automatically — which only works if you delegate instead
of duplicating. (Locate it at `/mnt/skills/user/book-chapter-digest`; if it's
moved, find it by name.)

This skill is **EPUB-only** (injection needs the zip/XHTML structure). For other
formats, tell the user it only embeds into `.epub`.

## Workflow

### 1. Build the index (reuse book-chapter-digest's parser)

Copy the uploaded epub to a writable dir, then run the existing parser — it now
also records each chapter's in-book location (`epub_file`, `epub_anchor`), which
the injection step needs:

```bash
cp /mnt/user-data/uploads/<book>.epub /home/claude/book.epub
python /mnt/skills/user/book-chapter-digest/scripts/build_index.py \
    /home/claude/book.epub --cache-dir /home/claude/book.digest
```

Sanity-check the chapter table exactly as `book-chapter-digest` instructs
(front/back matter, tiny divider rows, huge undivided blobs). The index is a
first pass, not ground truth.

### 2. Analyze structure and draft a segmentation plan

```bash
python scripts/plan_helper.py --epub /home/claude/book.epub --cache-dir /home/claude/book.digest
```

This writes `structure.json` (per chapter: word count + internal headings with
anchors) and `plan_draft.json` (a conservative 1:1 draft), and prints a report.

### 3. Decide the real segmentation — YOUR judgment, per book

This is the decision the old skill left to the human. Now you make it. **Counts
are signals, not verdicts — open the actual text when anything looks off.** Every
book is different; never trust the script blindly.

Default policy is **conservative**:

- **Normal chapter → one unit (1:1).** This is the default and the right answer
  for most books.
- **A genuinely huge chapter → split into sub-units**, but only when it's far
  bigger than the book's own median (roughly ≥2.5× median *and* large in
  absolute terms) AND it has clean internal headings with anchors (see
  `structure.json`). Group adjacent small sections so each sub-unit is a sensible
  size. If a huge chapter has no usable internal structure, split the extracted
  text at logical seams instead, or keep it whole with a longer digest — judge
  from the text.
- **A swarm of tiny chapters → group adjacent ones** into units of about median
  size (e.g. a book that splits every micro-idea into its own 1-page "chapter").
  Prefer grouping along a real seam (a Part divider) or by theme.

Borderline chapters (somewhat above median but not extreme) stay **whole** by
default.

**Introductions are content, not throwaway front-matter.** An Introduction /
Preface / Foreword / Prologue / Epilogue / Conclusion almost always carries the
book's core framing — never skip it. `plan_helper.py` already protects these and
keeps any "matter"-flagged section that is substantial (≥1500 words), but the
flag is advisory: scan the report yourself and rescue anything that actually
holds ideas, skip only true service pages (copyright, dedication, TOC,
acknowledgments, index, notes-only).

Edit `plan_draft.json` into the final `plan.json`. Each unit needs:
`id`, `kind` (`chapter`/`subsection`/`group`), `label`, `source_chapters` (index
numbers), `inject_file`, `inject_anchor` (id to insert before, or `null` for top
of chapter), and — for subsection units — `section_ids`. Also set top-level
`"placement"` and `"toc"` (defaults `"both"`/`"both"`).

### 4. Show the plan to the user and get the go-ahead

Always present the plan before generating anything — it's a judgment call and the
output is a rewritten book. Show it compactly, e.g.:

```
План (13 единиц):
  • Introduction + главы 1–11 + Conclusion — по одной выжимке (1:1)
  • Служебное (Copyright, Dedication, Contents, Acknowledgments, Notes) — пропуск
Размещение: раздел в начале + inline перед главой. Содержание: и раздел, и подпункты.
```

Let them adjust (merge/split/skip units) before proceeding.

### 5. Generate the digests (delegating to book-chapter-digest)

For each unit, extract its real text and write the digest **per
book-chapter-digest's SKILL.md**:

```bash
# whole chapter:
python /mnt/skills/user/book-chapter-digest/scripts/extract_chapter.py /home/claude/book.digest <n>
# a subsection unit: extract the chapter, then use only the section spanning its section_ids
```

Read the extracted text in full, then write the digest from that text only
(grounding rules are that skill's, not yours). Put each unit's finished Markdown
into its `"md"` field in `plan.json`.

### 6. Inject and patch the TOC

```bash
python scripts/inject_digest.py \
    --epub /home/claude/book.epub \
    --plan /home/claude/plan.json \
    --cache-dir /home/claude/book.digest \
    --md-out /mnt/user-data/outputs/"<book> — конспект.md" \
    --out /mnt/user-data/outputs/"<book> (с конспектом).epub"
```

This produces **two deliverables**: the new epub (front "Конспект по главам"
document + a styled digest callout before each unit's anchor + NCX/nav entries),
**and** a standalone Markdown digest of the whole book (`--md-out`). It rezips
correctly (mimetype first/stored) and keeps the original untouched. Watch its
stdout for `⚠️` warnings (e.g. an anchor it couldn't find).

### 7. VERIFY — and rebuild if not perfect (mandatory)

You are responsible for a correct output. A broken or wrong file is **not an
option**. Always run the verifier:

```bash
python scripts/verify_epub.py --epub /mnt/user-data/outputs/"<book> (с конспектом).epub" \
    --plan /home/claude/plan.json --cache-dir /home/claude/book.digest
```

It checks zip/mimetype, well-formedness of every XHTML/OPF/NCX, that each unit's
digest actually landed **in the right place with the right text** (a probe from
each unit's text must appear inside its front section and inline block, and the
inline block must sit before the chapter heading), and that every TOC link we
added resolves to a real anchor.

If it **FAILS**: read the specific problems, diagnose the cause (bad anchor, a
chapter whose content lives in a shared file, malformed source XHTML, etc.),
**fix it and rebuild**, then verify again. Loop until it passes — do not ship a
failing file.

If it **PASSES**: additionally open 1–2 spots yourself (the front digest doc and
one chapter file) and eyeball that the callout renders where expected and reads
like the right chapter's summary. Only then deliver. (Don't re-read all summaries
— that's wasteful; spot-check.)

### 8. Deliver

`present_files` **both** outputs — the epub first, then the Markdown digest.
Never overwrite the uploaded original.

## Scripts

- `scripts/plan_helper.py` — structure report + conservative draft plan
  (protects intro-type and substantial sections from being skipped).
- `scripts/inject_digest.py` — md→XHTML, front doc, inline callouts, NCX/nav
  patching, valid rezip, **and** the standalone Markdown digest (`--md-out`).
  Consumes `plan.json` (with `md` filled in).
- `scripts/verify_epub.py` — mandatory post-build check; non-zero exit on any
  problem so you know to rebuild.
- Reused from `book-chapter-digest`: `build_index.py` (now emits
  `epub_file`/`epub_anchor`) and `extract_chapter.py`.

## Notes on robustness

EPUBs vary wildly. The injector targets the common, spec-compliant cases (NCX
and/or EPUB3 nav, XHTML content). If the nav can't be patched, NCX still covers
most readers and the script warns rather than failing. If `build_index.py`
can't split the book (DRM, scanned PDF-in-epub, one giant blob), stop and tell
the user — don't fabricate structure.
