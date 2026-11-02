---
name: diffs
description: Produce real, shareable diffs (unified patch or rendered HTML) instead of describing edits in prose. Use whenever you edit or compare files, prepare a code review, or the user asks "show me the diff", "fammi vedere il diff", "cosa e cambiato".
---

# diffs

Whenever edits or differences between versions must be shown, produce a **real diff** — not a prose summary.

## When to use

- After editing files: show what changed.
- Comparing two revisions, branches, or two arbitrary files.
- Code review, PR descriptions, "what changed?" requests.
- Anywhere a unified patch or a rendered diff view is more useful than a description.

## Preferred commands

- Inside a git repo: `git diff`, `git diff --stat`, `git diff --staged`, `git show <rev>`.
- Between two commits/branches: `git diff <a>..<b>`.
- Two arbitrary files (no repo needed): `git diff --no-index old new` or `diff -u old new`.
- Only a summary is wanted: `git diff --stat` (or `--numstat`).

Prefer `git diff --no-index` when available — it gives colourised, unified output for any pair of files.

## Rendering a shareable diff

For a self-contained, side-by-side HTML you can open, attach, or send, use the helper:

```bash
# before/after text files
python3 scripts/render_diff.py --before old.txt --after new.txt --path "src/app.py" --out /tmp/diff.html

# a unified patch (from git diff, diff -u, etc.)
git diff > /tmp/change.patch
python3 scripts/render_diff.py --patch /tmp/change.patch --out /tmp/diff.html

# names for display / text-only output
python3 scripts/render_diff.py --before a.py --after b.py --title "Fix parser" --text
```

The helper is pure Python 3 standard library (`difflib`) — it works on Linux (DGX) and Windows.

- `--out <file>` writes a self-contained HTML (no external assets) you can share or attach.
- `--text` also prints a plain unified diff to stdout.
- identical inputs produce an empty diff and say so — do not fabricate changes.

## Delivery

- To send the rendered diff to the user, pass the HTML path to your file/message-sending tool
  (e.g. the `telegram-file-send` skill on the DGX).
- To embed it, open the HTML locally or attach it; it needs no server.

## Notes

- Keep the original `path`/`title` so the diff is self-describing.
- For very large diffs, show `--stat` first and render only the relevant files.
- Never hand-write a fake +N/-N summary: always derive it from a real diff command.
