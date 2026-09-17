---
name: alter
description: >
  Inspect and safely change Alter, the native macOS AI assistant from
  alterhq.com, without going through its GUI. Audit its global hotkeys, find
  and resolve collisions with launchers and capture tools, move an action off a
  chord, and document its app-data locations without reading private content.
  Use when the user
  mentions Alter, asks why an Alter shortcut stopped firing, wants to free a
  keyboard chord an Alter action is holding, or needs a macOS global hotkey
  conflict audit. Alter's meeting transcripts and conversation history are off
  limits to this skill.
license: MIT
allowed-tools:
  - Bash
  - Read
metadata:
  author: vanducng
  version: "1.0.0"
  bundle-id: com.wearedevx.alter
---

# Alter

Alter is a native macOS AI assistant: actions, dictation, meeting recording and
transcription, with local model support. Official docs are at
`https://docs.alterhq.com`. This skill uses the preferences file for narrowly
scoped hotkey work and the GUI for everything else.

## Privacy boundary, read this first

Alter records meetings and stores transcripts and conversation history locally.
Some of that content sits in the **same preferences plist as the hotkeys**, not
only in its databases.

Never dump the whole plist. A bare `defaults read com.wearedevx.alter` or a
broad `plutil -p` can splash an entire meeting transcript into the transcript of
your own session, including names and whatever the meeting was about.

- Read **named keys only**, never the whole domain.
- Never open `Alter.sqlite`, `Search.sqlite`, or anything under the transcripts
  directory.
- Never quote, summarize, or store what you see if it leaks anyway. Say that it
  leaked and move on.
- If the user wants transcript content, tell them to export it from the app.

This is the one hard rule in this skill. Everything below respects it.

## Where things live

| What | Path |
| --- | --- |
| Hotkeys and settings | `$HOME/Library/Preferences/com.wearedevx.alter.plist` |
| Actions, history, transcripts | `$HOME/Library/Application Support/Alter/` |
| Application | `/Applications/Alter.app` |

Hotkeys are the only part of that plist this skill touches.

## Hotkey encoding

Every binding is a JSON **string** under a `KeyboardShortcuts_<action>` key:

```json
{"access": "systemGlobal", "carbonKeyCode": 15, "carbonModifiers": 768}
```

- `access` is `systemGlobal` (fires anywhere) or `appLocal` (only while Alter is
  focused). **Only `systemGlobal` can collide with other apps.**
- `carbonModifiers` is a bitmask: cmd 256, shift 512, opt 2048, ctrl 4096. So
  768 is cmd+shift.
- `carbonKeyCode` is a Carbon virtual keycode, which is layout independent and
  not ASCII. The letters are scattered: A 0, S 1, D 2, F 3, H 4, G 5, Z 6, X 7,
  C 8, V 9, B 11, Q 12, W 13, E 14, R 15, Y 16, T 17, O 31, U 32, I 34, P 35,
  L 37, J 38, K 40, N 45, M 46, Space 49.

Custom actions use a key of the form
`KeyboardShortcuts_user_action_<action-uuid>`. The UUID maps to a record inside
Alter's database, which is off limits, so you cannot name the action from the
plist alone. **Ask the user what an action does rather than going to look.**

## Audit hotkeys

`scripts/hotkey-audit.py` reads hotkey-shaped keys from Alter and other common
macOS hotkey owners, decodes them, and reports collisions. It never prints
non-hotkey keys. Alter `appLocal` bindings appear in the inventory so they can
be avoided when choosing a replacement, but only `systemGlobal` bindings enter
cross-owner collision groups.

```sh
python3 scripts/hotkey-audit.py               # all owners, human readable
python3 scripts/hotkey-audit.py --json        # machine readable
python3 scripts/hotkey-audit.py --strict      # exit 1 when anything collides
```

