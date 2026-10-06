#!/usr/bin/env python3
"""
extract_chapter.py — Print the VERBATIM text of selected chapters from the cache.

The summarizer must call this and read its output before writing any summary.
It never paraphrases or invents — it only echoes the cached real chapter text.

Usage:
    ~/.claude/skills/.venv/bin/python extract_chapter.py <cache_dir> <selector> [selector ...]
    ~/.claude/skills/.venv/bin/python extract_chapter.py <cache_dir> --title "substring"
    ~/.claude/skills/.venv/bin/python extract_chapter.py <cache_dir> --list

Selectors:
    5         single chapter
    5-7       inclusive range
    2,4,9     comma list (also works as separate args)
"""

import sys
import os
import re
import json
import argparse


def load_index(cache_dir):
    p = os.path.join(cache_dir, "index.json")
    if not os.path.exists(p):
        print(f"ERROR: no index at {p}. Run build_index.py first.", file=sys.stderr)
        sys.exit(1)
    with open(p, encoding="utf-8") as f:
        return json.load(f)


def resolve_selectors(selectors, max_n):
    nums = []
    for s in selectors:
        for part in str(s).split(","):
            part = part.strip()
            if not part:
                continue
            m = re.match(r"^(\d+)\s*-\s*(\d+)$", part)
            if m:
                a, b = int(m.group(1)), int(m.group(2))
                nums.extend(range(min(a, b), max(a, b) + 1))
            elif part.isdigit():
                nums.append(int(part))
    # dedupe preserving order, clamp to valid range
    out = []
    for n in nums:
        if 1 <= n <= max_n and n not in out:
            out.append(n)
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("cache_dir")
    ap.add_argument("selectors", nargs="*")
    ap.add_argument("--title", default=None, help="match chapters by title substring")
    ap.add_argument("--list", action="store_true", help="list chapters and exit")
    args = ap.parse_args()

    index = load_index(args.cache_dir)
    chapters = index["chapters"]
    by_n = {c["n"]: c for c in chapters}
    max_n = max(by_n) if by_n else 0

    if args.list:
        for c in chapters:
            print(f"{c['n']:>3}. {c['title']}  ({c['words']} сл)")
        return

    selected = []
    if args.title:
        q = args.title.lower()
        selected = [c["n"] for c in chapters if q in c["title"].lower()]
        if not selected:
            print(f"Нет глав с '{args.title}' в названии. Доступные главы:",
                  file=sys.stderr)
            for c in chapters:
                print(f"  {c['n']}. {c['title']}", file=sys.stderr)
            sys.exit(2)
    else:
        selected = resolve_selectors(args.selectors, max_n)

    if not selected:
        print("Не указано ни одной валидной главы. Доступно: "
              f"1..{max_n}", file=sys.stderr)
        sys.exit(2)

    for n in selected:
        ch = by_n[n]
        text = open(os.path.join(args.cache_dir, ch["file"]),
                    encoding="utf-8").read()
        print("=" * 72)
        print(f"ГЛАВА {n}: {ch['title']}  ({ch['words']} слов)")
        if ch.get("warning"):
            print(f"⚠️  {ch['warning']}")
        print("=" * 72)
        print(text)
        print()


if __name__ == "__main__":
    main()
