#!/usr/bin/env python3
"""
build_index.py — Build a chapter map of a book and cache each chapter's REAL text.

This is the anti-hallucination foundation of the skill: it parses the actual book
file, splits it into chapters according to the book's own structure (EPUB spine +
TOC, FB2 sections, PDF outline, or TXT headings), and writes the verbatim text of
every chapter to disk. The summarizer then reads only from these cached files.

Usage:
    ~/.claude/skills/.venv/bin/python build_index.py <book_file> [--cache-dir DIR]

Output:
    Creates <cache-dir>/index.json and <cache-dir>/chap_001.txt, chap_002.txt, ...
    Prints a human-readable chapter table to stdout.

Reliable for: .epub (first-class), .fb2, .txt.
Best-effort for: .pdf (needs an outline/bookmarks or detectable headings).

Stdlib only for EPUB/FB2/TXT. PDF uses pypdf if available.
"""

import sys
import os
import re
import json
import zipfile
import argparse
import xml.etree.ElementTree as ET
from html.parser import HTMLParser


# ---------------------------------------------------------------------------
# HTML -> text, while recording character offset of every element id/anchor.
# ---------------------------------------------------------------------------

BLOCK_TAGS = {
    "p", "div", "br", "li", "tr", "section", "article", "blockquote",
    "h1", "h2", "h3", "h4", "h5", "h6", "header", "footer", "table",
}
SKIP_TAGS = {"script", "style", "head", "title"}


# Sentinel markers carry anchor ids THROUGH whitespace normalization so the
# recorded offsets stay valid against the final cleaned text (no drift).
_ID_OPEN = "\x00ID:"
_ID_CLOSE = "\x00"
_ID_RE = re.compile(r"\x00ID:(.*?)\x00")


class HTMLTextExtractor(HTMLParser):
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.parts = []
        self.ids = {}            # id/name -> char offset (filled in get_text)
        self._seen_ids = set()
        self._skip_depth = 0

    def handle_starttag(self, tag, attrs):
        d = dict(attrs)
        for key in ("id", "name"):
            val = d.get(key)
            if val and val not in self._seen_ids:
                self._seen_ids.add(val)
                self.parts.append(f"{_ID_OPEN}{val}{_ID_CLOSE}")
        if tag in SKIP_TAGS:
            self._skip_depth += 1
        if tag in BLOCK_TAGS:
            self.parts.append("\n")

    def handle_endtag(self, tag):
        if tag in SKIP_TAGS and self._skip_depth > 0:
            self._skip_depth -= 1
        if tag in {"p", "div", "li", "h1", "h2", "h3", "h4", "h5", "h6",
                   "blockquote", "section"}:
            self.parts.append("\n")

    def handle_data(self, data):
        if self._skip_depth == 0:
            self.parts.append(data)

    def get_text(self):
        text = "".join(self.parts)
        # normalize whitespace (sentinels contain no spaces/newlines -> survive)
        text = re.sub(r"[ \t]+", " ", text)
        text = re.sub(r"\n[ \t]+", "\n", text)
        text = re.sub(r"\n{3,}", "\n\n", text)
        # now strip sentinels and record their positions in the CLEANED text
        out = []
        pos = 0
        last = 0
        for m in _ID_RE.finditer(text):
            out.append(text[last:m.start()])
            pos += m.start() - last
            if m.group(1) not in self.ids:
                self.ids[m.group(1)] = pos
            last = m.end()
        out.append(text[last:])
        clean = "".join(out)
        # leading-edge cleanup without shifting recorded offsets mid-text:
        # only strip trailing whitespace (leading kept so offsets stay valid)
        return clean.rstrip()


def html_to_text_and_ids(html_bytes):
    try:
        html = html_bytes.decode("utf-8")
    except UnicodeDecodeError:
        html = html_bytes.decode("utf-8", errors="replace")
    p = HTMLTextExtractor()
    try:
        p.feed(html)
    except Exception:
        pass
    return p.get_text(), p.ids


