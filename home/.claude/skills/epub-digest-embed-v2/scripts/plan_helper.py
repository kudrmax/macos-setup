#!/usr/bin/env python3
"""
plan_helper.py — Inspect an EPUB's real structure and draft a *conservative*
segmentation plan for embedding chapter digests.

This is the mechanical first pass for the hard judgment the embed skill has to
make on its own: the old book-chapter-digest skill let the human pick the unit
("summarize this chapter", "the part about X", "chapters 4-6"). When we process
a whole book automatically, Claude must pick the units. This script surfaces the
signals (chapter sizes, internal heading structure with anchors) and proposes a
safe default plan. Claude is expected to OPEN THE ACTUAL TEXT and adjust — the
draft is a starting point, never ground truth. Every book is different.

Inputs:
    --epub PATH         the .epub
    --cache-dir DIR     book-chapter-digest cache (must contain index.json with
                        epub_file/epub_anchor — i.e. produced by the patched
                        build_index.py)

Outputs (written into --cache-dir):
    structure.json      per content-chapter: words + internal headings(id,level,
                        title, approx words) — the raw material for planning.
    plan_draft.json     conservative draft plan (1:1 by default). Claude edits
                        this into the final plan.json after review + user OK.

Also prints a human-readable report to stdout.

The draft policy is intentionally CONSERVATIVE:
  * normal chapters            -> 1 unit each (1:1)
  * a really huge chapter      -> split into subsection units, but only when it
    (>= ~2.5x the book median  has clean internal headings with anchors; nearby
     AND >= 9000 words)        small sections are merged so each unit is sane.
  * a swarm of tiny chapters   -> group adjacent ones into units of ~median size.
    (many < ~0.4x median)
Front/back matter is excluded from units (but still listed in the report).
"""

import sys, os, re, json, argparse, zipfile, statistics
from html.parser import HTMLParser

HEAD_RE = re.compile(r"<h([1-6])\b([^>]*)>(.*?)</h\1>", re.I | re.S)
ID_RE = re.compile(r'\bid\s*=\s*["\']([^"\']+)["\']', re.I)
TAG_RE = re.compile(r"<[^>]+>")


def strip_tags(s):
    return re.sub(r"\s+", " ", TAG_RE.sub(" ", s)).strip()


def words(s):
    return len(s.split())


# Titles that are ALWAYS content even if a matter-detector flags them: an
# Introduction / Preface / Foreword / Prologue / Conclusion usually carries the
# book's core framing, not throwaway front-matter.
CONTENT_TITLE_RE = re.compile(
    r"\b(introduction|preface|foreword|prologue|epilogue|conclusion|afterword|"
    r"введени|предислови|вступлени|пролог|эпилог|заключени|послеслови)",
    re.I,
)


def effective_matter(entry):
    """Decide whether to SKIP an entry. Conservative: never skip intro-type
    sections, and never skip a 'matter'-flagged section that is substantial
    (it probably carries real content the detector mislabelled)."""
    if CONTENT_TITLE_RE.search(entry.get("title") or ""):
        return False
    if not entry.get("matter"):
        return False
    # flagged as matter — only skip if it's genuinely small/service-sized
    if entry.get("words", 0) >= 1500:
        return False  # too big to be a mere service page; keep + let Claude judge
    return True


def read_zip_text(z, name):
    try:
        return z.read(name).decode("utf-8", errors="replace")
    except KeyError:
        return ""


def chapter_html_span(z, ch, all_chapters):
    """Return the HTML substring belonging to this chapter inside its epub_file.

    For one-chapter-per-file books this is the whole file. When several chapters
    share a file (split by anchors), the span runs from this chapter's anchor to
    the next chapter's anchor in the same file.
    """
    f = ch.get("epub_file")
    if not f:
        return ""
    html = read_zip_text(z, f)
    if not html:
        return ""
    anchor = ch.get("epub_anchor")
    start = 0
    if anchor:
        m = re.search(r'<[^>]*\bid\s*=\s*["\']' + re.escape(anchor) + r'["\']', html, re.I)
        if m:
            start = m.start()
    # find next chapter that lives in the same file with an anchor after `start`
    end = len(html)
    nexts = []
    for other in all_chapters:
        if other is ch:
            continue
        if other.get("epub_file") == f and other.get("epub_anchor"):
            m2 = re.search(r'<[^>]*\bid\s*=\s*["\']' + re.escape(other["epub_anchor"]) + r'["\']', html, re.I)
            if m2 and m2.start() > start:
                nexts.append(m2.start())
    if nexts:
        end = min(nexts)
    return html[start:end]


def internal_sections(span_html):
    """List internal headings with anchors inside a chapter span.
    Returns [{level, id, title, words_after}] in document order; words_after is
    the approx word count of the text from this heading to the next heading."""
    heads = []
    for m in HEAD_RE.finditer(span_html):
        level = int(m.group(1))
        attrs = m.group(2)
        idm = ID_RE.search(attrs)
        title = strip_tags(m.group(3))
        heads.append({"level": level, "id": idm.group(1) if idm else None,
                      "title": title, "_pos": m.start(), "_end": m.end()})
    for i, h in enumerate(heads):
        nxt = heads[i + 1]["_pos"] if i + 1 < len(heads) else len(span_html)
        h["words_after"] = words(strip_tags(span_html[h["_end"]:nxt]))
    for h in heads:
        h.pop("_pos", None); h.pop("_end", None)
    return heads


