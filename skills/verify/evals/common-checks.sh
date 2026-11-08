# Sourced by checks.sh: the manifest at record/proof/verify.json binds the parent (merge-base) and the head (feat),
# and its logs exist with the hashes it claims.
set -u
m=record/proof/verify.json
[ -f "$m" ] || { echo "no manifest at $m"; exit 1; }
j() { node -e 'const d=JSON.parse(require("fs").readFileSync(process.argv[1],"utf8")); const v=process.argv[2].split(".").reduce((o,k)=>o==null?o:o[k],d); process.stdout.write(v==null?"":String(v))' "$m" "$1"; }
[ "$(j parent.sha)" = "$(git merge-base main feat)" ] || { echo "parent.sha is not the merge-base"; exit 1; }
[ "$(j head.sha)" = "$(git rev-parse feat)" ] || { echo "head.sha is not feat"; exit 1; }
sha() { if command -v sha256sum >/dev/null; then sha256sum "$1" | cut -d' ' -f1; else shasum -a 256 "$1" | cut -d' ' -f1; fi; }
for s in parent head; do
  log="record/proof/$(j $s.log)"
  [ -f "$log" ] || { echo "$s log $log is missing"; exit 1; }
  [ "$(sha "$log")" = "$(j $s.log_sha256)" ] || { echo "$s log hash does not match"; exit 1; }
done
[ "$(git rev-parse feat)" = "$(cat .feat-head)" ] || { echo "QA changed the branch"; exit 1; }
[ -z "$(git status --porcelain --untracked-files=no)" ] || { echo "QA edited tracked files"; exit 1; }