# ---------------------------------------------------------------------------
# Tiny HTML link extractor for EPUB3 nav documents (the TOC <nav>).
# ---------------------------------------------------------------------------

class NavLinkExtractor(HTMLParser):
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.in_toc_nav = False
        self.nav_depth = 0
        self.cur_href = None
        self.cur_text = []
        self.links = []          # (title, href)

    def handle_starttag(self, tag, attrs):
        d = dict(attrs)
        if tag == "nav":
            self.nav_depth += 1
            etype = d.get("epub:type") or d.get("type") or d.get("role") or ""
            if "toc" in etype.lower() or d.get("id", "").lower() in ("toc", "nav-toc"):
                self.in_toc_nav = True
        if self.in_toc_nav and tag == "a" and d.get("href"):
            self.cur_href = d["href"]
            self.cur_text = []

    def handle_endtag(self, tag):
        if tag == "a" and self.cur_href is not None:
            title = " ".join("".join(self.cur_text).split()).strip()
            self.links.append((title, self.cur_href))
            self.cur_href = None
            self.cur_text = []
        if tag == "nav" and self.nav_depth > 0:
            self.nav_depth -= 1
            if self.nav_depth == 0:
                self.in_toc_nav = False

    def handle_data(self, data):
        if self.cur_href is not None:
            self.cur_text.append(data)


# ---------------------------------------------------------------------------
# EPUB parsing
# ---------------------------------------------------------------------------

def _local(tag):
    return tag.split("}")[-1].lower()


