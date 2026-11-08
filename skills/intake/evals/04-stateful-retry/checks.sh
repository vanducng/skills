#!/usr/bin/env bash
# A rule about duplicate and retried events names the statechart lens; it is still a bug fix, and the code is left alone.
. "$(dirname "$0")/../common-checks.sh"
type_is 'bug[- ]?fix'
grep -Eq '^lenses: *\[?[^]]*statechart' "$spec" || { echo "no statechart lens in the frontmatter of $spec"; exit 1; }
diff -q src/webhook.js "$EVAL_ORIG/src/webhook.js" >/dev/null || { echo "the code was changed"; exit 1; }
echo ok
