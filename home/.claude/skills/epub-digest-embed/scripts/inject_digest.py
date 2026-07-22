#!/usr/bin/env python3
"""
inject_digest.py — Embed per-unit chapter digests into an EPUB, and register them
in the table of contents (NCX + EPUB3 nav).

It does ONLY the mechanical surgery. The digest *content* (wording, length, style,
verdict) is produced upstream by the book-chapter-digest skill and arrives here as
rendered Markdown inside plan.json — this script never writes or judges summaries.

plan.json schema (units, with `md` filled in by the caller after generation):
{
  "placement": "front" | "inline" | "both",
  "toc":       "section" | "nested" | "both",
  "units": [
    {
      "id": "u01",
      "kind": "chapter" | "subsection" | "group",
      "label": "Introduction: Life by Design",
      "source_chapters": [4],
      "inject_file": "OEBPS/..._itr_....xhtml",   # zip entry to inject before
      "inject_anchor": "h2" | null,               # id to insert before; null=body top
      "md": "## ... digest markdown ..."
    }, ...
  ]
}

Usage:
    python inject_digest.py --epub IN.epub --plan plan.json --out OUT.epub
"""

import sys, os, re, json, argparse, zipfile, shutil
import xml.etree.ElementTree as ET

try:
    import markdown as _md
except ImportError:
    _md = None
from lxml import html as LH, etree as LET


# --------------------------------------------------------------------------- #
# Markdown -> XHTML fragment
# --------------------------------------------------------------------------- #
_LIST_RE = re.compile(r"^(\s*)(\d+[.)]|[-*+])(\s+)(\S.*)$")


def _normalize_md(md_text):
    """Make the digest's Markdown robust for python-markdown without changing
    wording: (1) ensure a blank line precedes a list that directly follows a
    non-list line, and (2) snap list-marker indentation up to a multiple of 4
    spaces, because the digest template nests sub-lists at 3-space indent which
    python-markdown won't recognise as nesting."""
    lines = md_text.split("\n")
    out = []
    for ln in lines:
        m = _LIST_RE.match(ln)
        if m:
            indent = len(m.group(1).replace("\t", "    "))
            depth = (indent + 3) // 4 if indent else 0      # round up to /4
            new_indent = " " * (depth * 4)
            ln = f"{new_indent}{m.group(2)}{m.group(3)}{m.group(4)}"
            if out and out[-1].strip() and not _LIST_RE.match(out[-1]) and depth == 0:
                out.append("")  # blank line before a top-level list
        out.append(ln)
    return "\n".join(out)


def md_to_xhtml(md_text):
    """Render digest Markdown to a well-formed XHTML fragment string."""
    if _md is None:
        raise SystemExit("Need the 'markdown' package: pip install markdown --break-system-packages")
    raw = _md.markdown(_normalize_md(md_text), extensions=["extra", "sane_lists"])
    # normalise into valid XHTML via lxml (self-closes void tags, escapes stray &)
    frag = LH.fragment_fromstring(raw, create_parent="div")
    xml = LET.tostring(frag, encoding="unicode", method="xml")
    # strip the wrapper <div>...</div> we created
    xml = re.sub(r"^<div>", "", xml)
    xml = re.sub(r"</div>$", "", xml)
    return xml.strip()


CALLOUT_STYLE = (
    "border:1px solid #b9b9b9;border-left:4px solid #6a6a6a;border-radius:6px;"
    "padding:0.6em 0.9em;margin:1em 0;font-size:0.95em;line-height:1.5;"
)
LABEL_STYLE = (
    "margin:0 0 0.4em;font-weight:bold;letter-spacing:0.03em;"
    "text-transform:uppercase;font-size:0.8em;opacity:0.65;"
)


def callout(inner_xhtml, anchor_id, label="📖 Конспект"):
    return (
        f'<div id="{anchor_id}" class="chap-digest" style="{CALLOUT_STYLE}">'
        f'<p style="{LABEL_STYLE}">{label}</p>'
        f'{inner_xhtml}'
        f'</div>'
    )


