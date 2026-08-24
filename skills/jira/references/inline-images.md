# Inline Images in Jira Comments

Use this workflow only after loading the instance rules, exporting authentication, showing the complete comment, and getting approval for the attachment and comment writes.

| Need | Method |
| --- | --- |
| Public image URL | `jira issue comment add` with Markdown image syntax |
| Readable local screenshot or diagram | REST v3 ADF `mediaSingle`, left aligned and sized from the source image |
| Quick local thumbnail | `jira issue comment add --image` |
| Repair an existing small or centered image | Update the existing comment ADF in place |

## Public Image URL

`jira-cli` converts Markdown image syntax to Jira markup. The URL must remain reachable by Jira users.

```bash
jira issue comment add PROJ-123 '![Architecture](https://example.com/architecture.png)'
```

Do not use this for private or short-lived URLs.

## Local Image: Readable ADF

This is the default local-file workflow for screenshots, diagrams, and other evidence users must read without opening the attachment preview. Jira's attachment content endpoint redirects to a Media Services URL whose path contains the UUID required by an ADF `media` node. This works on Jira Cloud, but Atlassian does not document the redirect path as a stable identifier contract.

Use the source image aspect ratio. Cap the display width at 1200 px, do not upscale images narrower than that, and calculate the display height as `round(source_height * display_width / source_width)`. Set `mediaSingle.attrs.layout` to `align-start`; Jira otherwise commonly centers inline media.

Upload the attachment manually, provide the calculated display dimensions, and resolve the UUID without printing the signed redirect URL:

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

Verify the stored layout and dimensions, not only that the media ID exists:

```bash
curl -fsS "$JIRA_BASE_URL/rest/api/3/issue/$issue_key/comment/$comment_id" \
  -u "$JIRA_USER_EMAIL:$JIRA_API_TOKEN" \
  -H 'Accept: application/json' | \
  jq -e --arg id "$media_id" --argjson width "$image_width" --argjson height "$image_height" '
    .body.content[]
    | select(.type == "mediaSingle")
    | .attrs.layout == "align-start"
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

Re-read the comment and apply the same layout, media-ID, width, and height verification used for a new ADF comment.

## Local Image: Compact Thumbnail

Use this only when a small preview is acceptable. The fork uploads the file and creates a centered 200 px ADF thumbnail.

```bash
issue_key='PROJ-123'
image_path='/path/to/architecture.png'
jira issue comment add "$issue_key" "Quick evidence:" --image "$image_path"
```

If the CLI reports a comment failure after upload, preserve the listed attachment IDs for review or cleanup. If UUID resolution or ADF validation fails for the readable workflow, this thumbnail path is the safe fallback. Do not call private Media API endpoints or place the numeric attachment ID in `attrs.id`.
