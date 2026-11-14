#!/usr/bin/env bash
# Link every skill in this repository into the agent skill directories.
#
#   ./scripts/link-skills.sh            create or refresh links
#   ./scripts/link-skills.sh --check    verify links and SKILL.md validity only
#   ./scripts/link-skills.sh --dry-run  print what would change
#
# A real directory at a target path is never replaced: the script reports it and
# exits non-zero so a manual decision is made first.
set -uo pipefail

REPO=$(CDPATH= cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd)
SKILLS_DIR="$REPO/skills"
DSH_DIR="${DSH_SKILLS_DIR:-$HOME/.dsh/skills}"
CC_DIR="${CC_SKILLS_DIR:-$HOME/.cc-switch/skills}"

MODE=link
for arg in "$@"; do
    case "$arg" in
        --check)   MODE=check ;;
        --dry-run) MODE=dry ;;
        -h|--help) sed -n '2,12p' "$0" | sed 's/^# \{0,1\}//'; exit 0 ;;
        *) printf 'unknown option: %s\n' "$arg" >&2; exit 1 ;;
    esac
done

die() { printf 'error: %s\n' "$1" >&2; exit 1; }

[ -d "$SKILLS_DIR" ] || die "no skills directory at $SKILLS_DIR"

# Validate frontmatter of every skill; returns non-zero on any problem.
validate() {
    python3 - "$SKILLS_DIR" <<'PY'
import os, re, sys
root = sys.argv[1]
bad = 0
for name in sorted(os.listdir(root)):
    d = os.path.join(root, name)
    if not os.path.isdir(d):
        continue
    p = os.path.join(d, 'SKILL.md')
    if not os.path.isfile(p):
        print(f'  {name}: missing SKILL.md'); bad += 1; continue
    text = open(p, encoding='utf-8').read()
    m = re.match(r'^---\n(.*?)\n---\n', text, re.S)
    if not m:
        print(f'  {name}: missing frontmatter'); bad += 1; continue
    fm = m.group(1)
    fn = re.search(r'^name:\s*(.+)$', fm, re.M)
    problems = []
    if not fn:
        problems.append('no name field')
    elif fn.group(1).strip().strip('"\'') != name:
        problems.append(f'name "{fn.group(1).strip()}" != directory "{name}"')
    if not re.search(r'^description:', fm, re.M):
        problems.append('no description field')
    if problems:
        print(f'  {name}: ' + '; '.join(problems)); bad += 1
    else:
        print(f'  {name}: ok')
sys.exit(1 if bad else 0)
PY
}

check_link() {
    local target=$1 name=$2 label=$3
    if [ -L "$target" ]; then
        local actual
        actual=$(readlink -f "$target")
        if [ "$actual" = "$(readlink -f "$SKILLS_DIR/$name")" ]; then
            echo "  ok   $label/$name"
        else
            echo "  BAD  $label/$name -> $actual"; return 1
        fi
    elif [ -d "$target" ]; then
        echo "  REAL $label/$name is a real directory (not a link)"; return 1
    else
        echo "  MISS $label/$name"; return 1
    fi
}

if [ "$MODE" = check ]; then
    echo "Validating SKILL.md files:"
    validate || exit 1
    echo
    echo "Checking links:"
    rc=0
    for d in "$SKILLS_DIR"/*/; do
        name=$(basename "$d")
        check_link "$DSH_DIR/$name" "$name" "dsh" || rc=1
        check_link "$CC_DIR/$name" "$name" "cc-switch" || rc=1
    done
    exit $rc
fi

mkdir -p "$DSH_DIR" "$CC_DIR" || die "cannot create skill directories"

changed=0
failed=0
for d in "$SKILLS_DIR"/*/; do
    name=$(basename "$d")
    for pair in "$DSH_DIR:dsh" "$CC_DIR:cc-switch"; do
        base=${pair%:*}; label=${pair##*:}
        target="$base/$name"
        want=$(readlink -f "$d")
        if [ -L "$target" ] && [ "$(readlink -f "$target")" = "$want" ]; then
            continue
        fi
        if [ -e "$target" ] && [ ! -L "$target" ]; then
            printf '  SKIP %s/%s: a real directory already exists; move it away first\n' "$label" "$name" >&2
            failed=$((failed + 1)); continue
        fi
        if [ "$MODE" = dry ]; then
            printf '  would link %s/%s -> %s\n' "$label" "$name" "$want"
        else
            ln -sfn "$want" "$target" || { failed=$((failed + 1)); continue; }
            printf '  link %s/%s -> %s\n' "$label" "$name" "$want"
        fi
        changed=$((changed + 1))
    done
done

[ "$MODE" = dry ] && { printf '\ndry run: %d link(s) would change\n' "$changed"; exit 0; }
printf '\n%d link(s) updated, %d skipped\n' "$changed" "$failed"
[ "$failed" -eq 0 ] || exit 1
