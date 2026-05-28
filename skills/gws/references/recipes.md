# gws Recipes

Common workflows for `me@vanducng.dev`. Load this reference only for multi-step Google Workspace tasks.

## Daily Inbox Triage

```bash
gws gmail messages list --account me@vanducng.dev --params '{"q":"is:unread newer_than:1d category:primary","maxResults":50}' \
  | jq -r '.messages[].id' \
  | xargs -I {} gws gmail messages get --account me@vanducng.dev --params '{"id":"{}","format":"metadata","metadataHeaders":["From","Subject","Date"]}'
```

## Backup A Drive Folder Locally

```bash
FOLDER_ID=...
mkdir -p ./backup
gws drive files list --account me@vanducng.dev --params "{\"q\":\"'$FOLDER_ID' in parents and trashed=false\",\"pageSize\":1000}" \
  | jq -r '.files[] | [.id, .name] | @tsv' \
  | while IFS=$'\t' read -r id name; do
      gws drive +download --account me@vanducng.dev --file-id "$id" --out "./backup/$name"
    done
```

## Send A Templated Email

Read the recipient list and rendered body before sending. Ask for confirmation when there are more than 10 recipients.

```bash
gws gmail +send \
  --account me@vanducng.dev \
  --to recipient@example.com \
  --subject "$(date +%Y-%m-%d) status" \
  --body "$(cat ./status.md)"
```

## Today's Agenda To Markdown

```bash
gws calendar +agenda --account me@vanducng.dev --timezone Asia/Ho_Chi_Minh \
  | jq -r '.events[] | "- \(.start.dateTime // .start.date) - \(.summary)"' \
  > today.md
```

## Append A Row To A Sheet

```bash
gws sheets +append \
  --account me@vanducng.dev \
  --spreadsheet-id <ID> \
  --range "Log!A:C" \
  --values '[["'"$(date -Iseconds)"'","event","detail"]]'
```

## Find Large Drive Files

```bash
gws drive files list --account me@vanducng.dev --params '{"pageSize":1000,"orderBy":"quotaBytesUsed desc","fields":"files(id,name,quotaBytesUsed,mimeType)"}' \
  | jq -r '.files[] | select(.quotaBytesUsed|tonumber > 100000000) | "\(.quotaBytesUsed)\t\(.name)\t\(.id)"'
```

## Search Gmail And Archive Matches

Read the message count and sample subjects first. Archive only after the user confirms the filter is correct.

```bash
gws gmail messages list --account me@vanducng.dev --params '{"q":"from:noreply@ older_than:30d"}' \
  | jq -r '.messages[].id' \
  | xargs -I {} gws gmail messages modify --account me@vanducng.dev --params '{"id":"{}"}' --json '{"removeLabelIds":["INBOX"]}'
```
