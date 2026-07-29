# Inline Images in Jira Comments

Use this workflow only after loading the instance rules, exporting authentication, showing the complete comment, and getting approval for the attachment and comment writes.

| Need | Method |
| --- | --- |
| Public image URL | `jira issue comment add` with Markdown image syntax |
| Local image and simple comment | `jira issue comment add --image` |
| Local image inside structured ADF | Upload attachment, resolve media UUID, then REST v3 `mediaSingle` |

## Public Image URL

`jira-cli` converts Markdown image syntax to Jira markup. The URL must remain reachable by Jira users.

```bash
jira issue comment add PROJ-123 '![Architecture](https://example.com/architecture.png)'
```

Do not use this for private or short-lived URLs.

## Local Image

This is the default local-file workflow. Repeat `--image` for multiple images. The fork uploads each file and renders Jira's returned attachment filename inline.

```bash
issue_key='PROJ-123'
image_path='/path/to/architecture.png'
jira issue comment add "$issue_key" "Implementation flow:" --image "$image_path"

attachment_name="$(basename "$image_path")"
curl -fsS "$JIRA_BASE_URL/rest/api/2/issue/$issue_key/comment?orderBy=-created&maxResults=1" \
  -u "$JIRA_USER_EMAIL:$JIRA_API_TOKEN" \
  -H 'Accept: application/json' | \
  jq -e --arg name "$attachment_name" '.comments[0].body | contains("!" + $name + "|thumbnail!")'
```

If the CLI reports a comment failure after upload, preserve the listed attachment IDs for review or cleanup.

## Local Image: Structured ADF

Use this only when the same comment needs ADF-only features such as native mentions or structured nodes. Jira's attachment content endpoint redirects to a Media Services URL whose path contains the UUID required by an ADF `media` node. This works on Jira Cloud, but Atlassian does not document the redirect path as a stable identifier contract.

Upload the attachment manually, then provide its dimensions and resolve the UUID without printing the signed redirect URL:

```bash
issue_key='PROJ-123'
image_path='/path/to/architecture.png'
inline_name="architecture-$(date -u +%Y%m%dT%H%M%SZ).png"
image_width=1200
image_height=675

upload_response="$(curl -fsS -X POST \
  "$JIRA_BASE_URL/rest/api/2/issue/$issue_key/attachments" \
  -u "$JIRA_USER_EMAIL:$JIRA_API_TOKEN" \
  -H 'Accept: application/json' \
  -H 'X-Atlassian-Token: no-check' \
  -F "file=@$image_path;filename=$inline_name")"
attachment_id="$(jq -er '.[0].id' <<< "$upload_response")"
attachment_name="$(jq -er '.[0].filename' <<< "$upload_response")"

media_id="$(curl -fsS --max-redirs 0 -D - -o /dev/null \
  "$JIRA_BASE_URL/rest/api/3/attachment/content/$attachment_id" \
  -u "$JIRA_USER_EMAIL:$JIRA_API_TOKEN" | \
  tr -d '\r' | \
  sed -nE 's|^[Ll]ocation: https://api\.media\.atlassian\.com/file/([^/?]+)/binary.*|\1|p')"
test -n "$media_id"
```

Add the image to the approved ADF comment body:

```bash
comment_response="$(jq -n \
  --arg mediaId "$media_id" \
  --arg filename "$attachment_name" \
  --argjson width "$image_width" \
  --argjson height "$image_height" \
  '{body:{type:"doc",version:1,content:[
    {type:"paragraph",content:[{type:"text",text:"Implementation flow:"}]},
    {type:"mediaSingle",attrs:{layout:"align-start"},content:[
      {type:"media",attrs:{
        type:"file",id:$mediaId,collection:"",alt:$filename,
        width:$width,height:$height
      }}
    ]}
  ]}}' | curl -fsS -X POST \
    "$JIRA_BASE_URL/rest/api/3/issue/$issue_key/comment" \
    -u "$JIRA_USER_EMAIL:$JIRA_API_TOKEN" \
    -H 'Accept: application/json' \
    -H 'Content-Type: application/json' \
    --data @-)"

comment_id="$(jq -er '.id' <<< "$comment_response")"
curl -fsS "$JIRA_BASE_URL/rest/api/3/issue/$issue_key/comment/$comment_id" \
  -u "$JIRA_USER_EMAIL:$JIRA_API_TOKEN" \
  -H 'Accept: application/json' | \
  jq -e --arg id "$media_id" 'any(..; .type? == "media" and .attrs.id == $id)'
```

If UUID resolution or ADF validation fails, use the CLI `--image` flow. Do not fall back to private Media API endpoints or place the numeric attachment ID in `attrs.id`.
