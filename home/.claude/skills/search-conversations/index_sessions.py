#!/usr/bin/env python3
"""Build a discriminator-rich index of Claude Code sessions.

Unlike grepping history.jsonl (user messages only), this surfaces the
assistant/tool side of each session — the part users actually remember:
  - aiTitle       : the AI-generated topic of the session
  - last reply    : how the session ENDED ("we finished on...")
  - files touched : artifacts the assistant created (Write/Edit) — ("you wrote an instruction")
  - first ask     : the user's opening request

Usage:
  index_sessions.py <project-dir-or-jsonl-dir> [FILTER]
  index_sessions.py all [FILTER]                 # every project under ~/.claude/projects

  FILTER (optional): comma/space-separated tokens, case-insensitive. A session
  is kept if ANY token appears in aiTitle / last reply / a touched filename /
  first ask (OR, not AND). Pass synonyms AND both languages — e.g.
  "config,конфиг,setup,инструкц" — a single word silently drops the target
  (the topic title may be in the other language). Filter only NARROWS; never
  treat a match as the answer — read the columns and match the discriminator
  from the user's request. When unsure, run with NO filter and read the map.

Output: one block per session, newest last. The 'id:' line is the verified
sessionId, byte-for-byte — copy it from here, never retype.
"""
import json, os, sys, glob, re

HOME = os.path.expanduser("~")
PROJECTS = os.path.join(HOME, ".claude", "projects")


def resolve_dirs(arg):
    if arg == "all":
        return sorted(glob.glob(os.path.join(PROJECTS, "*")))
    if os.path.isdir(arg):
        # a project source path like /Users/x/go/... -> -Users-x-go-...
        if os.path.isdir(os.path.join(arg, ".git")) or not arg.startswith(PROJECTS):
            # Claude Code slugifies the project path: every non-alnum char -> "-"
            slug = re.sub(r"[^A-Za-z0-9]", "-", arg)
            cand = os.path.join(PROJECTS, slug)
            if os.path.isdir(cand):
                return [cand]
        return [arg]
    sys.exit(f"not a directory: {arg}")


def text_blocks(msg):
    c = msg.get("content")
    if isinstance(c, str):
        return [c]
    out = []
    if isinstance(c, list):
        for b in c:
            if isinstance(b, dict) and b.get("type") == "text" and b.get("text", "").strip():
                out.append(b["text"])
    return out


def scan(path):
    title = last_reply = first_ask = None
    files = []
    for line in open(path, encoding="utf-8"):
        try:
            o = json.loads(line)
        except Exception:
            continue
        t = o.get("type")
        if t == "ai-title":
            title = o.get("aiTitle") or title
        m = o.get("message", {})
        role = m.get("role")
        if role == "user" and first_ask is None:
            for tb in text_blocks(m):
                s = tb.strip()
                if s and "<command-" not in s and "<local-command" not in s and "caveat" not in s.lower():
                    first_ask = s
                    break
        if role == "assistant":
            tbs = text_blocks(m)
            if tbs:
                last_reply = tbs[-1]
            c = m.get("content")
            if isinstance(c, list):
                for b in c:
                    if isinstance(b, dict) and b.get("type") == "tool_use" and b.get("name") in ("Write", "Edit", "NotebookEdit"):
                        fp = b.get("input", {}).get("file_path")
                        if fp:
                            files.append(os.path.basename(fp))
    return title, last_reply, first_ask, files


def main():
    if len(sys.argv) < 2:
        sys.exit(__doc__)
    arg = sys.argv[1]
    toks = [t for t in sys.argv[2].lower().replace(",", " ").split()] if len(sys.argv) > 2 else []
    rows = []
    for d in resolve_dirs(arg):
        for f in glob.glob(os.path.join(d, "*.jsonl")):
            try:
                title, last, first, files = scan(f)
            except Exception:
                continue
            sid = os.path.basename(f)[:-6]
            rows.append((os.path.getmtime(f), sid, os.path.basename(d), title, last, first, files))
    rows.sort()

    def oneline(s, n):
        return (" ".join((s or "").split()))[:n] or "—"

    shown = 0
    for mt, sid, proj, title, last, first, files in rows:
        uniqf = sorted(set(files))
        hay = " ".join([title or "", last or "", first or "", " ".join(uniqf)]).lower()
        if toks and not any(t in hay for t in toks):
            continue
        import datetime
        ts = datetime.datetime.fromtimestamp(mt).strftime("%Y-%m-%d %H:%M")
        print(f"id:    {sid}")
        print(f"  when:  {ts}")
        print(f"  title: {oneline(title, 100)}")
        print(f"  ask:   {oneline(first, 120)}")
        print(f"  ended: {oneline(last, 160)}")
        if uniqf:
            print(f"  files: {', '.join(uniqf[:12])}")
        print()
        shown += 1
    print(f"# {shown} session(s)" + (f" matching any of {toks}" if toks else ""))


if __name__ == "__main__":
    main()
