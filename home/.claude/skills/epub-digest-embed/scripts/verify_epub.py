#!/usr/bin/env python3
"""
verify_epub.py — Prove the embedded EPUB is correct before it ships.

The embed skill is responsible for a GOOD output file; a broken or wrong file is
not an option. This script does the mechanical half of that responsibility and
exits non-zero (with specifics) if anything is wrong, so the skill knows to
diagnose and rebuild rather than deliver.

Checks:
  STRUCTURE
    - zip integrity; mimetype is the first entry and STORED
    - every .opf/.ncx/.xhtml/.html parses as well-formed XML
  PLACEMENT + CONTENT (per unit, using a distinctive probe from the unit's md)
    - front: a <section id="dig-<uid>"> exists in the digest doc and actually
      contains the unit's text (not random/garbled content)
    - inline: a block id="dig-inline-<uid>" exists in the unit's inject_file,
      contains the unit's text, and sits BEFORE the chapter anchor
  NAVIGATION
    - every TOC target we added (digest doc + #anchors) resolves to a real file
      and a real id inside it (no dead links)

Usage:
    python verify_epub.py --epub OUT.epub --plan plan.json [--cache-dir DIR]
Exit code 0 = all good; 1 = problems (listed).
"""

import sys, os, re, json, argparse, zipfile
from lxml import etree as LET

XHTML = "http://www.w3.org/1999/xhtml"
PROBE_MIN = 18  # chars


def plain(md):
    """Strip markdown to plain text for probing."""
    t = re.sub(r"[#>*_`~\-]", " ", md)
    t = re.sub(r"\s+", " ", t)
    return t.strip()


