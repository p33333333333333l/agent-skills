#!/usr/bin/env python3
"""Repository layout inventory: measured evidence, language-agnostic.

Read-only. Reads the git index, tracked file contents, and the project's own
declaration files. Writes nothing, changes nothing.

Two outputs:
  facts     -- what is actually in the tree (counts, paths, sizes)
  drift     -- areas the project's own docs name, versus areas that exist.
               This is the part a generic linter cannot do: the project has
               written down its layout, and this diffs reality against it.

Every printed line carries a count or a path so the caller can cite it.
Nothing here decides that a file *should* move.
"""

import argparse
import json
import re
import subprocess
from collections import Counter, defaultdict
from pathlib import Path

# Files that commonly declare a project's own layout rules.
DECLARATION_NAMES = (
    "AGENTS.md", "CLAUDE.md", "SCHEMA.md", "ARCHITECTURE.md", "CONTRIBUTING.md",
    "STRUCTURE.md", "CONVENTIONS.md", "README.md", "README.zh.md", "README.en.md",
    "package.json", "pyproject.toml", "tsconfig.json", "Makefile", "justfile",
    "Cargo.toml", "go.mod", "astro.config.mjs", "vite.config.ts", "next.config.js",
)
DECLARATION_DIRS = ("docs", ".github", ".agents", "curation", "doc")

GENERATED_DIRS = {
    "node_modules", "dist", "build", "out", "target", "obj", "__pycache__",
    ".venv", "venv", "env", ".next", ".astro", ".nuxt", ".svelte-kit", ".turbo",
    ".parcel-cache", "coverage", ".pytest_cache", ".mypy_cache", ".ruff_cache",
    ".tox", "htmlcov", ".gradle", ".idea", ".cache", "vendor", "Pods", "bin",
}
GENERATED_SUFFIXES = (
    ".pyc", ".pyo", ".o", ".a", ".so", ".dylib", ".dll", ".class", ".jar",
    ".tsbuildinfo", ".log", ".tmp", ".swp", ".orig", ".rej", ".exe", ".pdb",
)

# Extensions eligible for the unreferenced-file check. Data and prose
# extensions are excluded on purpose: an unreferenced .md or .yml is normal.
SOURCE_SUFFIXES = {
    ".py", ".js", ".mjs", ".cjs", ".ts", ".tsx", ".jsx", ".vue", ".svelte",
    ".go", ".rs", ".java", ".kt", ".rb", ".php", ".cs", ".c", ".cc", ".cpp",
    ".h", ".hpp", ".swift", ".scala", ".sh", ".bash", ".zsh", ".lua", ".ex",
    ".exs", ".erl", ".hs", ".ml", ".clj", ".dart", ".r", ".jl",
}
CORPUS_SUFFIXES = SOURCE_SUFFIXES | {
    ".md", ".json", ".yml", ".yaml", ".toml", ".txt", ".cfg", ".ini", ".xml", "",
}

# Loaded by position or by convention rather than imported by a sibling.
POSITIONAL_NAMES = {
    "__init__.py", "__main__.py", "conftest.py", "setup.py", "manage.py",
    "index.js", "index.ts", "index.mjs", "index.cjs", "index.tsx", "index.jsx",
    "main.py", "main.go", "main.rs", "main.ts", "main.js", "app.py", "wsgi.py",
    "asgi.py", "urls.py", "settings.py", "layout.tsx", "page.tsx", "page.jsx",
    "loading.tsx", "error.tsx", "not-found.tsx", "route.ts", "route.js",
    "Dockerfile", "Makefile", "Procfile", "Rakefile", "build.sh", "run.sh",
}
POSITIONAL_SUFFIXES = (
    ".config.js", ".config.ts", ".config.mjs", ".config.cjs", ".d.ts",
    ".test.js", ".test.ts", ".spec.js", ".spec.ts", ".test.tsx", ".spec.tsx",
    ".test.mjs", ".test.cjs", ".spec.mjs", ".spec.cjs",
    "_test.py", "_test.go", "test_.py", "_spec.rb",
)
# Directories whose contents are run by a tool, never imported by a sibling.
RUN_BY_TOOL_DIRS = {
    "test", "tests", "__tests__", "spec", "specs", "eval", "evals", "bench",
    "benchmarks", "scripts", "bin", "tools", "examples", "samples", "fixtures",
}
MAIN_GUARD = re.compile(r"^\s*if\s+__name__\s*==\s*['\"]__main__['\"]", re.M)

