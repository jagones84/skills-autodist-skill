#!/usr/bin/env python3
"""Render a diff (before/after or unified patch) as a self-contained HTML file.

Pure Python 3 standard library (difflib). Works on Linux and Windows.

Examples:
  render_diff.py --before old.py --after new.py --path src/app.py --out diff.html
  render_diff.py --patch change.patch --out diff.html --text
  render_diff.py --before a.txt --after b.txt --title "Fix" --layout split
"""
import argparse
import difflib
import sys
from pathlib import Path

CSS = """
body{background:#1b1b1f;color:#e6e6e6;font-family:ui-monospace,SFMono-Regular,Menlo,Consolas,monospace;
     margin:0;padding:24px}
h1{font-size:16px;font-weight:600;color:#e6e6e6;margin:0 0 4px}
.meta{color:#9aa0a6;font-size:12px;margin:0 0 16px}
.empty{color:#9aa0a6;padding:16px;border:1px solid #333;border-radius:8px}
table.diff{width:100%;border-collapse:collapse;font-size:13px;line-height:1.45;
     border:1px solid #333;border-radius:8px;overflow:hidden}
table.diff td{padding:1px 6px;vertical-align:top}
table.diff th{padding:6px 10px;background:#26262b;color:#cfcfcf;text-align:left;font-weight:600}
table.diff .diff_header{background:#26262b;color:#9aa0a6;text-align:right;width:48px;
     border-right:1px solid #333;user-select:none}
table.diff td.diff_header{padding-right:8px}
.diff_next{background:#2a2a30;color:#9aa0a6}
.diff_add{background:#16351f}
.diff_chg{background:#3a2f10}
.diff_sub{background:#3a1a1a}
table.diff ins{background:#1f6f3a;color:#eaffea;text-decoration:none}
table.diff del{background:#7a2222;color:#ffeaea;text-decoration:none}
"""


def read_text(path):
    return Path(path).read_text(encoding="utf-8", errors="replace")


def parse_patch(text):
    """Split a unified patch into per-file (name, before, after) blocks."""
    files = []
    cur_name, cur_lines = None, []
    for line in text.splitlines(keepends=True):
        if line.startswith("diff --git ") or line.startswith("--- "):
            if cur_name is not None:
                files.append((cur_name, cur_lines))
            cur_name = line.split()[-1] if line.startswith("diff --git ") else line[4:].strip()
            cur_lines = [line]
        elif cur_name is not None:
            cur_lines.append(line)
    if cur_name is not None:
        files.append((cur_name, cur_lines))
    return files


def render(before, after, name, layout):
    a = before.splitlines()
    b = after.splitlines()
    return difflib.HtmlDiff(tabsize=4, wrapcolumn=None).make_table(
        a, b, fromdesc="before", todesc="after",
        context=True, numlines=3,
    )


def main():
    ap = argparse.ArgumentParser(description="Render a diff to self-contained HTML.")
    src = ap.add_mutually_exclusive_group(required=True)
    src.add_argument("--patch", help="unified patch file (git diff / diff -u output)")
    src.add_argument("--before", help="before text file (use with --after)")
    ap.add_argument("--after", help="after text file (use with --before)")
    ap.add_argument("--path", default="", help="display path/name for before/after input")
    ap.add_argument("--title", default="diff", help="HTML title")
    ap.add_argument("--out", default="diff.html", help="output HTML path")
    ap.add_argument("--text", action="store_true", help="also print a unified diff to stdout")
    ap.add_argument("--layout", choices=["unified", "split"], default="unified")
    args = ap.parse_args()

    if args.before:
        if not args.after:
            sys.exit("ERROR: --before requires --after")
        name = args.path or Path(args.before).name
        before, after = read_text(args.before), read_text(args.after)
        blocks = [(name, before, after)]
    else:
        patch = read_text(args.patch)
        if "--- " in patch and "@@" in patch:
            import re
            blocks = []
            for chunk in re.split(r"(?m)^(?=diff --git )", patch):
                if not chunk.strip():
                    continue
                fname = chunk.splitlines()[0]
                fname = fname.split(" b/")[-1].split()[-1] if fname.startswith("diff --git") else "(patch)"
                blocks.append((fname, chunk, None))
        else:
            blocks = [("(patch)", patch, None)]

    parts = ['<!DOCTYPE html><html><head><meta charset="utf-8">',
             '<title>%s</title><style>%s</style></head><body>' % (args.title, CSS),
             '<h1>%s</h1>' % args.title, '<p class="meta">rendered by diffs/render_diff.py</p>']

    text_out = []
    changed_any = False

    for name, before, after in blocks:
        if after is not None and before == after:
            continue
        changed_any = True
        if after is not None:
            a, b = before, after
            parts.append('<p class="meta">%s</p>' % name)
            parts.append(render(a, b, name, args.layout))
            if args.text:
                text_out.extend(difflib.unified_diff(a.splitlines(), b.splitlines(),
                                                     fromfile="a/" + name, tofile="b/" + name, lineterm=""))
        else:
            parts.append('<p class="meta">%s</p>' % name)
            parts.append('<pre style="white-space:pre-wrap;font-size:13px">%s</pre>'
                         % before.replace("&", "&amp;").replace("<", "&lt;"))
            if args.text:
                text_out.append(before)

    if not changed_any:
        parts.append('<div class="empty">No differences (inputs identical).</div>')

    parts.append("</body></html>")
    Path(args.out).write_text("\n".join(parts), encoding="utf-8")

    if args.text and text_out:
        print("\n".join(text_out))

    if changed_any:
        print("OK: diff written -> %s" % args.out)
    else:
        print("OK: no differences; wrote %s" % args.out)


if __name__ == "__main__":
    main()
