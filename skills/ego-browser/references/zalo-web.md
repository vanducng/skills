# Zalo Web

## One session only

Zalo Web allows one active web session for the account. Reuse the existing Ego task space and tab for every Zalo action in the same user session.

- Do not open Zalo in a second Ego task space.
- Keep the Zalo task space open until all chat work is finished.
- If the task space already exists, resume it by the same name or ID instead of creating another one.

## Mentions that actually notify

A bot or person may stay silent unless the message contains a real Zalo mention token. Plain text such as `@Name` is not enough.

Zalo's rich editor can move a selected mention into later text if `typeText()` appends prose after the mention. `Enter` is not a reliable selection or send action: depending on focus it may add a newline and leave the draft unsent. Use the visible mention result and send button instead.

1. Confirm `#richInput` is empty. Clear only a draft created by the current failed attempt.
2. Type the complete message first, leaving the mention for the end.
3. Type `@`, then the exact member name.
4. Click the exact visible `.mention-popover .tg-name` result.
5. Verify the draft contains `.clnMention` with the intended name.
6. Do not type anything else. Click `.send-msg-btn`.
7. Verify the composer is empty and the sent message contains `a.mention-name`.

Use one mention per message when reliability matters. Send separate short messages for multiple people.

```js
const editor = '#richInput'
const existing = await js(`document.querySelector('${editor}')?.innerText.trim()`)
if (existing) throw new Error('composer already contains a draft')

await click(editor)
await typeText('Please review the plan and reply in the ticket: ')
await typeText('@Member Name')
await wait(1)

const selected = await js(String.raw`(() => {
  const normalize = value => value.replace(/\s+/g, ' ').trim()
  const item = [...document.querySelectorAll('.mention-popover .tg-name')]
    .find(el => normalize(el.textContent) === 'Member Name')
  if (!item) return false
  item.click()
  return true
})()`)
if (!selected) throw new Error('mention suggestion was not found')

const draft = await js(String.raw`(() => ({
  text: document.querySelector('#richInput')?.innerText,
  mentions: [...document.querySelectorAll('#richInput .clnMention')].map(x => x.textContent),
}))()`)
if (!draft.mentions.includes('@Member Name')) throw new Error('mention was not selected')

await click('.send-msg-btn')
await wait(2)
const sent = await js(String.raw`(() => ({
  draft: document.querySelector('#richInput')?.innerText.trim(),
  mention: [...document.querySelectorAll('a.mention-name')].at(-1)?.textContent,
}))()`)
if (sent.draft || sent.mention !== '@Member Name') throw new Error('message was not sent with the mention')
```

If the sent DOM lacks `a.mention-name`, the mention did not land. Send a corrected message instead of assuming the recipient or bot was notified.

## Paste an image or screenshot

Zalo Web may use a native chooser without leaving an `input[type="file"]` in the DOM. Copy the image to the macOS clipboard, then dispatch a paste event with a `File` from the page context.

```bash
osascript -e 'set the clipboard to (read (POSIX file "/tmp/zalo-upload.png") as «class PNGf»)'
```

```js
await snapshotText()
await click('@COMPOSER_REF')

const result = await js(String.raw`(async () => {
  const items = await navigator.clipboard.read()
  const blob = await items[0].getType('image/png')
  const file = new File([blob], 'zalo-upload.png', { type: 'image/png' })
  const transfer = new DataTransfer()
  transfer.items.add(file)
  const editor = [...document.querySelectorAll('[contenteditable="true"]')]
    .find(e => e.offsetParent !== null)
  if (!editor) return { error: 'no editor' }
  editor.focus()
  const event = new ClipboardEvent('paste', {
    bubbles: true,
    cancelable: true,
    clipboardData: transfer,
  })
  editor.dispatchEvent(event)
  return { files: transfer.files.length }
})()`)

if (result.files !== 1) throw new Error('image paste failed')
await wait(3)
```

Confirm the composer shows an image preview before pressing `Enter`. After sending, capture or inspect the conversation to verify the image appears.
