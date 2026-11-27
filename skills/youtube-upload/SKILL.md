---
name: youtube-upload
description: "Uploads a finished video to the owner's YouTube channel through Aside (their signed-in browser) and finishes it in one pass: confirm the channel, upload, set title, description, custom thumbnail, audience and playlist, set Private or Unlisted (never Public), then read every field back from Studio. Use when the user says 'upload this to YouTube', 'put the video on my channel', 'upload it private', 'add it to the playlist', 'set the thumbnail on YouTube', 'is the upload done' or 'check the YouTube upload'. Not for cutting or rendering the video (travel-vlog, video), downloading from YouTube, or general browsing (aside-browser)."
license: MIT
metadata:
  author: vanducng
  version: "0.1.0"
---

# youtube-upload

`scripts/yt.sh` does the upload; do not drive YouTube Studio by hand. Each step that broke in real uploads is in the script: Aside reads files only from its own session folder, the upload wizard leaves a draft when it closes early, the playlist checkbox can click without saving, and a fresh video shows Visibility "Pending" until YouTube's checks run.

## Rules

1. **The owner's channel only.** Put the channel id (`UC...`) and the Google account index (`authuser`) in the meta file. Every script stops when the browser is signed in to another channel. Then stop and tell the owner; never point the upload at the channel that happens to be signed in.
2. **Private by default, never Public.** `edit` changes Private and Unlisted on a finished video too. `privacy` is `private` or `unlisted` (Unlisted is public to anyone with the link). Making a video Public, deleting one, or messaging anyone waits for the owner's word.
3. **Check before upload.** `yt.sh check` fails on a title over 100 characters, a description over 5000, `<` or `>` in either, a thumbnail that is not 16:9 or is 2 MB or more, and a bad channel id. Fix the file or the text, keeping the series name at the start of the title, and run it again. Nothing uploads while a `FAIL` line remains.
4. **One upload per video.** If a run fails after `upload.js` printed an id, finish that video with `yt.sh edit` (add `"id"` to the meta file). If it failed with no id after `STEP file handed over`, the file may still have arrived: look for a new draft on the channel and finish that one. If it printed an id but not `STEP upload complete`, the video shows "Upload interrupted": tell the owner, who decides whether to delete it before you upload again. A second upload makes a duplicate, and only the owner may delete one. If the file changed after the upload, say so; do not upload again on your own.
5. **The playlist must exist once.** The script refuses a missing or duplicated playlist name. Creating a playlist is a one-time step in Studio, as Private unless the owner says otherwise.
6. **Read back.** `publish` and `edit` end with `status`: title, visibility, draft, playlist, custom thumbnail; it fails when a video reads back as Public or with another visibility than the one asked for (Pending is allowed). Report what Studio shows. "Pending" means checks are still running; run `status` again later.

## Workflow

```bash
S=scripts                      # inside this skill
cat > meta.json <<'EOF'
{"channel": "UC...", "authuser": 1, "title": "Taiwan 2026 · Day 1 · Arrival",
 "description": "Landing at Taoyuan...\n\nMusic: \"...\" by ... (YouTube Audio Library)",
 "playlist": "Taiwan 2026", "privacy": "private"}
EOF
$S/yt.sh check   video.mp4 thumb.jpg meta.json    # ok, or FAIL lines to fix
$S/yt.sh publish video.mp4 thumb.jpg meta.json    # upload, details, playlist, privacy, read-back
$S/yt.sh edit    thumb.jpg meta-with-id.json      # finish an uploaded video
$S/yt.sh status  meta.json <id> [<id>...]         # read back any videos
```

`ASIDE` overrides the Aside binary; `ASIDE_SESSIONS` only changes where `yt.sh` looks for Aside's session folder (default `~/.aside/u/0/sessions`; Aside itself does not read it). Each repl call has a 120 s limit, so the upload and the details run as separate calls. Aside closes the call's tab when it ends, and a tab closed before "Upload complete" leaves "Upload interrupted" in Studio, so `upload.js` waits for it (about 105 s at most) and `publish` never edits an unfinished upload.

## Report

Per video: the link, the title, the visibility and playlist as `status` read them, and anything the owner must do (a stale duplicate to delete, a Pending to re-check).
