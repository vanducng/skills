#!/bin/sh
# A plain conversion is not a travel video: the GIF, and no edit list, thumbnail or render.
. "$(dirname "$0")/../common.sh"
[ -s clip.gif ] || { echo "no clip.gif"; exit 1; }
extra=$(new_files | grep -v '^clip\.gif$')
[ -z "$extra" ] || { echo "made more than the GIF: $extra"; exit 1; }
echo ok