# --------------------------------------------------------------------------- #
# EPUB container plumbing
# --------------------------------------------------------------------------- #
def load_epub(path):
    z = zipfile.ZipFile(path)
    files = {}
    order = []
    for info in z.infolist():
        files[info.filename] = z.read(info.filename)
        order.append(info.filename)
    z.close()
    return files, order


def find_opf(files):
    root = ET.fromstring(files["META-INF/container.xml"])
    for el in root.iter():
        if el.tag.split("}")[-1].lower() == "rootfile" and el.get("full-path"):
            return el.get("full-path")
    cand = [n for n in files if n.lower().endswith(".opf")]
    if cand:
        return cand[0]
    raise SystemExit("OPF not found")


def resolve(base_dir, href):
    href = href.split("#")[0]
    return os.path.normpath(os.path.join(base_dir, href)).replace("\\", "/")


# --------------------------------------------------------------------------- #
# Inline insertion (string surgery, minimal disruption)
# --------------------------------------------------------------------------- #
def insert_inline(html_text, anchor, block):
    if anchor:
        m = re.search(r'<[^>]*\bid\s*=\s*["\']' + re.escape(anchor) + r'["\'][^>]*>',
                      html_text, re.I)
        if m:
            return html_text[:m.start()] + block + "\n" + html_text[m.start():], True
    # fallback: right after <body ...>
    m = re.search(r"<body[^>]*>", html_text, re.I)
    if m:
        return html_text[:m.end()] + "\n" + block + html_text[m.end():], True
    return html_text, False


# --------------------------------------------------------------------------- #
# NCX helpers
# --------------------------------------------------------------------------- #
def ncx_ns(root):
    if root.tag.startswith("{"):
        return root.tag[1:].split("}")[0]
    return "http://www.daisy.org/z3986/2005/ncx/"


def q(ns, tag):
    return f"{{{ns}}}{tag}" if ns else tag


def make_navpoint(ns, np_id, order, label, src):
    np = LET.Element(q(ns, "navPoint"))
    np.set("id", np_id)
    np.set("playOrder", str(order))
    nl = LET.SubElement(np, q(ns, "navLabel"))
    t = LET.SubElement(nl, q(ns, "text"))
    t.text = label
    c = LET.SubElement(np, q(ns, "content"))
    c.set("src", src)
    return np


def patch_ncx(ncx_bytes, units, opf_dir, digest_href, mode, chap_loc):
    """mode: 'section' | 'nested' | 'both'. Returns new bytes or None on failure."""
    try:
        root = LET.fromstring(ncx_bytes)
    except Exception:
        return None
    ns = ncx_ns(root)
    navmap = root.find(q(ns, "navMap"))
    if navmap is None:
        return None

    # relative href of a target file as it should appear in TOC (relative to opf_dir)
    def rel(href_abs, anchor=None):
        r = os.path.relpath(href_abs, opf_dir).replace("\\", "/")
        return r + (f"#{anchor}" if anchor else "")

    order_base = 10000  # keep our entries late in playOrder, harmless

    if mode in ("section", "both"):
        parent = make_navpoint(ns, "digest-root", order_base,
                               "📖 Конспект по главам", rel(digest_href))
        for k, u in enumerate(units, 1):
            child = make_navpoint(ns, f"digest-{u['id']}", order_base + k,
                                  u["label"], rel(digest_href, f"dig-{u['id']}"))
            parent.append(child)
        navmap.append(parent)

    if mode in ("nested", "both"):
        # find each chapter's navPoint by matching content src, add an inline child
        content_els = [(np, np.find(q(ns, "content"))) for np in root.iter(q(ns, "navPoint"))]
        for u in units:
            loc = chap_loc.get(u["source_chapters"][0])
            if not loc:
                continue
            want_file = os.path.relpath(loc["epub_file"], opf_dir).replace("\\", "/")
            target_np = None
            for np, c in content_els:
                if c is None or not c.get("src"):
                    continue
                src_file = c.get("src").split("#")[0]
                if src_file == want_file:
                    src_anchor = c.get("src").split("#")[1] if "#" in c.get("src") else None
                    if (loc.get("epub_anchor") or None) == (src_anchor or None):
                        target_np = np
                        break
                    if target_np is None:
                        target_np = np  # file-level fallback
            if target_np is not None:
                inline_src = rel(loc["epub_file"], f"dig-inline-{u['id']}")
                target_np.append(make_navpoint(ns, f"digest-inl-{u['id']}",
                                               order_base + 5000, "↳ Конспект", inline_src))

    return LET.tostring(root, xml_declaration=True, encoding="utf-8")


