#!/bin/sh
# The field map flags the missing field and the field with two candidate columns, before anything is built.
. "$(dirname "$0")/../common.sh"
built=$(new_files | grep -Ei '\.(html?|png|svg|jpe?g|ipynb|ya?ml|json)$')
[ -z "$built" ] || { echo "built something before the field map: $built"; exit 1; }
row_with channel 'missing|not (found|present|available)|absent|no column' || { echo "no field-map row marks the sales channel missing"; exit 1; }
row_with created_at order_date || { echo "no field-map row names both candidate date columns (created_at, order_date)"; exit 1; }
row_with created_at order_date 'variant|ambiguous|two candidates|choose|pick|which' || { echo "the date row does not flag the choice between the two columns"; exit 1; }
echo ok
