#!/bin/sh
# Not ready: it is 20 s, far too quiet, has no music bed and no thumbnail. The reply must say so and name the loudness and the thumbnail.
. "$(dirname "$0")/../common.sh"
out=$(tr 'A-Z' 'a-z' < "$EVAL_OUTPUT")
printf '%s' "$out" | grep -q 'ready to upload' && ! printf '%s' "$out" | grep -Eq "not (yet )?ready|isn't ready|is not ready" && { echo "called it ready"; exit 1; }
printf '%s' "$out" | grep -Eq 'lufs|loud|quiet|volume' || { echo "did not flag the loudness"; exit 1; }
printf '%s' "$out" | grep -q 'thumbnail' || { echo "did not flag the missing thumbnail"; exit 1; }
printf '%s' "$out" | grep -Eq 'music' || { echo "did not flag the missing music bed"; exit 1; }
cmp -s tw26-d02-01-market.mp4 "$EVAL_ORIG/tw26-d02-01-market.mp4" || { echo "changed the render"; exit 1; }
echo ok
