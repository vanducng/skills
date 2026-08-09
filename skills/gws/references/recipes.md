# gws Recipes

Multi-step workflows. Every command needs the account's config dir; set it once per shell block:

```bash
export GOOGLE_WORKSPACE_CLI_CONFIG_DIR="$HOME/.config/vd/gws/<alias>"
```

## Daily Inbox Triage

```bash
gws gmail +triage
# or raw, for custom filters:
gws gmail users messages list --params '{"userId":"me","q":"is:unread newer_than:1d category:primary","maxResults":50}' \
  | jq -r '.messages[].id' \
  | xargs -I {} gws gmail users messages get --params '{"userId":"me","id":"{}","format":"metadata","metadataHeaders":["From","Subject","Date"]}'
```

## Cross-Account Inbox Summary

Reads may fan out across accounts when the user explicitly asks; label each result with its account.

```bash
for alias in $(ls ~/.config/vd/gws-accounts/ | sed 's/\.gws-account\.md//'); do
  echo "== $alias =="
  GOOGLE_WORKSPACE_CLI_CONFIG_DIR="$HOME/.config/vd/gws/$alias" gws gmail +triage
done
```

## Backup A Drive Folder Locally

```bash
FOLDER_ID=...
mkdir -p ./backup
gws drive files list --params "{\"q\":\"'$FOLDER_ID' in parents and trashed=false\",\"pageSize\":1000}" \
  | jq -r '.files[] | [.id, .name] | @tsv' \
  | while IFS=$'\t' read -r id name; do
      gws drive files get --params "{\"fileId\":\"$id\",\"alt\":\"media\"}" --output "./backup/$name"
    done
```

## Send A Templated Email

Run the identity check first; read the recipient list and rendered body before sending. Ask for confirmation when there are more than 10 recipients.

```bash
gws gmail users getProfile --params '{"userId":"me"}' | jq -r '.emailAddress'
gws gmail +send --to recipient@example.com --subject "$(date +%Y-%m-%d) status" --body "$(cat ./status.md)"
```

## Today's Agenda To Markdown

```bash
gws calendar +agenda --format json \
  | jq -r '.events[]? | "- \(.start.dateTime // .start.date) - \(.summary)"' > today.md
```

## Append A Row To A Sheet

```bash
gws sheets +append --help   # confirm current flags, then:
gws sheets spreadsheets values append \
  --params '{"spreadsheetId":"<ID>","range":"Log!A:C","valueInputOption":"USER_ENTERED"}' \
  --json '{"values":[["'"$(date -Iseconds)"'","event","detail"]]}'
```

## Find Large Drive Files

```bash
gws drive files list --params '{"pageSize":1000,"orderBy":"quotaBytesUsed desc","fields":"files(id,name,quotaBytesUsed,mimeType)"}' \
  | jq -r '.files[] | select(.quotaBytesUsed|tonumber > 100000000) | "\(.quotaBytesUsed)\t\(.name)\t\(.id)"'
```

## Search Gmail And Archive Matches

Read the message count and sample subjects first. Archive only after the user confirms the filter is correct.

```bash
gws gmail users messages list --params '{"userId":"me","q":"from:noreply@ older_than:30d"}' \
  | jq -r '.messages[].id' \
  | xargs -I {} gws gmail users messages modify --params '{"userId":"me","id":"{}"}' --json '{"removeLabelIds":["INBOX"]}'
```
