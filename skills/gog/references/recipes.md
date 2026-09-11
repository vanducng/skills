# gog Recipes

```bash
export GOG_HOME="$HOME/.config/vd/gog"
```

`--user person` needs a valid refresh token (`gog --account <resolved> auth list --check`).

Prompt: `vd:gog --account acme --user person gmail ...` → CLI `gog --account acme`.

## Daily Inbox Triage

```bash
# vd:gog --account acme --user person gmail
gog --account acme --readonly --gmail-no-send \
  gmail search 'is:unread newer_than:1d category:primary' --max 50 --json --wrap-untrusted
```

## Cross-Account Inbox Summary

Fan out only when the user asked. Label each block. Skip `--user sa`.

```bash
for alias in acme beta; do
  echo "== $alias person =="
  gog --account "$alias" --readonly --gmail-no-send \
    gmail search 'is:unread newer_than:1d' --max 20 --json --wrap-untrusted
done
```

## Today's Agenda

```bash
gog --account acme --readonly calendar events --today --json --wrap-untrusted \
  | jq -r '.events[]? | "- \(.start.dateTime // .start.date) - \(.summary)"'
```

## Send A Templated Email

Identity check first. Confirm the recipient list. Block >10 recipients.

```bash
gog --account acme me --json --no-input
gog --account acme gmail send --to recipient@example.com \
  --subject "$(date +%Y-%m-%d) status" --body-file ./status.md
```

## Append A Sheet Row

```bash
gog --account acme sheets append <sid> 'Log!A:C' --values-json "[[\"$(date -Iseconds)\",\"event\",\"detail\"]]"
```

## Search Gmail And Archive Matches

Sample subjects first. Archive only after the user confirms the filter.

```bash
gog --account acme --readonly --gmail-no-send \
  gmail search 'from:noreply@ older_than:30d' --max 20 --json
gog --account acme gmail archive --query 'from:noreply@ older_than:30d' --dry-run
```