def parse_epub(path):
    """Return ordered list of chapters: [{title, text}]."""
    with zipfile.ZipFile(path) as z:
        names = z.namelist()

        # 1. container.xml -> opf path
        opf_path = None
        if "META-INF/container.xml" in names:
            root = ET.fromstring(z.read("META-INF/container.xml"))
            for el in root.iter():
                if _local(el.tag) == "rootfile" and el.get("full-path"):
                    opf_path = el.get("full-path")
                    break
        if not opf_path:
            opf_path = next((n for n in names if n.lower().endswith(".opf")), None)
        if not opf_path:
            raise ValueError("EPUB: cannot locate OPF package file")

        opf_dir = os.path.dirname(opf_path)

        def resolve(href):
            href = href.split("#")[0]
            p = os.path.normpath(os.path.join(opf_dir, href)).replace("\\", "/")
            return p

        # 2. parse OPF: manifest + spine
        opf = ET.fromstring(z.read(opf_path))
        manifest = {}   # id -> {href, media, props}
        spine = []      # ordered list of idrefs
        toc_id = None
        for el in opf.iter():
            t = _local(el.tag)
            if t == "item":
                manifest[el.get("id")] = {
                    "href": el.get("href"),
                    "media": (el.get("media-type") or "").lower(),
                    "props": (el.get("properties") or "").lower(),
                }
            elif t == "spine":
                toc_id = el.get("toc")  # ncx id (EPUB2)
            elif t == "itemref":
                if el.get("idref"):
                    spine.append(el.get("idref"))

        # ordered spine files
        spine_files = []
        for idref in spine:
            item = manifest.get(idref)
            if item and item["href"]:
                spine_files.append(resolve(item["href"]))

        # 3. Build a global concatenated text + per-file global offsets + ids
        full_text_parts = []
        global_len = 0
        file_global_start = {}   # file path -> global start offset
        file_ids = {}            # file path -> {anchor: local offset}
        SEP = "\n\n"
        for f in spine_files:
            if f not in names:
                continue
            text, ids = html_to_text_and_ids(z.read(f))
            file_global_start[f] = global_len
            file_ids[f] = ids
            full_text_parts.append(text)
            global_len += len(text)
            full_text_parts.append(SEP)
            global_len += len(SEP)
        full_text = "".join(full_text_parts)

        # 4. Find TOC entries -> (title, file, anchor)
        toc_entries = []  # (title, href_file, anchor_or_None)

        # 4a. NCX (EPUB2 / back-compat)
        ncx_name = None
        if toc_id and toc_id in manifest:
            ncx_name = resolve(manifest[toc_id]["href"])
        if not ncx_name:
            ncx_name = next(
                (resolve(v["href"]) for v in manifest.values()
                 if v["media"] == "application/x-dtbncx+xml"),
                None,
            )
        if ncx_name and ncx_name in names:
            ncx = ET.fromstring(z.read(ncx_name))
            navpoints = [el for el in ncx.iter() if _local(el.tag) == "navpoint"]
            for np in navpoints:
                label = ""
                src = ""
                for c in np.iter():
                    lc = _local(c.tag)
                    if lc == "text" and not label:
                        label = (c.text or "").strip()
                    if lc == "content" and c.get("src"):
                        src = c.get("src")
                        break
                if src:
                    file_part = resolve(src)
                    anchor = src.split("#")[1] if "#" in src else None
                    toc_entries.append((label, file_part, anchor))

        # 4b. EPUB3 nav document, if NCX gave nothing
        if not toc_entries:
            nav_item = next(
                (v for v in manifest.values() if "nav" in v["props"]),
                None,
            )
            if nav_item:
                nav_file = resolve(nav_item["href"])
                if nav_file in names:
                    nav_dir = os.path.dirname(nav_file)
                    nx = NavLinkExtractor()
                    nx.feed(z.read(nav_file).decode("utf-8", errors="replace"))
                    for title, href in nx.links:
                        fp = os.path.normpath(
                            os.path.join(nav_dir, href.split("#")[0])
                        ).replace("\\", "/")
                        anchor = href.split("#")[1] if "#" in href else None
                        toc_entries.append((title, fp, anchor))

        # 5. Convert TOC entries to global offsets
        marks = []  # (global_offset, title, file, anchor)
        for title, fpart, anchor in toc_entries:
            if fpart not in file_global_start:
                continue
            base = file_global_start[fpart]
            off = 0
            if anchor and anchor in file_ids.get(fpart, {}):
                off = file_ids[fpart][anchor]
            marks.append((base + off, title or "Без названия", fpart, anchor))

        # dedupe + sort by position
        seen = set()
        uniq = []
        for pos, title, fpart, anchor in sorted(marks, key=lambda x: x[0]):
            if pos in seen:
                continue
            seen.add(pos)
            uniq.append((pos, title, fpart, anchor))

        chapters = []
        if uniq and full_text.strip():
            for i, (pos, title, fpart, anchor) in enumerate(uniq):
                end = uniq[i + 1][0] if i + 1 < len(uniq) else len(full_text)
                chunk = full_text[pos:end].strip()
                if chunk:
                    chapters.append({"title": title, "text": chunk,
                                     "epub_file": fpart, "epub_anchor": anchor})

        # 6. Fallback: one chapter per spine file
        if not chapters:
            offset = 0
            for f in spine_files:
                if f not in names:
                    continue
                text, _ = html_to_text_and_ids(z.read(f))
                text = text.strip()
                if not text:
                    continue
                title = _first_heading(text) or os.path.basename(f)
                chapters.append({"title": title, "text": text,
                                 "epub_file": f, "epub_anchor": None})

        return chapters


def _first_heading(text):
    for line in text.splitlines():
        line = line.strip()
        if line:
            return line[:120]
    return None


# ---------------------------------------------------------------------------
# FB2 parsing
# ---------------------------------------------------------------------------

def parse_fb2(path):
    data = open(path, "rb").read()
    root = ET.fromstring(data)
    body = next((el for el in root.iter() if _local(el.tag) == "body"), None)
    if body is None:
        raise ValueError("FB2: no <body> element")
    chapters = []

    def section_text(sec):
        title = ""
        title_el = next((c for c in sec if _local(c.tag) == "title"), None)
        if title_el is not None:
            title = " ".join("".join(title_el.itertext()).split())
        # text = everything except nested <section> (handled separately)
        parts = []
        for c in sec:
            if _local(c.tag) == "section":
                continue
            parts.append("".join(c.itertext()))
        text = re.sub(r"\n{3,}", "\n\n", "\n\n".join(p.strip() for p in parts if p.strip()))
        return title, text.strip()

    sections = [el for el in body if _local(el.tag) == "section"]
    if not sections:
        sections = [body]
    for sec in sections:
        title, text = section_text(sec)
        if text or title:
            chapters.append({"title": title or "Без названия", "text": text})
    return chapters


