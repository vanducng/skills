# Sourced by checks.sh: lint message.md as a person reads it in Grok Bot. Each failure names its rule.
set -u
msg=${1:-message.md}
[ -s "$msg" ] || { echo "no $msg written"; exit 1; }
if grep -Eq '(^|[[:space:](`])(~/|/(Users|home|Volumes|private|tmp|var|opt|srv)/)' "$msg"; then
  echo "a local path the person cannot open: $(grep -Eo '(~/|/(Users|home|Volumes|private|tmp|var|opt|srv)/)[^ )`]*' "$msg" | head -1)"; exit 1
fi
if grep -Eq '^[[:space:]]*\|?[[:space:]]*:?-{3,}:?[[:space:]]*\|' "$msg"; then echo "a markdown table (render unverified)"; exit 1; fi
if grep -Eq '^[[:space:]]{2,}([-*+]|[0-9]+\.)[[:space:]]' "$msg"; then echo "a nested list (render unverified)"; exit 1; fi
if grep -Eiq '<(details|summary|br|table|div|span)[ />]' "$msg"; then echo "raw HTML"; exit 1; fi
# Decision cards: a bold "Decision N:" title line ending in one question mark, 2-4 lettered options from A, one recommendation.
cards() { grep -Ec '^\*\*Decision [0-9]+: [^?]*\?\*\*$' "$msg"; }
card_ok() {
  awk '
    /^\*\*Decision [0-9]+: / { if (n) check(); n=1; opts=""; rec=0; next }
    n && /^[A-D]\. / { opts = opts substr($0,1,1); next }
    n && /^Recommendation: [A-D]([^A-Za-z]|$)/ { rec++; r=substr($0,17,1); next }
    END { if (n) check(); exit bad }
    function check() {
      if (opts !~ /^(AB|ABC|ABCD)$/) { print "card options are \"" opts "\", want A, B[, C, D]"; bad=1 }
      if (rec != 1) { print "card has " rec " Recommendation lines, want 1"; bad=1 }
      else if (index(opts, r) == 0) { print "recommendation " r " is not an option"; bad=1 }
    }' "$msg"
}
