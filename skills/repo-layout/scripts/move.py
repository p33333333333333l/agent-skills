#!/usr/bin/env python3
"""Apply a layout plan: move files and rewrite the references that point at them.

Language-agnostic on purpose. Instead of parsing each language's import
syntax, it works on what every language has in common: the moved file's path,
written as text somewhere in the repo. Three forms are recognised.

  repo path      src/data/nav.ts   src/data/nav
  relative path  ../data/nav       ./nav
  bare specifier  kept untouched -- too ambiguous to rewrite safely

The plan is JSON, one entry per move:

  {"moves": [{"from": "src/data/nav.ts", "to": "src/lib/nav.ts"}],
   "verify": "npm run test"}

Nothing happens unless --apply is passed. `--apply` requires a clean tree
(override with --allow-dirty), and every move goes through `git mv`, so
`git restore --staged --worktree . && git clean -fd` puts everything back.
"""

import argparse
import json
import os
import re
import subprocess
import sys
from pathlib import Path

TEXT_SUFFIXES = {
    ".py", ".js", ".mjs", ".cjs", ".ts", ".tsx", ".jsx", ".vue", ".svelte",
    ".go", ".rs", ".java", ".kt", ".rb", ".php", ".cs", ".c", ".cc", ".cpp",
    ".h", ".hpp", ".swift", ".scala", ".sh", ".bash", ".zsh", ".lua", ".ex",
    ".exs", ".erl", ".hs", ".ml", ".clj", ".dart", ".r", ".jl",
    ".md", ".json", ".yml", ".yaml", ".toml", ".txt", ".cfg", ".ini", ".xml",
    ".css", ".scss", ".sass", ".less", ".html", ".htm", ".astro", ".mdx",
    ".ipynb", ".sql", ".proto", ".gradle", ".cmake", "",
}
MAX_FILE = 2 * 1024 * 1024


def git(repo, *args, check=True):
    out = subprocess.run(["git", "-C", str(repo), *args],
                         capture_output=True, text=True, errors="replace")
    if check and out.returncode != 0:
        raise SystemExit(f"git {' '.join(args)} failed: {out.stderr.strip()}")
    return out


def tracked(repo):
    return [p for p in git(repo, "ls-files", "-z").stdout.split("\0") if p]


def is_text(path):
    try:
        if path.stat().st_size > MAX_FILE:
            return False
        return b"\0" not in path.read_bytes()[:4096]
    except OSError:
        return False


def validate(repo, moves):
    """Reject a plan before touching anything."""
    errors = []
    seen_targets = {}
    for i, mv in enumerate(moves):
        src, dst = mv.get("from"), mv.get("to")
        if not src or not dst:
            errors.append(f"move #{i}: needs both 'from' and 'to'")
            continue
        for p in (src, dst):
            if Path(p).is_absolute() or ".." in Path(p).parts:
                errors.append(f"move #{i}: path must stay inside the repo: {p}")
        if not (repo / src).exists():
            errors.append(f"move #{i}: source missing: {src}")
        if (repo / dst).exists():
            errors.append(f"move #{i}: target already exists: {dst}")
        if dst in seen_targets:
            errors.append(f"move #{i}: target claimed twice: {dst}")
        seen_targets[dst] = src
        if Path(src).suffix != Path(dst).suffix:
            errors.append(f"move #{i}: extension change {src} -> {dst} "
                          f"would break references; move without renaming")
    return errors


def token_re(old):
    """Every way a path to `old` can appear, as one match.

    Group 1 is the directory part, group 3 the extension. Matching the whole
    token (rather than guessing which relative form a file happens to use)
    means `./nav`, `../data/nav`, `src/data/nav` and `src/data/nav.ts` are all
    found by the same pattern, and the bare `nav` (a package name, not a path)
    is recognised and skipped.
    """
    return re.compile(
        r"(?<![A-Za-z0-9_.\-])"
        r"((?:\.{1,2}/)*(?:[A-Za-z0-9_.\-]+/)*)"
        + re.escape(Path(old).stem)
        + r"(?![A-Za-z0-9_\-])"
        r"(\.[A-Za-z0-9]+)?"
    )


def path_shaped(token):
    """A bare `nav` is a package name; a path has a directory part or a suffix."""
    return "/" in token or "." in token


def target(token, ref_file, old, repo):
    """Absolute path `token` in `ref_file` points at, or None if it is not `old`."""
    ref_dir = repo / Path(ref_file).parent
    base = ref_dir / token if token.startswith(".") else repo / token
    want = os.path.normpath(repo / old)
    for cand in (base, base.with_name(base.name + Path(old).suffix)):
        if os.path.normpath(cand) == want:
            return cand
    return None


def replacement(token, ref_file, new, repo):
    """`new` written in the same style as `token`: relative or repo-relative."""
    if token.startswith("."):
        ref_dir = repo / Path(ref_file).parent
        r = os.path.normpath(os.path.relpath(repo / new, ref_dir))
        r = r.replace(os.sep, "/")
        r = r if r.startswith(".") else "./" + r
    else:
        r = str(new)
    suffix = Path(new).suffix
    return r[: -len(suffix)] if not Path(token).suffix and r.endswith(suffix) else r