# --------------------------------------------------------------------------- #
# EPUB3 nav.xhtml helpers (best-effort)
# --------------------------------------------------------------------------- #
def patch_nav(nav_bytes, units, nav_path, opf_dir, digest_href, mode, chap_loc):
    try:
        parser = LET.HTMLParser(encoding="utf-8")
        root = LET.fromstring(nav_bytes, parser)
    except Exception:
        return None
    # locate the toc <nav> and its first <ol>
    nav_el = None
    for nav in root.iter("nav"):
        et = (nav.get("{http://www.idpf.org/2007/ops}type") or nav.get("type")
              or nav.get("role") or nav.get("id") or "")
        if "toc" in et.lower():
            nav_el = nav
            break
    if nav_el is None:
        for nav in root.iter("nav"):
            nav_el = nav
            break
    if nav_el is None:
        return None
    ol = nav_el.find(".//ol")
    if ol is None:
        return None

    nav_dir = os.path.dirname(nav_path)

    def rel(href_abs, anchor=None):
        r = os.path.relpath(href_abs, nav_dir).replace("\\", "/")
        return r + (f"#{anchor}" if anchor else "")

    def li(href, text):
        e = LET.Element("li")
        a = LET.SubElement(e, "a")
        a.set("href", href)
        a.text = text
        return e

    if mode in ("section", "both"):
        top = LET.Element("li")
        a = LET.SubElement(top, "a")
        a.set("href", rel(digest_href))
        a.text = "📖 Конспект по главам"
        sub = LET.SubElement(top, "ol")
        for u in units:
            sub.append(li(rel(digest_href, f"dig-{u['id']}"), u["label"]))
        ol.append(top)

    if mode in ("nested", "both"):
        anchors = list(nav_el.iter("a"))
        for u in units:
            loc = chap_loc.get(u["source_chapters"][0])
            if not loc:
                continue
            want = os.path.relpath(loc["epub_file"], nav_dir).replace("\\", "/")
            target_li = None
            for a in anchors:
                href = (a.get("href") or "").split("#")[0]
                if href == want:
                    target_li = a.getparent()
                    break
            if target_li is not None and target_li.tag == "li":
                sub = target_li.find("ol")
                if sub is None:
                    sub = LET.SubElement(target_li, "ol")
                sub.append(li(rel(loc["epub_file"], f"dig-inline-{u['id']}"), "↳ Конспект"))

    return LET.tostring(root, method="xml", encoding="utf-8", xml_declaration=True)


# --------------------------------------------------------------------------- #
# Front digest document
# --------------------------------------------------------------------------- #
def build_digest_doc(units):
    body = ['<h1>📖 Конспект по главам</h1>',
            '<p style="opacity:0.6;font-size:0.9em;">Краткие выжимки по каждой главе. '
            'Сгенерированы автоматически; в самой книге продублированы перед началом глав.</p>']
    for u in units:
        inner = md_to_xhtml(u["md"])
        body.append(f'<section id="dig-{u["id"]}" style="margin:1.4em 0;">{inner}</section>')
    return (
        '<?xml version="1.0" encoding="utf-8"?>\n'
        '<!DOCTYPE html>\n'
        '<html xmlns="http://www.w3.org/1999/xhtml" xml:lang="ru" lang="ru">\n'
        '<head><meta charset="utf-8"/><title>Конспект по главам</title></head>\n'
        '<body>\n' + "\n".join(body) + '\n</body>\n</html>\n'
    )