# ---------------------------------------------------------------------------
# TXT parsing (best-effort heading detection)
# ---------------------------------------------------------------------------

HEADING_RE = re.compile(
    r"^\s*(глава|chapter|часть|part|раздел)\s+[\dIVXLC]+[\.\):]?.*$",
    re.IGNORECASE,
)


def parse_txt(path):
    with open(path, "r", encoding="utf-8", errors="replace") as f:
        text = f.read()
    return split_text_by_headings(text, os.path.basename(path))


def split_text_by_headings(text, fallback_title):
    lines = text.splitlines()
    idxs = [i for i, ln in enumerate(lines) if HEADING_RE.match(ln)]
    chapters = []
    if idxs:
        for j, start in enumerate(idxs):
            end = idxs[j + 1] if j + 1 < len(idxs) else len(lines)
            title = lines[start].strip()
            body = "\n".join(lines[start + 1:end]).strip()
            chapters.append({"title": title, "text": body})
    else:
        chapters.append({"title": fallback_title, "text": text.strip()})
    return chapters


# ---------------------------------------------------------------------------
# PDF parsing (best-effort, requires pypdf)
# ---------------------------------------------------------------------------

def parse_pdf(path):
    try:
        from pypdf import PdfReader
    except ImportError:
        raise ValueError(
            "PDF support needs pypdf. Create the skills venv and run the script with it:\n"
            "  python3 -m venv ~/.claude/skills/.venv && "
            "~/.claude/skills/.venv/bin/pip install lxml markdown pypdf\n"
            "  ~/.claude/skills/.venv/bin/python ~/.claude/skills/book-chapter-digest/scripts/build_index.py <book>"
        )
    reader = PdfReader(path)
    n_pages = len(reader.pages)
    page_text = [reader.pages[i].extract_text() or "" for i in range(n_pages)]

    # Use outline/bookmarks if present
    bookmarks = []
    try:
        def walk(items):
            for it in items:
                if isinstance(it, list):
                    walk(it)
                else:
                    try:
                        pg = reader.get_destination_page_number(it)
                        bookmarks.append((str(it.title).strip(), pg))
                    except Exception:
                        pass
        walk(reader.outline)
    except Exception:
        bookmarks = []

    chapters = []
    if bookmarks:
        bookmarks.sort(key=lambda x: x[1])
        for j, (title, start) in enumerate(bookmarks):
            end = bookmarks[j + 1][1] if j + 1 < len(bookmarks) else n_pages
            body = "\n".join(page_text[start:end]).strip()
            if body:
                chapters.append({"title": title or f"Стр. {start+1}", "text": body})
    else:
        # no outline: try heading detection across the whole text
        full = "\n".join(page_text)
        chapters = split_text_by_headings(full, os.path.basename(path))
        if len(chapters) == 1:
            chapters[0]["_warning"] = (
                "PDF has no bookmarks and no detectable chapter headings — "
                "treated as a single block. Chapter-level extraction may be unreliable."
            )
    return chapters


# ---------------------------------------------------------------------------
# Driver
# ---------------------------------------------------------------------------

def words(text):
    return len(text.split())


_MATTER_RE = re.compile(
    r"\b(copyright|dedication|contents|table of contents|acknowledg|"
    r"about the author|about the publisher|title page|cover|colophon|"
    r"index|notes|bibliography|references|epigraph|praise for|also by|"
    r"оглавление|содержание|благодарност|об автор|выходные данные|"
    r"титул|примечани|библиографи|указатель|посвящ)",
    re.IGNORECASE,
)