TEXT_SNIFF = 4096
CORPUS_FILE_CAP = 512 * 1024
CORPUS_TOTAL_CAP = 96 * 1024 * 1024
STEM_MIN_LEN = 4

# Two shapes count as naming an area. Prose alone does not, and neither does a
# path to a file: only a token that ends in a slash names a directory.
#   directory-tree line     |-- src/          ├── daily/
#   path wrapped as code    `docs/`   **daily/**
# Branch names (`origin/main`), file paths (`src/pages/index.astro`) and
# markdown table rules (`|---|---|`) are rejected by those two conditions.
TREE_LINE_RE = re.compile(r"^\s*(?:\|--|`--|[├└]──|\+--)\s*([A-Za-z0-9_.\-]+)/")
WRAPPED_AREA_RE = re.compile(r"(?:`|\*\*)([A-Za-z0-9_.\-]+)/(?:`|\*\*)")


def looks_like_area(name):
    return (len(name) >= 2 and any(c.isalpha() for c in name)
            and not name.startswith("-"))


def git(repo, *args):
    out = subprocess.run(["git", "-C", str(repo), *args],
                         capture_output=True, text=True, errors="replace")
    if out.returncode != 0:
        raise SystemExit(f"git {' '.join(args)} failed: {out.stderr.strip()}")
    return out.stdout


def tracked_files(repo):
    return [p for p in git(repo, "ls-files", "-z").split("\0") if p]


def ignored_present(repo):
    # No --directory: folding a whole ignored tree into one entry reports
    # 1438 "paths" for a tree that holds 4770 files, and the count is what
    # gets quoted in reports. Enumerating every file costs ~0.04s even with
    # node_modules present.
    raw = git(repo, "ls-files", "--others", "--ignored", "--exclude-standard",
              "-z")
    return [p for p in raw.split("\0") if p]


def read_text(path, cap=CORPUS_FILE_CAP):
    try:
        if path.stat().st_size > cap:
            return None
        if b"\0" in path.read_bytes()[:TEXT_SNIFF]:
            return None
        return path.read_text(encoding="utf-8", errors="replace")
    except OSError:
        return None


def is_generated(rel):
    if any(p in GENERATED_DIRS for p in Path(rel).parts[:-1]):
        return True
    return rel.endswith(GENERATED_SUFFIXES)


def is_positional(rel, repo=None):
    """Loaded by position or run directly, so no sibling will ever import it."""
    name = Path(rel).name
    if (name in POSITIONAL_NAMES or name.startswith(".")
            or name.endswith(POSITIONAL_SUFFIXES)):
        return True
    if any(p in RUN_BY_TOOL_DIRS for p in Path(rel).parts[:-1]):
        return True
    if repo is not None:
        head = read_text(repo / rel)
        if head and (head.startswith("#!") or MAIN_GUARD.search(head[:8192])):
            return True
    return False


def declaration_files(repo):
    found = [n for n in DECLARATION_NAMES if (repo / n).is_file()]
    for sub in DECLARATION_DIRS:
        d = repo / sub
        if d.is_dir():
            for child in sorted(d.iterdir()):
                if child.is_file() and child.suffix in (".md", ".yml", ".yaml"):
                    found.append(f"{sub}/{child.name}")
    return found


def contract_docs(files):
    """Docs that state layout intent, excluding archives and giant log dumps.

    An archived hand-off log quotes paths that no longer exist; treating it as
    a contract produces pure noise.
    """
    out = []
    for rel in files:
        if not rel.endswith((".md", ".yml", ".yaml", ".json", ".toml")):
            continue
        parts = Path(rel).parts
        if any(p in ("archive", "archived", "node_modules") for p in parts):
            continue
        name = Path(rel).name
        is_root_contract = name in DECLARATION_NAMES and "/" not in rel
        is_sub_contract = (rel.split("/")[0] in DECLARATION_DIRS
                           and name in DECLARATION_NAMES)
        if is_root_contract or is_sub_contract:
            out.append(rel)
    return out


