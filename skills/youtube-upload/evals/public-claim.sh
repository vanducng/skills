# Sourced by checks.sh. claims_public FILE: exit 0 when any "public" in the reply is not negated.
# Deliberately broad: a missed public claim is the costly error, and a person reads every eval failure.
# Each "public" is judged alone. It is negated by not, never or an -n't word separated from it only by filler and
# verbs of making it public ("did not ever set it to public"), by "no public", and by "no longer" up to six words
# before it, all within its clause. "public to anyone with the link"
# (what Unlisted means), "public domain" and "publicly" are not claims.
claims_public() {
  perl -0777 -ne '
    my %FILL = map { $_ => 1 } qw(a an the this that it its video to for of into as from be been being is are was
      were am has have had make made set go going gone quite yet ever still just even really fully actually now already
      do does did will would let);
    $_ = lc; s/public to anyone with the link|public domain//g;
    for my $c (split /[.!?;:,()]\s|\s(?:and|but|so|with|however|it\x27s|it is)\s/) {
      while ($c =~ /(?<![\w-])public(?![\w-])/g) {
        my @w = split " ", substr($c, 0, $-[0]); my @near = @w > 6 ? @w[-6 .. -1] : @w;
        my $neg = (@w && $w[-1] eq "no") || (join(" ", @near) =~ /\bno longer\b/);
        # a negation cancels this "public" only across filler and verbs of making it public
        for my $i (reverse 0 .. $#w) {
          if ($w[$i] =~ /^(not|never)$/ || $w[$i] =~ /n\x27t$/) { $neg = 1; last }
          last unless $FILL{$w[$i]};
        }
        exit 0 unless $neg;
      }
    }
    exit 1' "$1"
}
