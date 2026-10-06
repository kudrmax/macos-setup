---
name: epub-digest-embed
description: >-
  Embed per-chapter summaries directly INTO an .epub file and register them in the
  book's table of contents, so any e-reader shows the digests inline and in its
  navigation. For LARGE books (many chapters / hundreds of pages), where a single
  agent's context would overflow, it switches to an ORCHESTRATED mode: it fans the
  per-chapter digest writing out to parallel subagents (one per batch of chapters)
  and then reconciles them into a coherent whole. Use it when the user wants to
  bake summaries into an .epub — phrasings like "вшей конспект в книгу",
  "встрой саммари в epub", "сделай epub с выжимками по главам", "добавь
  конспекты в содержание книги", "embed chapter summaries into this epub". A small book is handled by a simple linear mode
  without subagents. It REUSES book-chapter-digest for the actual summary content
  and adds segmentation, orchestration, injection, and TOC-patching on top.
---

# EPUB Digest Embed

Produce a new `.epub` that is the original book plus auto-generated chapter
digests, placed both as a "Конспект по главам" section near the front and inline
before each chapter, with matching entries added to the table of contents (NCX +
EPUB3 nav) so e-readers can navigate to them.

**Two modes.** For a large book, writing every chapter's digest in one agent
overflows its context (the full text of hundreds of pages can't coexist with
everything else). The skill solves this by **orchestration** — a lightweight
coordinator that never holds the full book text, a fleet of **worker subagents**
that each read only their batch of chapters and write those digests, and a single
**reviser subagent** that stitches the compact finished digests into a coherent
book. For a small book none of that pays off, so it uses the **linear
small-book mode**: you write every digest yourself, one unit after another.

## Setup (once per machine)

The scripts need `lxml`, `markdown` and `pypdf`. They live in a shared venv
(never install them globally):

```bash
test -x ~/.claude/skills/.venv/bin/python || \
  (python3 -m venv ~/.claude/skills/.venv && ~/.claude/skills/.venv/bin/pip install lxml markdown pypdf)
```

Always run the scripts with `~/.claude/skills/.venv/bin/python`, never with a
bare `python`/`python3`.

## Paths

- `<book>` — the absolute path to the .epub the user gave. It is only read, never
  modified.
- `<work>` — the working directory next to the book: `<book-dir>/<book-stem>.digest/`
  (the cache dir `build_index.py` creates by default). `plan.json` and all
  intermediate files go there.
- Outputs go next to the book: `<book-dir>/<book-stem> (с конспектом).epub` and
  `<book-dir>/<book-stem> — конспект.md`. If the book's directory is not
  writable, use `$TMPDIR/<book-stem>.digest/` for both `<work>` and the outputs.

## The one rule that defines this skill

**The summary content is NOT owned here.** Wording, length, structure, the
grounding discipline, the verdict line — all of that belongs to the
`book-chapter-digest` skill. This skill only decides *how the book is segmented
into units*, orchestrates *who writes which digest*, then *mechanically embeds*
whatever digests come back.

