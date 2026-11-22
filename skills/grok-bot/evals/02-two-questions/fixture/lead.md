From the lead, for the person:

Two things need their call today.

First, the nightly backup job failed twice this week on the 2 TB volume. We can move it to a bigger runner (costs about 40 USD a month more), split the backup into two jobs, or keep it and retry on failure. I'd split it: no cost and it halves the window.

Second, the reviewer flagged that our staging site is still on the old domain. Should we redirect the old domain to the new one, keep both for a month and then redirect, or leave the old one as is? I'd keep both for a month, since two partners still link the old one.

Status otherwise: all three build slices green, nothing else blocked. Dashboard: https://ci.example.com/team/overview