def looks_like_matter(title):
    """Cheap, title-only hint that an entry is front/back matter, not a chapter.
    Advisory only — the skill is told to verify by looking at the text."""
    t = (title or "").strip().lower()
    return bool(_MATTER_RE.search(t))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("book", help="Path to the book file (.epub/.fb2/.txt/.pdf)")
    ap.add_argument("--cache-dir", default=None)
    args = ap.parse_args()

    book = args.book
    if not os.path.exists(book):
        print(f"ERROR: file not found: {book}", file=sys.stderr)
        sys.exit(1)

    ext = os.path.splitext(book)[1].lower()
    cache_dir = args.cache_dir or (os.path.splitext(book)[0] + ".digest")
    os.makedirs(cache_dir, exist_ok=True)

    parsers = {
        ".epub": parse_epub,
        ".fb2": parse_fb2,
        ".txt": parse_txt,
        ".pdf": parse_pdf,
    }
    if ext not in parsers:
        print(f"ERROR: unsupported format '{ext}'. Supported: {', '.join(parsers)}",
              file=sys.stderr)
        sys.exit(1)

    try:
        chapters = parsers[ext](book)
    except Exception as e:
        print(f"ERROR parsing book: {e}", file=sys.stderr)
        sys.exit(1)

    chapters = [c for c in chapters if c.get("text", "").strip()]
    if not chapters:
        print("ERROR: no readable chapters extracted. The file may be DRM-protected "
              "or image-only (scanned).", file=sys.stderr)
        sys.exit(1)

    # write cache
    index = {"book": os.path.basename(book), "format": ext, "chapters": []}
    for i, ch in enumerate(chapters, 1):
        fname = f"chap_{i:03d}.txt"
        with open(os.path.join(cache_dir, fname), "w", encoding="utf-8") as f:
            f.write(ch["text"])
        entry = {
            "n": i,
            "title": ch["title"],
            "file": fname,
            "words": words(ch["text"]),
            "matter": looks_like_matter(ch["title"]),
            "warning": ch.get("_warning"),
        }
        # in-book location (EPUB only) — needed by epub-digest-embed for injection
        if ch.get("epub_file"):
            entry["epub_file"] = ch["epub_file"]
            entry["epub_anchor"] = ch.get("epub_anchor")
        index["chapters"].append(entry)
    with open(os.path.join(cache_dir, "index.json"), "w", encoding="utf-8") as f:
        json.dump(index, f, ensure_ascii=False, indent=2)

    # print table
    print(f"Книга: {index['book']}  ({ext}, разделов: {len(chapters)})")
    print(f"Кэш: {cache_dir}")
    print("-" * 64)
    tiny, huge = [], []
    for ch in index["chapters"]:
        mins = max(1, round(ch["words"] / 220))
        tags = []
        if ch["matter"]:
            tags.append("служебный?")
        if ch["warning"]:
            tags.append("⚠️ " + ch["warning"])
        tag = ("  [" + "; ".join(tags) + "]") if tags else ""
        title = ch["title"] if len(ch["title"]) <= 64 else ch["title"][:61] + "..."
        print(f"{ch['n']:>3}. {title}  ({ch['words']} сл · ~{mins} мин){tag}")
        if ch["words"] < 40 and not ch["matter"]:
            tiny.append(ch["n"])
        if ch["words"] > 12000:
            huge.append(ch["n"])

    # structure sanity signals for the skill / user
    notes = []
    n_content = sum(1 for c in index["chapters"] if not c["matter"])
    if n_content <= 1:
        notes.append("Похоже, книга НЕ разбита на главы (один большой блок) — "
                     "проверь вручную и предложи деление по разделам.")
    if tiny:
        notes.append(f"Очень короткие разделы {tiny} — возможно разделители/"
                     "пустышки, не настоящие главы.")
    if huge:
        notes.append(f"Очень длинные разделы {huge} — внутри может быть "
                     "несколько глав без якорей; проверь содержимое.")
    if notes:
        print("-" * 64)
        print("СИГНАЛЫ О СТРУКТУРЕ:")
        for nt in notes:
            print("  • " + nt)


if __name__ == "__main__":
    main()
