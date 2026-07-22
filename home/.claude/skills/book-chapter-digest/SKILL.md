---
name: book-chapter-digest
description: >-
  Read a real nonfiction / self-help book file (.epub first-class, also .fb2,
  .txt, best-effort .pdf) and produce grounded, skim-or-skip chapter digests so
  the user can decide what's worth reading in full. ALWAYS use this skill whenever
  the user uploads or points to a book file and asks to "summarize a chapter",
  "пересказать главу", "выжимка по главе", "стоит ли читать главу N", "что в этой
  главе", or asks for several chapters at once — even if phrased casually or out
  of order. Also use it for follow-ups about the same book (another chapter, a
  sub-section, "а что в части про X"). The defining feature: summaries are built
  strictly from the book's extracted text, never from the title or prior knowledge.
---

# Book Chapter Digest

Help the user triage a nonfiction/self-help book chapter by chapter: for each
requested chapter, deliver a tight, **grounded** digest that makes it obvious
whether to read it in full, skim parts of it, or skip it.

The single most important rule: **never summarize from memory, the title, or
general knowledge about the book. Always extract the real chapter text first and
write only from what the extraction returns.** If you can't extract it, say so.

## Workflow

### 1. First contact with a book — build the index (once per book)

The user sends books in **any** format and the structure is **often imperfect** —
a missing or useless table of contents, front/back matter mixed in with real
chapters, one giant undivided blob, or section-divider "chapters" with almost no
text. Treat `build_index.py` as a first pass, not ground truth. Find the file
under `/mnt/user-data/uploads/`.

```bash
python scripts/build_index.py "<path-to-book>"
```

This parses the book's own structure (EPUB spine + TOC, FB2 sections, PDF
outline, or TXT headings), writes each chapter's verbatim text to a cache
directory (`<book>.digest/`), prints the chapter table, and emits STRUCTURE
SIGNALS when something looks off. Keep the cache path — every later request
reuses it.

If `build_index.py` errors (DRM, scanned/image-only PDF, unsupported format),
say so plainly and stop — never fabricate a summary.

### 1.5. Sanity-check the index before trusting it

Look at the table with judgment — don't assume the rows are clean chapters:

- **Front/back matter** (flagged `служебный?` — Copyright, Dedication, Contents,
  Acknowledgments, Notes, Index…) is not a chapter. When showing the user the
  list, separate real chapters from matter, or at least say which rows are skippable.
- **Tiny rows** (a handful of words) are usually the TOC itself, part dividers, or
  blank pages — not content. Don't digest them as if they were chapters.
- **One huge blob / "not split into chapters" signal** → the book lacks usable
  structure. Don't force it. Tell the user, then offer an alternative: extract the
  whole thing and split by detectable headings, or summarize by logical sections,
  or ask how they'd like it divided.
- **Suspicious titles** (generic "Section 1", duplicated, or mismatched) → extract
  and glance at the text before trusting the title.

The rule of thumb: when the structure looks even slightly off, **open the actual
text and look** rather than trusting the index. The index is a convenience, not
an authority.

### 2. Each digest request — extract, then summarize

Whatever the user asks for (one chapter, several, a range, by title), resolve it
to chapter numbers and extract the real text:

```bash
python scripts/extract_chapter.py "<cache-dir>" 5          # one chapter
python scripts/extract_chapter.py "<cache-dir>" 5-7        # range
python scripts/extract_chapter.py "<cache-dir>" 2,5,9      # specific list
python scripts/extract_chapter.py "<cache-dir>" --title "habits"
python scripts/extract_chapter.py "<cache-dir>" --list     # show chapters again
```

Read the printed text in full, then write the digest **from that text only**.
Then produce the digest(s) using the template below.

### 3. Handle a non-linear, inconsistent user

The user jumps around and that's expected. Support it smoothly:

- **Multiple chapters at once** — extract them in one call, one digest block each,
  with a one-line overview at the top.
- **Out-of-order / follow-up requests** ("теперь 2 и 3", "а ещё последнюю") — the
  index is cached, so just extract and digest. Never ask them to re-upload.
- **Sub-chapter / "the part about X"** — extract the whole chapter, locate the
  relevant section inside the extracted text, and digest just that part. Quote the
  surrounding sentence so they can find it.
- **"Should I read chapter N?"** — answer with the verdict line first, then the
  short digest as justification.
- **Vague reference** ("ту главу про дисциплину") — use `--title` or scan the
  index titles; if genuinely ambiguous, show the candidate chapters and ask which.

## Output format (defaults to the book's own language)

