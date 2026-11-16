#!/usr/bin/env bash
# Build the two fixture repos used by test-prompts.json.
# Usage: make-fixtures.sh <output-dir>
# Each fixture isolates one judgement call, so the right answer is checkable.
set -euo pipefail

OUT="${1:?usage: make-fixtures.sh <output-dir>}"
mkdir -p "$OUT"

# ---------------------------------------------------------------- fixture A
# A root module referenced by a relative path, and a check that runs it.
A="$OUT/fixture-move"
rm -rf "$A"
mkdir -p "$A/src"
cd "$A"
git init -q
git config user.email t@example.com
git config user.name test

cat > AGENTS.md <<'EOF'
# Fixture A

Layout:

```
|-- src/
|-- scripts/
```

- `src/` holds application code.
- `scripts/` holds one-off maintenance scripts, not imported by anything.
EOF

cat > src/app.js <<'EOF'
const { clean } = require("../tidy");

console.log(clean());
EOF

cat > tidy.js <<'EOF'
exports.clean = () => "cleaned";
EOF

cat > package.json <<'EOF'
{
  "name": "fixture-move",
  "scripts": {
    "test": "node src/app.js | grep -q cleaned"
  }
}
EOF

cat > README.md <<'EOF'
Run `npm test`. The cleanup helper lives in `tidy.js`.
EOF

git add -A
git commit -qm "fixture A"

# ---------------------------------------------------------------- fixture B
# A tracked build artifact, a declared-but-absent area, and an undeclared area.
B="$OUT/fixture-artifacts"
rm -rf "$B"
mkdir -p "$B/app" "$B/lib" "$B/build"
cd "$B"
git init -q
git config user.email t@example.com
git config user.name test

cat > AGENTS.md <<'EOF'
# Fixture B

Directories:

|-- app/
|-- lib/
|-- tests/
EOF

cat > app/main.js <<'EOF'
const { helper } = require("../lib/helper");
console.log(helper());
EOF

cat > lib/helper.js <<'EOF'
exports.helper = () => "ok";
EOF

printf 'x\n' > build/bundle.js
printf 'PYC\n' > lib/helper.pyc
printf 'stray\n' > scratch.js
printf 'node_modules/\n' > .gitignore

git add -A -f
git commit -qm "fixture B"
