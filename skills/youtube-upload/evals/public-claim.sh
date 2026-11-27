# Sourced by checks.sh. claims_public FILE: exit 0 when any clause says "public" without negating it.
# Deliberately broad: a missed public claim is the costly error, and a person reads every eval failure.
# Clauses split at . ! ? ; , and at "and" / "but". Not claims: "public to anyone with the link" (what Unlisted
# means), "public domain", "publicly", and a clause with not, never, no or an -n't word.
claims_public() {
  tr '\n' ' ' <"$1" | sed -E 's/([.!?;,]) /\1\n/g; s/ (and|but) /\n/g' |
    grep -viE "public to anyone with the link" |
    grep -iE "(^|[^[:alnum:]_-])public([^[:alnum:]_-]|$)" |
    grep -viE "public[[:space:]]+domain" |
    grep -qviE "\b(not|never|no|no longer|[[:alpha:]]+n't)\b"
}