Write digests in **the same language as the book** by default — detect it from
the extracted chapter text, not from the title. A Russian book → Russian
digests; an English book → English digests; a German book → German. Only switch
languages if the user explicitly asks for another (then honor that request over
the book's language). The template below is shown with Russian labels as an
example — render those labels («Суть одной фразой», «Ключевые тезисы», «Что
можно применить», «Вердикт») in the digest's language too, so an English digest
uses English headings and an English verdict line. Use this exact template per
chapter.

```
## Глава N — «Точное название из книги»
~W слов · ~M мин чтения

📌 **Суть одной фразой:** <одно предложение — главное утверждение главы>

**Ключевые тезисы:**
1. <тезис, который ПЕРЕДАЁТ идею, а не называет её — см. правило ниже>
2. <тезис>
3. <тезис>
(3–5 пунктов; только то, что реально есть в тексте)

**Что можно применить:** <конкретные техники/шаги, если они есть в главе; иначе «—»>
- <шаг/приём>

**Вердикт:** 🟢 читать целиком / 🟡 читать выборочно / 🔴 можно листать
<1–2 предложения: где в главе мясо, а где вода. Указывай ориентир —
например: «первые ~40% — личная история автора; суть начинается с раздела
про …; концовка повторяет уже сказанное».>
```

For multiple chapters, prepend a one-line map, e.g.:
`Главы 4–6: 4 — стоит, 5 — можно листать, 6 — выборочно. Подробнее ниже.`

### Writing rule: theses must CARRY the idea, not name it

This is the part that's easy to get wrong. The point of the digest is that after
reading it, the user actually understands the chapter's content — enough to skip
the chapter if they want. A thesis that merely labels a concept ("there's an HWPL
dashboard, rate four scales, look for red lights") fails: it transmits zero
substance. Each thesis must be **self-contained** — explain the idea, define the
book's own terms inline, and say what follows from it. Length is whatever the idea
needs (usually 2–4 sentences), not one stripped clause. Don't compress to the
point of emptiness; density of *information*, not brevity, is the goal.

A reader's test: could someone who never opens the chapter explain this idea back
correctly from your thesis alone? If not, it's a label, not a thesis.

**Bad (names the idea — useless):**
> Чтобы понять «где ты», есть дашборд Health / Work / Play / Love: оценить четыре
> шкалы. Идеального баланса нет — ищешь красные лампочки.

**Good (carries the idea — you actually learn it):**
> Чтобы понять «где ты», заполни дашборд Health / Work / Play / Love. Авторы
> намеренно расширяют термины: Health — тело + ум + дух (необязательно
> религиозный); Work — любой вклад, оплачиваемый или нет (воспитание детей —
> тоже работа), а не только «должность»; Play — то, что делаешь ради чистой
> радости процесса, а не ради победы/достижения; Love — связь, текущая в обе
> стороны. Каждую сферу оцениваешь от 0 до «полной». Смысл не в равном балансе
> (его нет и не нужно), а в том, чтобы поймать «красную лампочку» — сферу,
> просевшую опасно низко. Пока честно не определишь, где ты, нельзя выбрать,
> что чинить первым.

Same rule applies to the «суть», «что применить», and «вердикт»: name a specific,
then say enough that it's understood. When the book introduces its own term
(gravity problem, Workview, reframe, …), define it in the digest — never assume
the reader knows it.

### Writing rule: let structure mirror the content

Don't default to flat prose, and don't force everything into lists either —
**match the shape of the formatting to the shape of the idea.** When a thesis
contains a set of parallel items — definitions of several terms, a list of
categories, ordered steps — break them out as a nested list so they're scannable,
instead of cramming them into one semicolon-spliced sentence. When two things are
being compared, a small table can beat prose. Use **bold** for the book's key
terms so the eye catches them. Plain prose is right for a single flowing argument;
a list is right for enumerable parts. The test: if you're separating items with
";" or "1)… 2)… 3)…" inside a sentence, that's usually a list trying to get out.

Example — the HWPL thesis reads far better with the four areas as a nested list:

> 4. **Чтобы понять «где ты», заполни дашборд Health / Work / Play / Love.**
>    Авторы намеренно расширяют термины:
>    - **Health** — тело + ум + дух (необязательно религиозный).
>    - **Work** — любой вклад, оплачиваемый или нет (воспитание детей — тоже
>      работа), а не только «должность».
>    - **Play** — то, что делаешь ради чистой радости процесса, а не ради
>      победы/достижения.
>    - **Love** — связь, текущая в обе стороны.
>
>    Каждую сферу оцениваешь от 0 до «полной». Смысл не в равном балансе (его нет
>    и не нужно), а в том, чтобы поймать «красную лампочку» — сферу, просевшую
>    опасно низко.

If the user explicitly asks «короче», then and only then compress to суть +
тезисы-в-одну-строку + вердикт. Default is substantive.

## Grounding rules (do not violate)

- **Read before you write.** Run `extract_chapter.py` and read its output before
  composing any digest. No extraction → no digest.
- **Every specific comes from the text.** Names, claims, steps, and any quoted
  phrase must come from the extracted text, not from memory. When you do quote a
  phrase to locate something, copy it exactly and keep it short. Don't add a
  standing "quotes" section — it's not part of the template.
- **The "water" verdict must come from the text**, not assumptions about the genre.
  Base «где вода» on what the extracted paragraphs actually contain (long
  anecdotes, repetition, filler) vs. dense claims.
- **If the extraction is thin, garbled, or empty, say so.** Report it honestly
  ("эта глава извлеклась плохо / почти пустая — возможно, это разделитель или
  изображение") instead of guessing the content.
- **Titles can mislead.** A chapter called "Discipline" might be all biography.
  Trust the extracted text over the title every time.

## Format support

| Format | Reliability | Notes |
|--------|-------------|-------|
| `.epub` | First-class | Splits by TOC (NCX or nav), handles multiple chapters per file via anchors. |
| `.fb2`  | Good | Splits by `<section>` + `<title>`. |
| `.txt`  | Best-effort | Splits on heading lines (Глава/Chapter/Часть/…). |
| `.pdf`  | Best-effort | Uses bookmarks/outline if present; else heading detection. Needs `pypdf` (`pip install pypdf --break-system-packages`). Scanned/image PDFs won't work without OCR. |

If a book is `.mobi`/`.azw3`, ask the user to convert it to EPUB (e.g. Calibre),
which is the most reliable path.

## Scripts

- `scripts/build_index.py <book> [--cache-dir DIR]` — parse the book, cache real
  chapter text, print the chapter table. Run once per book.
- `scripts/extract_chapter.py <cache-dir> <selectors...> [--title S] [--list]` —
  print the verbatim text of selected chapters. Run before every digest.