def rewrite(repo, moves, apply):
    """Rewrite every reference to a moved path.

    All edits for one file are spliced into the original text at once, so a
    replacement can never be re-matched by a later move.
    """
    files = tracked(repo)
    changed, hits = [], []

    for rel_file in files:
        if Path(rel_file).suffix.lower() not in TEXT_SUFFIXES:
            continue
        p = repo / rel_file
        if not is_text(p):
            continue
        try:
            original = p.read_text(encoding="utf-8", errors="surrogateescape")
        except OSError:
            continue

        spans, counts = [], {}
        for mv in moves:
            if rel_file == mv["from"]:
                continue
            for m in token_re(mv["from"]).finditer(original):
                tok = m.group(0)
                if not path_shaped(tok):
                    continue
                if target(tok, rel_file, mv["from"], repo) is None:
                    continue
                repl = replacement(tok, rel_file, mv["to"], repo)
                spans.append((m.start(), m.end(), repl))
                counts[tok] = (counts.get(tok, (0, repl))[0] + 1, repl)

        if not spans:
            continue
        spans.sort()
        kept, end = [], -1
        for s, e, r in spans:
            if s >= end:
                kept.append((s, e, r))
                end = e
        text, cursor = [], 0
        for s, e, r in kept:
            text.append(original[cursor:s])
            text.append(r)
            cursor = e
        text.append(original[cursor:])
        new_text = "".join(text)

        for tok, (n, repl) in counts.items():
            hits.append({"file": rel_file, "from": tok, "to": repl, "count": n})
        if new_text != original:
            changed.append(rel_file)
            if apply:
                p.write_text(new_text, encoding="utf-8", errors="surrogateescape")
    return changed, hits


def leftover(repo, moves):
    """Path-shaped references to the old location that survived the rewrite."""
    stale = []
    for rel_file in tracked(repo):
        p = repo / rel_file
        if Path(rel_file).suffix.lower() not in TEXT_SUFFIXES or not is_text(p):
            continue
        try:
            text = p.read_text(encoding="utf-8", errors="surrogateescape")
        except OSError:
            continue
        for mv in moves:
            if rel_file == mv["from"]:
                continue
            for m in token_re(mv["from"]).finditer(text):
                tok = m.group(0)
                if path_shaped(tok) and target(tok, rel_file, mv["from"], repo):
                    stale.append({"file": rel_file, "still": tok})
                    break
    return stale


def main():
    ap = argparse.ArgumentParser(description="Apply a layout plan (moves + reference rewrite)")
    ap.add_argument("plan", help="JSON plan file")
    ap.add_argument("--apply", action="store_true", help="actually change files")
    ap.add_argument("--allow-dirty", action="store_true")
    ap.add_argument("--no-verify", action="store_true")
    args = ap.parse_args()

    plan = json.loads(Path(args.plan).read_text(encoding="utf-8"))
    repo = Path(plan.get("repo", ".")).resolve()
    if not (repo / ".git").exists():
        raise SystemExit(f"{repo} is not a git repository root")
    moves = plan.get("moves") or []
    if not moves:
        raise SystemExit("plan has no moves")

    errors = validate(repo, moves)
    if errors:
        print("PLAN REJECTED", file=sys.stderr)
        for e in errors:
            print("  " + e, file=sys.stderr)
        return 2

    dirty = git(repo, "status", "--porcelain").stdout.strip()
    if dirty and args.apply and not args.allow_dirty:
        print("working tree is not clean; commit or stash first, "
              "or pass --allow-dirty", file=sys.stderr)
        return 3

    print(f"{'APPLYING' if args.apply else 'DRY RUN'}: {len(moves)} move(s) in {repo}")
    for mv in moves:
        print(f"  {mv['from']}  ->  {mv['to']}")

    if args.apply:
        for mv in moves:
            dst = repo / mv["to"]
            dst.parent.mkdir(parents=True, exist_ok=True)
            git(repo, "mv", mv["from"], mv["to"])

    changed, hits = rewrite(repo, moves, args.apply)
    print(f"\nreferences: {len(hits)} occurrence(s) across {len(changed)} file(s)")
    for h in hits:
        print(f"  {h['file']}: {h['from']} -> {h['to']} ({h['count']}x)")

    if not args.apply:
        print("\ndry run only -- nothing written. re-run with --apply")
        return 0

    stale = leftover(repo, moves)
    if stale:
        print("\nWARNING: old paths still referenced:")
        for s in stale:
            print(f"  {s['file']}: {s['still']}")
    else:
        print("\nno stale reference to the old paths")

    verify = plan.get("verify")
    if verify and not args.no_verify:
        print(f"\nverify: {verify}")
        res = subprocess.run(verify, shell=True, cwd=repo, text=True,
                             capture_output=True, errors="replace")
        tail = (res.stdout + res.stderr).strip().splitlines()[-15:]
        for line in tail:
            print("  " + line)
        if res.returncode != 0:
            print(f"\nVERIFY FAILED (exit {res.returncode})")
            print("restore with: git -C {} restore --staged --worktree . && git -C {} clean -fd".format(repo, repo))
            return 4
        print("verify passed")
    print("\ndone. review with: git -C %s status" % repo)
    return 0


if __name__ == "__main__":
    sys.exit(main())
