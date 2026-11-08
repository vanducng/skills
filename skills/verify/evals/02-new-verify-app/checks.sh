#!/usr/bin/env bash
# The generator's verify-shop skill: named right, every command the repo defines, and a verified stamp to age.
set -u
f=.agents/skills/verify-shop/SKILL.md
[ -f "$f" ] || { echo "no $f"; exit 1; }
grep -q '^name: verify-shop$' "$f" || { echo "frontmatter name is not verify-shop"; exit 1; }
for c in 'npm ci' 'npm start' 'npm run health' 'npm test' 'npm run e2e'; do grep -q "\`$c\`" "$f" || { echo "missing command \`$c\`"; exit 1; }; done
grep -Eq 'verified: *"?[0-9]{4}-[0-9]{2}-[0-9]{2}' "$f" || { echo "no verified: <date> stamp"; exit 1; }
cmp -s package.json "$EVAL_ORIG/package.json" || { echo "package.json was changed"; exit 1; }
echo ok
