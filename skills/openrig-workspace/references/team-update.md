# Team update in a chat channel

An update the operator posts to a team channel (Slack, Teams, Google Chat) about a project: what changed, what was decided, and what the team must answer. The workspace rule applies in full: drafted, shown with its destination, sent only after the operator's yes on the exact text, then read back and logged.

## Shape

```
*<Project> update: <topic> (<ticket keys>)*

*1. <first change, as a short headline>*
<two to five plain sentences: what changed, why, and the evidence that it works>

*2. <next change>*
• <one bullet per item when the section is a list>
• <a person who must act is mentioned by user id, with the ticket link>

*N. Decision needed: <the question in a few words>*
<what it is, what it does now, what the other choice does, the current setting, one doc link>. <The question, ending in a question mark.>
```

- One message, numbered bold sections, newest decisions last. Each section stands alone.
- Facts only, each one something the team can check: numbers, links, test results. No internal ids the team cannot open.
- A decision section carries the current state and both options in one paragraph, and ends with the question.
- Mention a person with the app's user id (Slack `<@U…>`), never a display name; mention only people who must act. No channel-wide mention unless the channel's recent posts use it.
- Links: ticket keys as links (Slack `<url|KEY-1>`); console and doc links in full.
- No secrets, tokens, client data, or personal phone numbers.

## Post and read back (Slack through Aside)

```js
// Aside REPL; the team id comes from the org's resources.yaml, never from listWorkspaces().
const client = await slack.getClient('<team id>');
const text = <the approved text, as a JSON string>;
const posted = await client.chat.postMessage({ channel: '<channel id>', text, unfurl_links: false, unfurl_media: false });
const { permalink } = await client.chat.getPermalink({ channel: '<channel id>', message_ts: posted.ts });
const back = (await client.conversations.history({ channel: '<channel id>', latest: posted.ts, inclusive: true, limit: 1 })).messages[0].text;
```

- Pass the text inline as a JSON string; the REPL has no synchronous file read.
- Compare `back` with the approved text line by line. Slack wraps bare URLs in `<…>`; any other difference means the words changed: stop and tell the operator.
- Log the permalink in the slice or mission `PROGRESS.md`, and on the tracking board when there is one.
- A ticket the post refers to is created first (its own yes, see the `jira` skill), so the post carries its real key.