# --------------------------------------------------------------------------- #
# OPF patching
# --------------------------------------------------------------------------- #
def patch_opf_add_digest(opf_bytes, opf_dir, digest_rel, first_content_file):
    root = LET.fromstring(opf_bytes)
    ns = root.tag[1:].split("}")[0] if root.tag.startswith("{") else ""
    manifest = root.find(q(ns, "manifest"))
    spine = root.find(q(ns, "spine"))
    # manifest item
    item = LET.SubElement(manifest, q(ns, "item"))
    item.set("id", "digest-doc")
    item.set("href", digest_rel)
    item.set("media-type", "application/xhtml+xml")
    # spine itemref before first content file
    itemref = LET.Element(q(ns, "itemref"))
    itemref.set("idref", "digest-doc")
    # map manifest id -> href to find the first content file's idref
    id_by_href = {}
    for it in manifest.iter(q(ns, "item")):
        id_by_href[resolve(opf_dir, it.get("href"))] = it.get("id")
    target_id = id_by_href.get(first_content_file)
    inserted = False
    if target_id:
        for i, ref in enumerate(list(spine)):
            if ref.get("idref") == target_id:
                spine.insert(i, itemref)
                inserted = True
                break
    if not inserted:
        spine.insert(0, itemref)
    return LET.tostring(root, xml_declaration=True, encoding="utf-8")


# --------------------------------------------------------------------------- #
# Rezip (mimetype first, stored)
# --------------------------------------------------------------------------- #
def write_epub(out_path, files, order):
    if os.path.exists(out_path):
        os.remove(out_path)
    zf = zipfile.ZipFile(out_path, "w")
    if "mimetype" in files:
        zf.writestr("mimetype", files["mimetype"], compress_type=zipfile.ZIP_STORED)
    for name in order:
        if name == "mimetype":
            continue
        zf.writestr(name, files[name], compress_type=zipfile.ZIP_DEFLATED)
    # any new files not in original order
    for name in files:
        if name not in order and name != "mimetype":
            zf.writestr(name, files[name], compress_type=zipfile.ZIP_DEFLATED)
    zf.close()