Two apps binding the same chord is not a warning in macOS, it is a silent
failure. Carbon hands the chord to whichever app registers it first, and the
loser gets no error. Symptom: a shortcut that "just stopped working" after a
reboot, with nothing in any log. If both apps launch at login, the winner can
change between boots.

## Change a hotkey

Prefer the GUI when the user is at the machine. Editing the plist is for
scripted or repeatable setups.

In the app: **Settings** with `cmd+,` then **Shortcuts**, or the Action Editor
at `cmd+shift+E` for an individual action's binding.

By file, all four steps matter:

```sh
osascript -e 'quit app "Alter"'; sleep 3      # 1
```

```python
# 2. read, assert the current value, then write. The assert is the guard
#    against stomping a binding that already moved.
import plistlib, json, os
p = os.path.expanduser("~/Library/Preferences/com.wearedevx.alter.plist")
KEY = "KeyboardShortcuts_user_action_<action-uuid>"
d = plistlib.load(open(p, "rb"))
before = json.loads(d[KEY])
assert before["carbonKeyCode"] == 15 and before["carbonModifiers"] == 768, before
after = dict(before); after["carbonKeyCode"] = 2     # R to D
d[KEY] = json.dumps(after)
plistlib.dump(d, open(p, "wb"))
```

```sh
killall cfprefsd; sleep 1                     # 3
open -a Alter                                 # 4
```

Why each step, because skipping any one makes the edit look like it failed:

1. A running app holds its preferences in memory and rewrites them on quit,
   discarding an external edit.
2. Load, verify, write. Modify one key and leave every other key untouched, so
   transcript data in the same file is never re-encoded or read.
3. `cfprefsd` caches preferences. Without this, macOS keeps serving the old
   value and can write its cache back over the file.
4. Carbon registers hotkeys at launch. Until Alter restarts it holds its old
   chord and not the new one.

`defaults write <domain> <key> -string '<json>'` also works for these values,
since each is a plain string. `plistlib` is preferred here only because it
supports the read-verify-write guard.

## Resolving a collision

1. Run the audit. Confirm the collision is real and both sides are
   `systemGlobal`. `--strict` checks only those cross-owner collisions.
2. Ask which app should own the chord. Do not guess, and do not go read
   Alter's database to work out what its action does.
3. Move the loser to a free chord. Check the full audit output for what is
   taken, including Alter's `appLocal` chords.
4. Prefer a replacement that avoids Alter's own `appLocal` chords too, so the
   new binding does not collide inside Alter.
5. Re-run the audit and confirm zero collisions.

Frequent competitors for `cmd+shift` chords: launchers such as Raycast or
Tinycast, capture tools such as CleanShot, and tiling daemons driven by skhd.

Alter's documented defaults include QuickHub at `cmd+shift+Space`, Hub at
`cmd+shift+H`, new chat at `opt+Space`, dictation on `Fn`, meeting capture at
`cmd+shift+M`, live captions at `cmd+shift+down`, and live notepad at
`cmd+shift+right`. The Action Editor is `cmd+shift+E`; the Settings shortcut
editor is under Settings → Shortcuts. Treat defaults as starting points and
audit the live machine, since users remap.

## Sources

- [Settings guide](https://docs.alterhq.com/how-to/settings-guide) - shortcut
  editor, permissions, voice and meeting settings.
- [Alter Actions](https://docs.alterhq.com/workflows/alter-actions) - Action
  Editor, action context, triggers and x-callback-url automation.
- [Meetings](https://docs.alterhq.com/workflows/meetings) - recording,
  transcription and meeting workflows.
- [Core features](https://docs.alterhq.com/getting-started/core-features) -
  AppSense, Follow Mode and native app integrations.

## Config portability

Alter has no text config. Its bindings live in the plist, so a dotfiles
repository cannot stow them, and a rebuilt machine comes back with Alter's
defaults. When a user has deliberately moved an Alter chord to make room for
another app, record that in whatever script provisions the other app, or the
collision returns silently on the next rebuild.
