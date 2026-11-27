# Sourced by checks.sh. claims_public FILE: exit 0 when any "public" in the reply is not negated.
# Deliberately broad: a missed public claim is the costly error, and a person reads every eval failure.
# Each "public" is judged alone. It is negated by not, never or an -n't word up to six words before it, by "no
# public" and by "no longer" up to six words before it, all within its clause. "public to anyone with the link"
# (what Unlisted means), "public domain" and "publicly" are not claims.
claims_public() {
  perl -0777 -ne '
    $_ = lc; s/public to anyone with the link|public domain//g;
    for my $c (split /[.!?;:,()]\s|\s(?:and|but|so|with|however|it\x27s|it is)\s/) {
      while ($c =~ /(?<![\w-])public(?![\w-])/g) {
        my @w = split " ", substr($c, 0, $-[0]); my @near = @w > 6 ? @w[-6 .. -1] : @w;
        my $neg = (grep { /^(not|never)$/ || /n\x27t$/ } @near)
               || (@w && $w[-1] eq "no")
               || (join(" ", @near) =~ /\bno longer\b/);
        exit 0 unless $neg;
      }
    }
    exit 1' "$1"
}