# --------------------------------------------------------------------------- #
def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--epub", required=True)
    ap.add_argument("--plan", required=True)
    ap.add_argument("--cache-dir", help="for index.json (chapter locations for nested TOC)")
    ap.add_argument("--md-out", help="also write a standalone Markdown digest of the whole book")
    ap.add_argument("--out", required=True)
    args = ap.parse_args()

    plan = json.load(open(args.plan, encoding="utf-8"))
    units = plan["units"]
    placement = plan.get("placement", "both")
    toc_mode = plan.get("toc", "both")
    for u in units:
        if not u.get("md", "").strip():
            raise SystemExit(f"unit {u['id']} has empty 'md' — generate digests first")

    # chapter locations (for nested TOC) from index.json if available
    chap_loc = {}
    if args.cache_dir:
        idx_path = os.path.join(args.cache_dir, "index.json")
        if os.path.exists(idx_path):
            idx = json.load(open(idx_path, encoding="utf-8"))
            for c in idx["chapters"]:
                chap_loc[c["n"]] = {"epub_file": c.get("epub_file"),
                                    "epub_anchor": c.get("epub_anchor")}

    files, order = load_epub(args.epub)
    opf_path = find_opf(files)
    opf_dir = os.path.dirname(opf_path)

    first_content_file = units[0]["inject_file"]

    warnings = []

    # 1. inline blocks
    if placement in ("inline", "both"):
        by_file = {}
        for u in units:
            by_file.setdefault(u["inject_file"], []).append(u)
        for fname, us in by_file.items():
            if fname not in files:
                warnings.append(f"inline: file not found in epub: {fname}")
                continue
            text = files[fname].decode("utf-8", errors="replace")
            # insert from last anchor position to first to avoid offset drift
            def anchor_pos(u):
                a = u.get("inject_anchor")
                if not a:
                    return -1
                m = re.search(r'<[^>]*\bid\s*=\s*["\']' + re.escape(a) + r'["\']', text, re.I)
                return m.start() if m else -1
            for u in sorted(us, key=anchor_pos, reverse=True):
                block = callout(md_to_xhtml(u["md"]), f"dig-inline-{u['id']}")
                text, ok = insert_inline(text, u.get("inject_anchor"), block)
                if not ok:
                    warnings.append(f"inline: anchor not found for {u['id']} in {fname}")
            files[fname] = text.encode("utf-8")

    # 2. front digest doc — place alongside the content files
    content_dir = os.path.dirname(first_content_file) or opf_dir
    digest_name = (content_dir + "/zz_digest.xhtml") if content_dir else "zz_digest.xhtml"
    digest_name = os.path.normpath(digest_name).replace("\\", "/")
    if placement in ("front", "both"):
        files[digest_name] = build_digest_doc(units).encode("utf-8")
        digest_rel = os.path.relpath(digest_name, opf_dir or ".").replace("\\", "/")
        files[opf_path] = patch_opf_add_digest(files[opf_path], opf_dir, digest_rel,
                                                first_content_file)
        order.append(digest_name)

    # 3. TOC — NCX
    ncx_name = next((n for n in files if n.lower().endswith(".ncx")), None)
    if ncx_name:
        new = patch_ncx(files[ncx_name], units, opf_dir, digest_name, toc_mode, chap_loc)
        if new:
            files[ncx_name] = new
        else:
            warnings.append("NCX present but could not be patched")

    # 4. TOC — EPUB3 nav
    # find nav doc via OPF manifest properties="nav"
    nav_name = None
    try:
        oroot = LET.fromstring(files[opf_path])
        ons = oroot.tag[1:].split("}")[0] if oroot.tag.startswith("{") else ""
        for it in oroot.iter(q(ons, "item")):
            if "nav" in (it.get("properties") or "").lower():
                nav_name = resolve(opf_dir, it.get("href"))
                break
    except Exception:
        pass
    if nav_name and nav_name in files:
        new = patch_nav(files[nav_name], units, nav_name, opf_dir, digest_name, toc_mode, chap_loc)
        if new:
            files[nav_name] = new
        else:
            warnings.append("nav.xhtml present but could not be patched (NCX still covers most readers)")

    write_epub(args.out, files, order)

    # standalone Markdown digest artifact (second deliverable)
    if args.md_out:
        title = plan.get("book") or os.path.splitext(os.path.basename(args.out))[0]
        parts = [f"# Конспект по главам — {title}\n",
                 "_Краткие выжимки по каждой главе (автогенерация)._\n"]
        for u in units:
            parts.append(u["md"].strip() + "\n")
            parts.append("\n---\n")
        if parts and parts[-1] == "\n---\n":
            parts.pop()
        with open(args.md_out, "w", encoding="utf-8") as fh:
            fh.write("\n".join(parts))

    print(f"OK → {args.out}")
    if args.md_out:
        print(f"  + markdown digest → {args.md_out}")
    print(f"  placement={placement}  toc={toc_mode}  units={len(units)}")
    if ncx_name:
        print(f"  NCX patched: {os.path.basename(ncx_name)}")
    if nav_name:
        print(f"  nav patched: {os.path.basename(nav_name)}")
    for w in warnings:
        print("  ⚠️ " + w)


if __name__ == "__main__":
    main()