def probe_from_md(md):
    """A distinctive text slice we expect to survive markdown->xhtml rendering."""
    # prefer the longest 'wordy' line
    best = ""
    for line in md.split("\n"):
        p = plain(line)
        # drop metadata-ish lines
        if re.search(r"\d+\s*слов|мин чтения", p):
            continue
        if len(p) > len(best):
            best = p
    best = best.strip()
    if len(best) < PROBE_MIN:
        best = plain(md)
    # take a middle slice to avoid leading markers
    mid = max(0, len(best) // 2 - 20)
    return best[mid:mid + 40].strip()


def el_text(el):
    return re.sub(r"\s+", " ", "".join(el.itertext())).strip()


def find_by_id(root, the_id):
    for el in root.iter():
        if el.get("id") == the_id:
            return el
    return None


def parse_xml(data):
    return LET.fromstring(data)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--epub", required=True)
    ap.add_argument("--plan", required=True)
    ap.add_argument("--cache-dir")
    args = ap.parse_args()

    plan = json.load(open(args.plan, encoding="utf-8"))
    units = plan["units"]
    placement = plan.get("placement", "both")
    toc_mode = plan.get("toc", "both")

    problems = []
    notes = []

    z = zipfile.ZipFile(args.epub)
    names = z.namelist()
    infos = z.infolist()

    # --- structure ---
    if z.testzip() is not None:
        problems.append("zip integrity check failed")
    if not infos or infos[0].filename != "mimetype":
        problems.append("mimetype is not the first zip entry")
    elif infos[0].compress_type != zipfile.ZIP_STORED:
        problems.append("mimetype is not STORED (uncompressed)")

    parsed = {}
    for n in names:
        if n.lower().endswith((".opf", ".ncx", ".xhtml", ".html")):
            try:
                parsed[n] = parse_xml(z.read(n))
            except Exception as e:
                problems.append(f"not well-formed XML: {n} :: {str(e)[:80]}")

    # locate digest doc
    digest_name = next((n for n in names if n.endswith("zz_digest.xhtml")), None)
    if placement in ("front", "both"):
        if not digest_name:
            problems.append("front placement requested but digest doc (zz_digest.xhtml) missing")

    # --- per-unit placement + content ---
    for u in units:
        uid = u["id"]
        probe = probe_from_md(u.get("md", ""))

        if placement in ("front", "both") and digest_name and digest_name in parsed:
            sec = find_by_id(parsed[digest_name], f"dig-{uid}")
            if sec is None:
                problems.append(f"[{uid}] front section dig-{uid} not found")
            elif probe and probe not in el_text(sec):
                problems.append(f"[{uid}] front section text doesn't contain expected probe «{probe}»")

        if placement in ("inline", "both"):
            f = u["inject_file"]
            if f not in parsed:
                problems.append(f"[{uid}] inject_file not parseable/missing: {f}")
            else:
                blk = find_by_id(parsed[f], f"dig-inline-{uid}")
                if blk is None:
                    problems.append(f"[{uid}] inline block dig-inline-{uid} not found in {os.path.basename(f)}")
                else:
                    if probe and probe not in el_text(blk):
                        problems.append(f"[{uid}] inline block text doesn't contain expected probe «{probe}»")
                    # ordering: block before chapter anchor
                    anchor = u.get("inject_anchor")
                    if anchor:
                        raw = z.read(f).decode("utf-8", "replace")
                        bpos = raw.find(f'dig-inline-{uid}')
                        m = re.search(r'<[^>]*\bid\s*=\s*["\']' + re.escape(anchor) + r'["\']', raw, re.I)
                        if m and bpos > -1 and bpos > m.start():
                            problems.append(f"[{uid}] inline block is AFTER the chapter anchor «{anchor}», expected before")

    # --- navigation: every added TOC target resolves ---
    def id_exists(fname, the_id):
        if fname not in parsed:
            return False
        return find_by_id(parsed[fname], the_id) is not None

    ncx_name = next((n for n in names if n.lower().endswith(".ncx")), None)
    opf_name = next((n for n in names if n.lower().endswith(".opf")), None)
    opf_dir = os.path.dirname(opf_name) if opf_name else ""

    def resolve_rel(base_file, href):
        d = os.path.dirname(base_file)
        return os.path.normpath(os.path.join(d, href)).replace("\\", "/")

    if ncx_name and ncx_name in parsed:
        for c in parsed[ncx_name].iter():
            if c.tag.split("}")[-1].lower() != "content":
                continue
            src = c.get("src") or ""
            if "dig-" not in src:
                continue  # only verify the entries we added
            path = resolve_rel(ncx_name, src.split("#")[0])
            anchor = src.split("#")[1] if "#" in src else None
            if path not in names:
                problems.append(f"NCX link to missing file: {src}")
            elif anchor and not id_exists(path, anchor):
                problems.append(f"NCX link to missing anchor: {src}")

    # nav (best-effort; only added entries)
    nav_name = None
    if opf_name and opf_name in parsed:
        for it in parsed[opf_name].iter():
            if it.tag.split("}")[-1].lower() == "item" and "nav" in (it.get("properties") or "").lower():
                nav_name = resolve_rel(opf_name, it.get("href"))
                break
    if nav_name and nav_name in parsed:
        for a in parsed[nav_name].iter():
            if a.tag.split("}")[-1].lower() != "a":
                continue
            href = a.get("href") or ""
            if "dig-" not in href:
                continue
            path = resolve_rel(nav_name, href.split("#")[0])
            anchor = href.split("#")[1] if "#" in href else None
            if path not in names:
                problems.append(f"nav link to missing file: {href}")
            elif anchor and not id_exists(path, anchor):
                problems.append(f"nav link to missing anchor: {href}")

    # --- report ---
    print(f"VERIFY {os.path.basename(args.epub)}  (units={len(units)}, placement={placement}, toc={toc_mode})")
    print("-" * 66)
    if not problems:
        print("✅ PASS — structure, placement, content probes and TOC links all OK.")
        for n in notes:
            print("  · " + n)
        sys.exit(0)
    print(f"❌ FAIL — {len(problems)} problem(s):")
    for p in problems:
        print("  • " + p)
    print("\nFix the cause and rebuild — do not ship this file.")
    sys.exit(1)


if __name__ == "__main__":
    main()