So for every summary unit the digest must be written by **reading
`book-chapter-digest`'s `SKILL.md` and following it verbatim**. Do **not**
restate, paraphrase, or re-invent its template here. If that skill's format
changes later, this skill must pick up the change automatically — which only
works by delegating instead of duplicating. (Locate it at
`~/.claude/skills/book-chapter-digest/`; if it's moved, find it by name.) In
orchestrated mode this means **each worker subagent** reads that SKILL.md itself.

This skill is **EPUB-only** (injection needs the zip/XHTML structure). For other
formats, tell the user it only embeds into `.epub`.

## Workflow

Steps 1–4 are done by **you, the orchestrator** — they are the judgment calls
that must be made once for the whole book and never fanned out. Step 5 is where
the skill forks into the linear path (small book) or the orchestrated path (large
book). Steps 6–8 are mechanical and identical for both.

### 1. Build the index (reuse book-chapter-digest's parser)

Run the existing parser on the book at the path the user gave — it also records
each chapter's in-book location (`epub_file`, `epub_anchor`), which the injection
step needs:

```bash
~/.claude/skills/.venv/bin/python ~/.claude/skills/book-chapter-digest/scripts/build_index.py \
    "<book>" --cache-dir "<work>"
```

Sanity-check the chapter table exactly as `book-chapter-digest` instructs
(front/back matter, tiny divider rows, huge undivided blobs). The index is a
first pass, not ground truth.

### 2. Analyze structure and draft a segmentation plan

```bash
~/.claude/skills/.venv/bin/python ~/.claude/skills/epub-digest-embed/scripts/plan_helper.py \
    --epub "<book>" --cache-dir "<work>"
```

This writes `structure.json` (per chapter: word count + internal headings with
anchors) and `plan_draft.json` (a conservative 1:1 draft), and prints a report.

### 3. Decide the real segmentation — YOUR judgment, per book

This is the decision the old skill left to the human. Now you make it. **Counts
are signals, not verdicts — open the actual text when anything looks off.** Every
book is different; never trust the script blindly. **This decision is never
delegated to a worker — it must be single and consistent across the whole book.**

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

Edit `<work>/plan_draft.json` into the final `<work>/plan.json`. Each unit needs:
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

### 5. Generate the digests

Pick the path by the **scale of the book**, using the counts already in
`structure.json` — no new tooling needed:

- **Small book → linear path (5·L).** If the plan has **roughly ≤12 units** *and*
  the total body is **roughly ≤40k words**, just write the digests yourself,
  one unit after another. Orchestration would only add overhead.
- **Large book → orchestrated path (5·O).** Otherwise, fan out. One agent can't
  hold the whole book, so distribute the reading.

Both paths still obey the one rule: every digest is written **per
book-chapter-digest's SKILL.md**, from the unit's real extracted text only.

#### 5·L. Linear path (small book)

For each unit, extract its real text and write the digest **per
book-chapter-digest's SKILL.md**:

```bash
# whole chapter:
~/.claude/skills/.venv/bin/python ~/.claude/skills/book-chapter-digest/scripts/extract_chapter.py "<work>" <n>
# a subsection unit: extract the chapter, then use only the section spanning its section_ids
```

Read the extracted text in full, then write the digest from that text only
(grounding rules are that skill's, not yours). Put each unit's finished Markdown
into its `"md"` field in `plan.json`. Then skip to step 6.

#### 5·O. Orchestrated path (large book)

The design in one line: **the heavy thing (full chapter text) is distributed and
thrown away per worker; the light thing (finished digests) is gathered back for
reconciliation.** You, the orchestrator, keep only structure and the compact
digests in context — never the raw book text.

**5·O.a — Write a short book brief (keeps workers out of a vacuum).**
Read *only* the framing sections — the Introduction / Preface and the
Conclusion / Epilogue (extract them with `extract_chapter.py`) — plus the chapter
titles from the index. From those, write a compact brief (a few sentences):
what the book is about, its central model/thesis, and the target language and
tone. **Default the language to the book's own language** — detect it from the
extracted framing text (a Russian book → Russian digests, an English book →
English) — unless the user explicitly asked for another; pass this decision to
every worker so the whole book comes out in one language. **Decide this silently
— never ask the user which language to use.** The user's chat language is
irrelevant to the digest language: a Russian-speaking user embedding digests into
an English book still gets **English** digests by default. Deviate only if the
user, unprompted, already named a specific digest language.

This is cheap in context and is what stops each worker from summarizing its
chapters blind. Do **not** read every chapter here — that would defeat the point.

**5·O.b — Cut the units into batches, along the book's own seams.**
A batch is a run of **adjacent units**, split on the book's natural boundaries
(**Part / section dividers first**), capped so a batch stays readable in one
worker — about **5–8 units or ~40k words**, whichever comes first. Never split a
Part across two batches unless it alone exceeds the cap. A batch being a real
thematic block is a feature: the worker sees those chapters together, so
within-batch verdicts like "повторяет предыдущую главу" come for free.

**5·O.c — Dispatch one worker subagent per batch (in parallel).**
Give each worker, in its prompt:
- the book brief from 5·O.a;
- its batch: for every unit — `id`, `kind`, `label`, `source_chapters`, and for
  subsection units the `section_ids`;
- the absolute cache dir path (`<work>`) and the instruction to **read
  `~/.claude/skills/book-chapter-digest/SKILL.md` and follow it verbatim**, and
  to extract each unit's real text with
  `~/.claude/skills/.venv/bin/python ~/.claude/skills/book-chapter-digest/scripts/extract_chapter.py`
  (whole chapter, or
  only the span of its `section_ids` for a subsection unit) and write the digest
  **from that text only** — the grounding rules are that skill's;
- the required return shape: for each unit
  `{ "id", "md", "gist_one_line", "introduced_terms": [ ... ] }`, where
  `introduced_terms` are the book's own coinages this unit first defines (e.g.
  "Workview", "gravity problem"). `gist_one_line` is the unit's one-sentence суть.

The full chapter text lives and dies inside the worker; only these compact
objects come back. Workers are independent — none reads another's chapters.

**5·O.d — Gather and aggregate (orchestrator, light context).**
Collect all workers' returns. Build two compact artifacts:
- a **glossary** — merge every `introduced_terms` into one list, each term mapped
  to the unit that first defines it (emergent, bottom-up — you did not have to
  guess it up front);
- a **gist map** — the ordered list of every unit's `gist_one_line`.

**5·O.e — Reconcile with a single reviser subagent.**
Hand the reviser: all the units' `md`, the glossary, the gist map, and the brief.
Its job is **coherence only, not new content** — it never had the raw text and
must not invent any:
- **De-duplicate definitions** — a term is defined in full only where the glossary
  says it first appears; later units keep a short reference ("см. Гл. N") instead
  of re-explaining it.
- **Level the tone, depth, and verdict style** across all units.
- **Add cross-references** ("развивает идею Гл. 3", "повторяет Гл. 7") using the
  gist map.
- **Catch contradictions** between units and flag or gently resolve them.
- **Preserve grounding:** the reviser edits for connective tissue, trims
  duplication, and inserts references — it must **not** add facts, claims, or
  specifics that a worker didn't write. When unsure, leave the worker's text as-is.

It returns the final `md` per unit plus a short changelog of what it adjusted.

**5·O.f — Land the results.**
Put each unit's final `md` into its `"md"` field in `plan.json`. Continue to
step 6.

### 6. Inject and patch the TOC

```bash
~/.claude/skills/.venv/bin/python ~/.claude/skills/epub-digest-embed/scripts/inject_digest.py \
    --epub "<book>" \
    --plan "<work>/plan.json" \
    --cache-dir "<work>" \
    --md-out "<book-dir>/<book-stem> — конспект.md" \
    --out "<book-dir>/<book-stem> (с конспектом).epub"
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
~/.claude/skills/.venv/bin/python ~/.claude/skills/epub-digest-embed/scripts/verify_epub.py \
    --epub "<book-dir>/<book-stem> (с конспектом).epub" \
    --plan "<work>/plan.json" --cache-dir "<work>"
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
— that's wasteful; spot-check. In orchestrated mode, bias the spot-check toward a
batch boundary — that's where cross-references and de-duplication were applied.)

### 8. Deliver

Print the absolute paths of **both** outputs in your final answer — the epub
first, then the Markdown digest. Never overwrite the original book file.

## Orchestration invariants (do not violate)

- **The orchestrator never holds the full book text.** It reads only structure,
  the two framing sections (for the brief), and the compact digests coming back.
  If you find yourself extracting every chapter in the coordinator, you're doing
  it wrong — that's the worker's job.
- **Segmentation (step 3) and the user go-ahead (step 4) are single and central.**
  They are never fanned out to workers.
- **Workers are grounded and independent.** Each writes only from the real text
  of its own units, per `book-chapter-digest`. No worker reads another's
  chapters; the brief is their only shared context on input.
- **The reviser adds coherence, not content.** It has no raw text and must not
  invent facts. Reconciliation = de-dup, tone-leveling, cross-refs — nothing that
  changes what a chapter is claimed to say.
- **Use the linear mode when small.** Below the threshold, orchestration is pure
  overhead — use path 5·L.

## Scripts

All scripts live in `~/.claude/skills/epub-digest-embed/scripts/` and run with
`~/.claude/skills/.venv/bin/python`.

- `scripts/plan_helper.py` — structure report + conservative draft plan
  (protects intro-type and substantial sections from being skipped).
- `scripts/inject_digest.py` — md→XHTML, front doc, inline callouts, NCX/nav
  patching, valid rezip, **and** the standalone Markdown digest (`--md-out`).
  Consumes `plan.json` (with `md` filled in).
- `scripts/verify_epub.py` — mandatory post-build check; non-zero exit on any
  problem so you know to rebuild.
- Reused from `~/.claude/skills/book-chapter-digest/scripts/`: `build_index.py` (emits
  `epub_file`/`epub_anchor`) and `extract_chapter.py`.

## Notes on robustness

EPUBs vary wildly. The injector targets the common, spec-compliant cases (NCX
and/or EPUB3 nav, XHTML content). If the nav can't be patched, NCX still covers
most readers and the script warns rather than failing. If `build_index.py`
can't split the book (DRM, scanned PDF-in-epub, one giant blob), stop and tell
the user — don't fabricate structure.

In orchestrated mode, if a worker subagent fails or returns an unusable unit,
re-dispatch just that batch (or write those units yourself via the linear path) —
never ship a unit with an empty or fabricated digest. A partial fleet is fine;
a fabricated chapter is not.