def declared_areas(repo, files, areas):
    """Areas the project's own contract docs name, and whether each exists.

    Existence is checked at any depth: a project that declares `notes/life`
    as a sub-area of `notes` is honoured, not reported as missing.
    """
    everywhere = {p for rel in files for p in Path(rel).parts[:-1]}
    # Ignored directories count as present: `run/` is gitignored by design and
    # is still a real directory the docs refer to.
    everywhere |= {p for entry in ignored_present(repo)
                   for p in Path(entry.rstrip("/")).parts[:-1]}
    known = dict(areas)

    def on_disk(area):
        if area in everywhere:
            return True
        p = repo / area
        return p.is_dir() or p.is_file()

    mentions = defaultdict(set)
    for rel in contract_docs(files):
        text = read_text(repo / rel, cap=256 * 1024)
        if not text:
            continue
        for line in text.splitlines():
            found = []
            m = TREE_LINE_RE.match(line)
            if m:
                found.append(m.group(1))
            found.extend(WRAPPED_AREA_RE.findall(line))
            for area in found:
                area = area.strip("/").strip()
                if not looks_like_area(area):
                    continue
                mentions[area].add(rel)

    declared = []
    repo_name = repo.name
    for area, paths in sorted(mentions.items()):
        if area == repo_name:
            continue          # the repository's own name, not a directory
        present = area in everywhere or area in known or on_disk(area)
        if not present and area in GENERATED_DIRS | {"dist", "build", "out", "coverage"}:
            status = "GENERATED"
        elif present:
            status = "OK"
        else:
            status = "ABSENT"
        declared.append({
            "area": area,
            "declared_in": sorted(paths)[:3],
            "declared_count": len(paths),
            "status": status,
            "tracked": known.get(area, 0),
        })
    named = {d["area"] for d in declared}
    undeclared = [(a, n) for a, n in areas
                  if a not in named and not a.startswith(".") and a != "(root)"]
    return declared, undeclared


def unreferenced_sources(repo, files):
    """Source files whose name appears nowhere else in the tracked text.

    One regex pass over the corpus, so cost stays linear in repo size.
    A hit is a candidate for review, never a verdict: dynamic imports,
    config-declared entry points and framework-by-position loading all
    produce legitimate hits.
    """
    corpus, total = {}, 0
    for rel in files:
        if total >= CORPUS_TOTAL_CAP:
            break
        if Path(rel).suffix.lower() not in CORPUS_SUFFIXES:
            continue
        text = read_text(repo / rel)
        if text is None:
            continue
        corpus[rel] = text
        total += len(text)

    candidates = []
    for rel in files:
        if Path(rel).suffix.lower() not in SOURCE_SUFFIXES:
            continue
        if is_positional(rel, repo) or "/" not in rel:
            continue
        stem = Path(rel).stem
        if len(stem) >= STEM_MIN_LEN:
            candidates.append((rel, Path(rel).name, stem))
    if not candidates:
        return []

    tokens = sorted({t for _, n, s in candidates for t in (n, s)},
                    key=len, reverse=True)
    pattern = re.compile("|".join(re.escape(t) for t in tokens))
    totals = Counter()
    for text in corpus.values():
        for m in pattern.finditer(text):
            totals[m.group(0)] += 1

    # A token seen once is the definition itself; the same token in another
    # file is a reference. Counting per-file would call every definition an
    # orphan, because the only hit is the file that defines it.
    return sorted(rel for rel, name, stem in candidates
                  if totals[name] + (totals[stem] if stem != name else 0) <= 1)


def analyse(repo, max_mb, line_len):
    files = tracked_files(repo)
    report = {
        "repo": str(repo),
        "branch": git(repo, "rev-parse", "--abbrev-ref", "HEAD").strip(),
        "tracked": len(files),
        "dirty": bool(git(repo, "status", "--porcelain").strip()),
    }

    areas, exts = Counter(), Counter()
    for rel in files:
        areas[rel.split("/")[0] if "/" in rel else "(root)"] += 1
        exts[Path(rel).suffix.lower() or "(none)"] += 1
    report["areas"] = areas.most_common()
    report["extensions"] = exts.most_common(15)
    report["root_files"] = sorted(r for r in files if "/" not in r)
    report["tracked_generated"] = [r for r in files if is_generated(r)]

    ignored = ignored_present(repo)
    report["ignored_present"] = Counter(
        e.split("/")[0] if "/" in e else e for e in ignored).most_common(20)
    report["ignored_present_total"] = len(ignored)

    big, long_lines = [], []
    for rel in files:
        p = repo / rel
        try:
            size = p.stat().st_size
        except OSError:
            continue
        if size > max_mb * 1048576:
            big.append((rel, round(size / 1048576, 1)))
        if size > 65536 and not is_generated(rel):
            text = read_text(p, cap=size + 1)
            if text:
                longest = max((len(ln) for ln in text.splitlines()), default=0)
                if longest > line_len:
                    long_lines.append((rel, longest, round(size / 1048576, 1)))
    report["oversized_files"] = sorted(big, key=lambda x: -x[1])
    report["long_line_files"] = sorted(long_lines, key=lambda x: -x[1])[:10]

    report["declarations"] = declaration_files(repo)
    declared, undeclared = declared_areas(repo, files, report["areas"])
    report["declared_areas"] = declared
    report["undeclared_areas"] = undeclared
    report["unreferenced_sources"] = unreferenced_sources(repo, files)

    basenames = defaultdict(list)
    for rel in files:
        basenames[Path(rel).name].append(rel)
    report["duplicate_basenames"] = sorted(
        ((k, v) for k, v in basenames.items() if len(v) > 1 and not is_generated(k)),
        key=lambda kv: -len(kv[1]))[:8]
    return report


