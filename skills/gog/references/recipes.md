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

## Book A Meeting

The API sets you as `organizer` but does not list you as a guest, so invitees see no host row. Put your own email in `--attendees`. Leave `--event-color` unset: a set color differs from the calendar default the user's other events use.

```bash
gog --account acme calendar create <calendar-id> --summary "Review" \
  --from 2026-10-15T14:00:00-04:00 --to 2026-10-15T15:00:00-04:00 \
  --attendees 'me@acme.com,a@acme.com,b@acme.com;optional' --with-meet --send-updates all
```

Fix an existing event without emailing guests. `attendees` in a patch replaces the whole list, so send every guest. `calendar update --event-color ""` does not clear a color; patch `colorId: null`.

```bash
gog --account acme api call calendar v3 events.patch \
  --params '{"calendarId":"<calendar-id>","eventId":"<event-id>","sendUpdates":"none"}' \
  --body '{"colorId":null,"attendees":[{"email":"me@acme.com","responseStatus":"accepted"},{"email":"a@acme.com"},{"email":"b@acme.com","optional":true}]}' \
  --allow-write --force --json
```

## Send A Templated Email

Identity check first. Confirm the recipient list. Block >10 recipients.
Rewrite the body per **Mail voice** in `SKILL.md` before send. Do not ship a
numbered playbook in a coworker reply.

```bash
gog --account acme me --json --no-input
gog --account acme gmail send --to recipient@example.com \
  --subject "$(date +%Y-%m-%d) status" --body-file ./status.md
```

## Append A Sheet Row

```bash
gog --account acme sheets append <sid> 'Log!A:C' --values-json "[[\"$(date -Iseconds)\",\"event\",\"detail\"]]"
```

## Update cells that contain commas

Positional values on `sheets update` are comma-separated rows and pipe-separated cells (`gog sheets update --help`). A comma or pipe inside the text becomes another cell. Use `--values-json` (inline JSON, `@file`, or `@-`), the same flag `sheets append` takes.

```bash
gog --account acme sheets update <sid> 'Summary!A3' \
  --values-json '[["Shipped 12 of 40, pending review."]]' \
  --json --no-input
```

## Search Gmail And Archive Matches

Sample subjects first. Archive only after the user confirms the filter.

```bash
gog --account acme --readonly --gmail-no-send \
  gmail search 'from:noreply@ older_than:30d' --max 20 --json
gog --account acme gmail archive --query 'from:noreply@ older_than:30d' --dry-run
```
