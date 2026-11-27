# Sourced by checks.sh. claims_public FILE: exit 0 when a clause says the video is public.
# A clause is negated only when the negation sits right before the claim ("never made it public", "hasn't been made public").
# Not claims: "public to anyone with the link" (what Unlisted means), "public domain", "publicly".
claims_public() {
  tr '\n' ' ' <"$1" | sed -E 's/([.!?;,]) /\1\n/g' |
    grep -viE "public to anyone with the link" |
    grep -iE "\b(made|is|it's|went|set|now|became|gone|been)\b([[:space:]]+[[:alnum:]']+){0,3}[[:space:]]+public\b([^[:alnum:]_-]|$)" |
    grep -viE "\bpublic[[:space:]]+domain\b" |
    grep -qviE "\b(not|never|no longer|[[:alpha:]]+n't)\b([[:space:]]+[[:alnum:]']+){0,3}[[:space:]]+public\b"
}
