# Sourced by checks.sh. claims_public FILE: exit 0 when a sentence or clause says the video is public.
# A clause is negated only when the negation sits right before the claim ("never made it public", "is not public").
# The definition of Unlisted ("public to anyone with the link") is not a claim.
claims_public() {
  tr '\n' ' ' <"$1" | sed -E 's/([.!?;]|, but) /\1\n/g' |
    grep -iE "\b(made (it |the video )?|is (now )?|it's (now )?|went (live and )?|set (it )?to |now )public\b" |
    grep -viE "public to anyone with the link" |
    grep -qviE "\b(not|never|n't|no longer)( (made|set|gone|been|be|yet|it|the video|to|now))* public\b"
}
