# Jira Ticket Follow-up

Use this workflow for evidence updates, structured comments, native mentions, and board-column moves. Assume Jira authentication is already exported as required by `SKILL.md`.

- [Structured Evidence Comment](#structured-evidence-comment)
- [Move by Board Column](#move-by-board-column)

## Structured Evidence Comment

1. Re-read the issue and draft the shortest result-first update supported by current evidence.
2. Show the complete comment and get approval before posting.
3. Use REST v3 ADF when the comment needs native bullets, a JSON/code block, or a real Jira mention.
4. Re-read the stored comment by ID and verify its structured nodes.

Native mentions require the target account ID. Plain text such as `@Display Name` may render as text without notifying the user.

```bash
issue_key='PROJ-123'
outcome='The requested behavior is live and verified.'
code_label='Current configuration:'
json_evidence='<approved JSON>'

issue_json="$(jira issue view "$issue_key" --raw)"
reporter_id="$(jq -er '.fields.reporter.accountId' <<< "$issue_json")"
reporter_name="$(jq -er '.fields.reporter.displayName' <<< "$issue_json")"

comment_response="$(jq -n \
  --arg outcome "$outcome" \
  --arg label "$code_label" \
  --arg json "$json_evidence" \
  --arg mentionId "$reporter_id" \
  --arg mentionText "@$reporter_name" \
  '{body:{type:"doc",version:1,content:[
    {type:"bulletList",content:[
      {type:"listItem",content:[{type:"paragraph",content:[{type:"text",text:$outcome}]}]},
      {type:"listItem",content:[{type:"paragraph",content:[{type:"text",text:$label}]}]}
    ]},
    {type:"codeBlock",attrs:{language:"json"},content:[{type:"text",text:$json}]},
    {type:"paragraph",content:[
      {type:"text",text:"FYI "},
      {type:"mention",attrs:{id:$mentionId,text:$mentionText}}
    ]}
  ]}}' | curl -fsS -X POST "$JIRA_BASE_URL/rest/api/3/issue/$issue_key/comment" \
    -u "$JIRA_USER_EMAIL:$JIRA_API_TOKEN" \
    -H 'Accept: application/json' \
    -H 'Content-Type: application/json' \
    --data @-)"

comment_id="$(jq -er '.id' <<< "$comment_response")"
curl -fsS "$JIRA_BASE_URL/rest/api/3/issue/$issue_key/comment/$comment_id" \
  -u "$JIRA_USER_EMAIL:$JIRA_API_TOKEN" -H 'Accept: application/json' | \
  jq -e --arg json "$json_evidence" --arg mentionId "$reporter_id" '
    {
      id,
      codeBlockStored: any(..; .type? == "codeBlock" and any(.content[]?; .text? == $json)),
      mentionStored: any(..; .type? == "mention" and .attrs.id == $mentionId)
    }
    | select(.codeBlockStored and .mentionStored)'
```

Mention the reporter only when requested or useful. For another person, resolve that user's Jira account ID rather than substituting a display name.

## Move by Board Column

A board column can contain one or more workflow statuses, and its label can differ from every status name. Resolve the mapping before transitioning.

```bash
issue_key='PROJ-123'
board_name='<Default board from instance rules>'
column_name='<approved target column>'

boards="$(curl -fsS -G "$JIRA_BASE_URL/rest/agile/1.0/board" \
  -u "$JIRA_USER_EMAIL:$JIRA_API_TOKEN" \
  -H 'Accept: application/json' \
  --data-urlencode "name=$board_name")"

board_id="$(jq -er --arg name "$board_name" '[
  .values[] | select((.name | ascii_downcase) == ($name | ascii_downcase)) | .id
] | if length == 1 then .[0] else error("Expected exactly one matching board") end' <<< "$boards")"

assert_issue_on_board() {
  curl -fsS -G "$JIRA_BASE_URL/rest/agile/1.0/board/$board_id/issue" \
    -u "$JIRA_USER_EMAIL:$JIRA_API_TOKEN" -H 'Accept: application/json' \
    --data-urlencode "jql=key=$issue_key" --data-urlencode 'maxResults=1' | \
    jq -e --arg key "$issue_key" '.total == 1 and .issues[0].key == $key' >/dev/null
}
assert_issue_on_board

board_config="$(curl -fsS "$JIRA_BASE_URL/rest/agile/1.0/board/$board_id/configuration" \
  -u "$JIRA_USER_EMAIL:$JIRA_API_TOKEN" -H 'Accept: application/json')"
transitions="$(curl -fsS "$JIRA_BASE_URL/rest/api/3/issue/$issue_key/transitions" \
  -u "$JIRA_USER_EMAIL:$JIRA_API_TOKEN" -H 'Accept: application/json')"

target_status_ids="$(jq -ce --arg column "$column_name" '[
  .columnConfig.columns[]
  | select((.name | ascii_downcase) == ($column | ascii_downcase))
] | if length == 1 then [.[0].statuses[].id] else error("Expected exactly one matching board column") end' <<< "$board_config")"

transition="$(jq -ec --argjson ids "$target_status_ids" '[
  .transitions[] | select(.to.id as $id | $ids | index($id))
] | if length == 1 then .[0] else error("Expected exactly one direct transition to the board column") end' <<< "$transitions")"
```

Show `column_name`, `transition.to.name`, and `transition.name` before the write. If several columns or direct transitions match the user's intent, or no direct transition reaches the target, stop and ask instead of inventing a path.

```bash
transition_id="$(jq -er '.id' <<< "$transition")"
jq -n --arg id "$transition_id" '{transition:{id:$id}}' | \
  curl -fsS -X POST "$JIRA_BASE_URL/rest/api/3/issue/$issue_key/transitions" \
    -u "$JIRA_USER_EMAIL:$JIRA_API_TOKEN" \
    -H 'Accept: application/json' \
    -H 'Content-Type: application/json' \
    --data @-

assert_issue_on_board
jira issue view "$issue_key" --raw | jq -e --argjson ids "$target_status_ids" '
  .fields.status.id as $statusId
  | {
      status: .fields.status.name,
      statusId: $statusId,
      inTargetColumn: ($ids | index($statusId) != null)
    }
  | select(.inTargetColumn)'
```