def render(r):
    L = []
    a = L.append
    a(f"# layout inventory: {r['repo']}")
    a(f"branch={r['branch']} tracked={r['tracked']} uncommitted={'yes' if r['dirty'] else 'no'}")
    a("")
    a("## declarations read (the project's own layout contract lives here)")
    for d in r["declarations"]:
        a(f"  {d}")
    if not r["declarations"]:
        a("  none -- no layout rule written down; report measured facts only")
    a("")
    a("## DRIFT: declared areas vs actual")
    if not r["declared_areas"]:
        a("  no area named in the docs -- nothing to diff against")
    for d in r["declared_areas"]:
        a(f"  {d['status']:<9} {d['area']:<18} "
          f"tracked={d['tracked']:<5} named in {', '.join(d['declared_in'])}")
    if r["undeclared_areas"]:
        a("  -- present but never named in the docs:")
        for area, n in r["undeclared_areas"]:
            a(f"     {area:<18} tracked={n}")
    a("")
    a("## areas by tracked file count")
    for area, n in r["areas"]:
        a(f"  {n:>6}  {area}")
    a("")
    a("## extensions")
    a("  " + ", ".join(f"{e}:{n}" for e, n in r["extensions"]))
    a("")
    a(f"## files at repository root ({len(r['root_files'])})")
    for f in r["root_files"]:
        a(f"  {f}")
    a("")
    a(f"## tracked but generated ({len(r['tracked_generated'])})")
    for f in r["tracked_generated"]:
        a(f"  {f}")
    if not r["tracked_generated"]:
        a("  none")
    a("")
    a(f"## ignored files present on disk ({r['ignored_present_total']}) -- gitignore is working")
    for area, n in r["ignored_present"]:
        a(f"  {n:>6}  {area}")
    if not r["ignored_present"]:
        a("  none")
    a("")
    a("## files over size threshold")
    for f, mb in r["oversized_files"]:
        a(f"  {mb:>7} MB  {f}")
    if not r["oversized_files"]:
        a("  none")
    a("")
    a("## files with very long lines (generated-looking content)")
    for f, longest, mb in r["long_line_files"]:
        a(f"  longest={longest:<7} {mb:>6} MB  {f}")
    if not r["long_line_files"]:
        a("  none")
    a("")
    a(f"## unreferenced source files ({len(r['unreferenced_sources'])}) -- verify before acting")
    for f in r["unreferenced_sources"]:
        a(f"  {f}")
    if not r["unreferenced_sources"]:
        a("  none")
    a("")
    a("## duplicate basenames")
    for name, paths in r["duplicate_basenames"]:
        a(f"  {name}  ({len(paths)}x)")
        for p in paths[:6]:
            a(f"      {p}")
    if not r["duplicate_basenames"]:
        a("  none")
    return "\n".join(L)


def main():
    ap = argparse.ArgumentParser(description="Repository layout inventory (read-only)")
    ap.add_argument("repo", nargs="?", default=".")
    ap.add_argument("--json", action="store_true")
    ap.add_argument("--max-mb", type=float, default=1.0)
    ap.add_argument("--line-len", type=int, default=2000)
    args = ap.parse_args()

    repo = Path(args.repo).resolve()
    if not (repo / ".git").exists():
        raise SystemExit(f"{repo} is not a git repository root")
    report = analyse(repo, args.max_mb, args.line_len)
    print(json.dumps(report, ensure_ascii=False, indent=2) if args.json else render(report))


if __name__ == "__main__":
    main()
