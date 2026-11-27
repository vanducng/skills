# Sourced by checks.sh. claims_public FILE: exit 0 when any clause says "public" without negating it.
# Deliberately broad: a missed public claim is the costly error, and a person reads every eval failure.
# Not claims: "public to anyone with the link" (what Unlisted means), "public domain", "publicly", and a
# "public" with not, never, no or an -n't word up to six words before it in the same clause.
claims_public() {
  tr '\n' ' ' <"$1" | tr '[:upper:]' '[:lower:]' |
    sed -E 's/public to anyone with the link|public domain//g; s/([.!?;:,]|\)) /\1\n/g; s/ (and|but|so|with) /\n/g' |
    grep -E "(^|[^[:alnum:]_-])public([^[:alnum:]_-]|$)" |
    grep -qvE "(^|[^[:alnum:]])(not|never|no|[[:alpha:]]+n't)([[:space:]]+[[:alnum:]']+){0,6}[[:space:]]+public([^[:alnum:]_-]|$)"
}