def build_structure(epub, index):
    z = zipfile.ZipFile(epub)
    chapters = index["chapters"]
    out = []
    for ch in chapters:
        entry = {
            "n": ch["n"], "title": ch["title"], "words": ch["words"],
            "matter": ch.get("matter", False),
            "epub_file": ch.get("epub_file"), "epub_anchor": ch.get("epub_anchor"),
            "sections": [],
        }
        entry["skip"] = effective_matter(entry)
        if not entry["skip"] and ch.get("epub_file"):
            span = chapter_html_span(z, ch, chapters)
            secs = internal_sections(span)
            # keep only headings that have a usable anchor and aren't the chapter
            # title itself (the first heading); these are candidate split points
            usable = [s for s in secs if s["id"]]
            entry["sections"] = usable
        out.append(entry)
    return out


def propose_plan(structure, index):
    content = [s for s in structure if not s["skip"]]
    if not content:
        return {"book": index.get("book"), "units": [], "note": "no content chapters detected"}

    sizes = [c["words"] for c in content]
    median = statistics.median(sizes) if sizes else 0
    HUGE = max(2.5 * median, 9000)
    TINY = min(0.4 * median, 600)
    target = median if median else 2500

    units = []
    uid = 0

    def new_uid():
        nonlocal uid
        uid += 1
        return f"u{uid:02d}"

    i = 0
    while i < len(content):
        c = content[i]

        # --- swarm of tiny chapters -> group adjacent tiny ones ---
        if c["words"] < TINY:
            grp = [c]
            j = i + 1
            acc = c["words"]
            while j < len(content) and content[j]["words"] < TINY and acc + content[j]["words"] <= target * 1.3:
                acc += content[j]["words"]
                grp.append(content[j])
                j += 1
            if len(grp) > 1:
                units.append({
                    "id": new_uid(), "kind": "group",
                    "label": f'{grp[0]["title"]} … {grp[-1]["title"]}',
                    "source_chapters": [g["n"] for g in grp],
                    "inject_file": grp[0]["epub_file"], "inject_anchor": grp[0]["epub_anchor"],
                    "words": acc,
                })
                i = j
                continue
            # single tiny chapter, no neighbours to group -> 1:1
            units.append(_unit_chapter(new_uid(), c))
            i += 1
            continue

        # --- really huge chapter with clean internal sections -> split ---
        if c["words"] >= HUGE and len(c["sections"]) >= 3:
            # group internal sections into chunks of ~target words
            chunks = _chunk_sections(c["sections"], target)
            if len(chunks) >= 2:
                for ch_secs in chunks:
                    first = ch_secs[0]
                    units.append({
                        "id": new_uid(), "kind": "subsection",
                        "label": f'{c["title"]} — {first["title"]}',
                        "source_chapters": [c["n"]],
                        "section_ids": [s["id"] for s in ch_secs],
                        "inject_file": c["epub_file"], "inject_anchor": first["id"],
                        "words": sum(s["words_after"] for s in ch_secs),
                    })
                i += 1
                continue

        # --- normal chapter -> 1:1 ---
        units.append(_unit_chapter(new_uid(), c))
        i += 1

    return {
        "book": index.get("book"),
        "median_words": median, "huge_threshold": HUGE, "tiny_threshold": TINY,
        "placement": "both", "toc": "both",
        "units": units,
    }


def _unit_chapter(uid, c):
    return {
        "id": uid, "kind": "chapter", "label": c["title"],
        "source_chapters": [c["n"]],
        "inject_file": c["epub_file"], "inject_anchor": c["epub_anchor"],
        "words": c["words"],
    }


def _chunk_sections(sections, target):
    chunks, cur, acc = [], [], 0
    for s in sections:
        cur.append(s); acc += s["words_after"]
        if acc >= target:
            chunks.append(cur); cur, acc = [], 0
    if cur:
        if chunks and acc < target * 0.4:
            chunks[-1].extend(cur)
        else:
            chunks.append(cur)
    return chunks


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--epub", required=True)
    ap.add_argument("--cache-dir", required=True)
    args = ap.parse_args()

    index = json.load(open(os.path.join(args.cache_dir, "index.json"), encoding="utf-8"))
    structure = build_structure(args.epub, index)
    plan = propose_plan(structure, index)

    json.dump(structure, open(os.path.join(args.cache_dir, "structure.json"), "w", encoding="utf-8"),
              ensure_ascii=False, indent=2)
    json.dump(plan, open(os.path.join(args.cache_dir, "plan_draft.json"), "w", encoding="utf-8"),
              ensure_ascii=False, indent=2)

    # report
    print(f"Книга: {index.get('book')}")
    print(f"Медиана главы: {plan.get('median_words')} сл · "
          f"огромная >= {int(plan.get('huge_threshold',0))} сл · "
          f"мелкая < {int(plan.get('tiny_threshold',0))} сл")
    print("-" * 70)
    for s in structure:
        tag = "  [служебное — пропуск]" if s["skip"] else ("  [matter? оставлено]" if s["matter"] else "")
        secn = f"  ·{len(s['sections'])} внутр.секций" if s["sections"] else ""
        print(f"{s['n']:>3}. {s['title'][:50]:50} {s['words']:>6} сл{secn}{tag}")
    print("-" * 70)
    print(f"ЧЕРНОВИК ПЛАНА — {len(plan['units'])} единиц(ы):")
    for u in plan["units"]:
        kind = {"chapter": "глава", "subsection": "подсекция", "group": "группа"}[u["kind"]]
        print(f"  [{u['id']}] {kind:9} ← гл.{u['source_chapters']}  «{u['label'][:55]}»")
    print("-" * 70)
    print("structure.json и plan_draft.json записаны в кэш.")
    print("ВАЖНО: это черновик. Открой реальный текст и поправь единицы по смыслу,")
    print("потом покажи план пользователю и только затем генерируй выжимки.")


if __name__ == "__main__":
    main()
