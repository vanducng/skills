# Inline Images in Jira Descriptions and Comments

Use this workflow after loading the instance rules, exporting authentication, showing the complete body, and getting approval for the write. Applies to **issue descriptions** (create/edit) and **comments**.

A provided screenshot or diagram is not done until it is inline ADF. An attachment with no `mediaSingle` in the description or comment is incomplete.

| Need | Method |
| --- | --- |
| Public image URL | Markdown image syntax in the description or comment |
| Readable local screenshot or diagram | REST v3 ADF `mediaSingle`, left aligned at 100% width, in the description (create) or comment (follow-up) |
| Reuse an existing attachment | Resolve its Media Services UUID; do not re-upload |
| Quick local thumbnail | `jira issue comment add --image` (not for ticket evidence) |
| Repair an existing small or centered image | Update the existing description or comment ADF in place |

## Issue description

Attachment upload needs an issue key, so create cannot carry the image on the first `POST`.

1. `POST /rest/api/3/issue` to create the issue (text description is fine).
2. Upload the file to `POST /rest/api/2/issue/$issue_key/attachments` and resolve the Media Services UUID (same recipe as comments below).
3. `PUT /rest/api/3/issue` with `mediaSingle` nodes in `fields.description`.

On edit, reuse the existing attachment UUID. Do not re-upload. Do not leave the description image-free after upload.

If `GET /rest/api/3/issue/KEY` 404s, confirm the key via JQL, then `PUT` anyway (see SKILL.md Known API Issues). Verify from `fields.description.content[]`, not `.body.content[]`:

```bash
curl -fsS "$JIRA_BASE_URL/rest/api/3/issue/$issue_key?fields=description" \
  -u "$JIRA_USER_EMAIL:$JIRA_API_TOKEN" \
  -H 'Accept: application/json' | \
  jq -e --arg id "$media_id" --argjson width "$image_width" --argjson height "$image_height" '
    .fields.description.content[]
    | select(.type == "mediaSingle")
    | .attrs.layout == "align-start"
      and .attrs.width == 100
      and .attrs.widthType == "percentage"
      and .content[0].attrs.id == $id
      and .content[0].attrs.width == $width
      and .content[0].attrs.height == $height
  '
```

## Public Image URL

`jira-cli` converts Markdown image syntax to Jira markup. The URL must remain reachable by Jira users.

```bash
jira issue comment add PROJ-123 '![Architecture](https://example.com/architecture.png)'
```

Do not use this for private or short-lived URLs.

## Local Image: Readable ADF

This is the default local-file workflow for screenshots, diagrams, and other evidence users must read without opening the attachment preview. Jira's attachment content endpoint redirects to a Media Services URL whose path contains the UUID required by an ADF `media` node. This works on Jira Cloud, but Atlassian does not document the redirect path as a stable identifier contract.

Keep the source pixel dimensions on the media node. Set `mediaSingle.attrs.layout` to `align-start`, `width` to `100`, and `widthType` to `percentage`. Jira otherwise centers media and defaults it to 50% of the comment width, even when the media node contains larger pixel dimensions.

Upload the attachment manually, provide its source dimensions, and resolve the UUID without printing the signed redirect URL:

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
    {type:"mediaSingle",attrs:{layout:"align-start",width:100,widthType:"percentage"},content:[
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

Verify the stored layout and dimensions, not only that the media ID exists:

```bash
curl -fsS "$JIRA_BASE_URL/rest/api/3/issue/$issue_key/comment/$comment_id" \
  -u "$JIRA_USER_EMAIL:$JIRA_API_TOKEN" \
  -H 'Accept: application/json' | \
  jq -e --arg id "$media_id" --argjson width "$image_width" --argjson height "$image_height" '
    .body.content[]
    | select(.type == "mediaSingle")
    | .attrs.layout == "align-start"
      and .attrs.width == 100
      and .attrs.widthType == "percentage"
      and .content[0].attrs.id == $id
      and .content[0].attrs.width == $width
      and .content[0].attrs.height == $height
  '
```

## Repair an Existing Small or Centered Image

Do not upload a duplicate attachment. Read the comment, retain its existing Media Services ID and text content, then update every `mediaSingle` node in the comment with REST v3. Inspect the stored ADF first when the comment contains multiple images that need different dimensions.

```bash
issue_key='PROJ-123'
comment_id='12345'
image_width=1200
image_height=675

comment="$(curl -fsS "$JIRA_BASE_URL/rest/api/3/issue/$issue_key/comment/$comment_id" \
  -u "$JIRA_USER_EMAIL:$JIRA_API_TOKEN" \
  -H 'Accept: application/json')"
media_id="$(jq -er '.body.content[] | select(.type == "mediaSingle") | .content[0].attrs.id' <<< "$comment")"

jq --argjson width "$image_width" --argjson height "$image_height" '
  .body.content |= map(
    if .type == "mediaSingle" then
      .attrs.layout = "align-start"
      | .attrs.width = 100
      | .attrs.widthType = "percentage"
      | .content[0].attrs.width = $width
      | .content[0].attrs.height = $height
    else . end
  )
  | {body: .body}
' <<< "$comment" | curl -fsS -X PUT \
  "$JIRA_BASE_URL/rest/api/3/issue/$issue_key/comment/$comment_id" \
  -u "$JIRA_USER_EMAIL:$JIRA_API_TOKEN" \
  -H 'Accept: application/json' \
  -H 'Content-Type: application/json' \
  --data @-
```

Re-read the comment and apply the same layout, 100% width, media-ID, source-width, and source-height verification used for a new ADF comment.

## Local Image: Compact Thumbnail

Use this only when a small preview is acceptable. The fork uploads the file and creates a centered 200 px ADF thumbnail.

```bash
issue_key='PROJ-123'
image_path='/path/to/architecture.png'
jira issue comment add "$issue_key" "Quick evidence:" --image "$image_path"
```

If the CLI reports a comment failure after upload, preserve the listed attachment IDs for review or cleanup. If UUID resolution or ADF validation fails for the readable workflow, this thumbnail path is the safe fallback. Do not call private Media API endpoints or place the numeric attachment ID in `attrs.id`.
