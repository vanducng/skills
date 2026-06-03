// Template — adapt FINDERS / scope to the user's real setup before running.
// Mine repeated corrections from history and distill verified rule proposals.
// Returns proposals; the main session presents them and writes only on approval.
export const meta = {
  name: 'mine-rules',
  description: 'Mine sessions + git + PR history for repeated corrections, verify each, distill CLAUDE.md rule proposals',
  phases: [
    { title: 'Discover', detail: 'parallel finders sweep each source for correction events' },
    { title: 'Cluster', detail: 'group events into candidates, dedupe vs existing rules' },
    { title: 'Verify', detail: 'per candidate: evidence verifier + skeptic, keep survivors' },
    { title: 'Distill', detail: 'survivors → proposed rule text + target file' },
  ],
}

const A = args || {}
const sessionsGlob = A.sessionsGlob || '~/.claude/projects/**/*.jsonl'
const repoPath = A.repoPath || '.'
const scope = A.scope || 'project' // global → ~/.claude rules; project → repo CLAUDE.md
const deep = !!A.deep
const ruleHome = scope === 'global'
  ? '~/.claude/CLAUDE.md and ~/.claude/rules/*.md'
  : 'the project CLAUDE.md and docs/'

const EVENTS = {
  type: 'object', required: ['events'],
  properties: { events: { type: 'array', items: {
    type: 'object', required: ['quote', 'inferredRule'],
    properties: {
      source: { type: 'string' },
      quote: { type: 'string' },
      context: { type: 'string' },
      inferredRule: { type: 'string' },
    },
  } } },
}
const CANDIDATES = {
  type: 'object', required: ['candidates'],
  properties: { candidates: { type: 'array', items: {
    type: 'object', required: ['id', 'rule'],
    properties: {
      id: { type: 'string' },
      rule: { type: 'string' },
      events: { type: 'array', items: { type: 'string' } },
      occurrences: { type: 'number' },
    },
  } } },
}
const VERDICT = {
  type: 'object', required: ['reason'],
  properties: {
    keep: { type: 'boolean' },
    falsePositive: { type: 'boolean' },
    reason: { type: 'string' },
  },
}
const PROPOSALS = {
  type: 'object', required: ['proposals'],
  properties: { proposals: { type: 'array', items: {
    type: 'object', required: ['rule', 'targetFile', 'why'],
    properties: {
      rule: { type: 'string' },
      targetFile: { type: 'string' },
      why: { type: 'string' },
      evidence: { type: 'string' },
      metadataType: { type: 'string' },
    },
  } } },
}

// Each finder is blind to the others — a different angle on "corrections I keep making".
const FINDERS = [
  { key: 'sessions', prompt: `Read recent Claude Code session transcripts matching ${sessionsGlob} (newest first; JSONL, one event per line). Extract correction events: user messages that push back, override, or re-instruct the assistant — "no", "don't", "actually", "stop doing X", "I told you", "again", "use X not Y", reverts of the assistant's output. For each, capture the verbatim quote, surrounding context, and the rule it implies.` },
  { key: 'git', prompt: `In ${repoPath}, mine git history for corrections: revert commits, "fixup"/"actually"/"oops" subjects, and diffs to CLAUDE.md / rules/ files (each rule edit is itself a recorded correction). Extract the same correction-event shape.` },
  { key: 'reviews', prompt: `Use \`gh\` to fetch recent PR review comments authored by the user in ${repoPath}'s remote. Extract recurring review nits the user raises across PRs (same critique on multiple PRs). Same correction-event shape.` },
]

phase('Discover')
async function discoverOnce(round) {
  const found = await parallel(FINDERS.map((f) => () =>
    agent(`${f.prompt}\n\nRound ${round}: return correction events you have NOT already reported.`,
      { label: `find:${f.key}:r${round}`, phase: 'Discover', schema: EVENTS })))
  return found.filter(Boolean).flatMap((r) => r.events || [])
}

let events = await discoverOnce(1)
if (deep) {
  let dry = 0
  let round = 2
  while (dry < 2 && round <= 5) {
    const more = await discoverOnce(round)
    if (more.length) { events.push(...more); dry = 0 } else { dry++ }
    round++
  }
}
log(`Discover: ${events.length} correction events across ${FINDERS.length} sources`)
if (!events.length) return { proposals: [], rejected: [], stats: { events: 0 } }

phase('Cluster')
const clustered = await agent(
  `Cluster these correction events into candidate rules. Merge near-duplicates. ` +
  `CRITICAL: first read the existing rule set (${ruleHome}) and DROP any candidate already covered there. ` +
  `A candidate needs >=2 distinct supporting events to qualify; cut the rest.\n\nEVENTS:\n${JSON.stringify(events)}`,
  { phase: 'Cluster', schema: CANDIDATES })
const candidates = clustered.candidates || []
log(`Cluster: ${candidates.length} candidate rules after dedupe vs existing`)
if (!candidates.length) return { proposals: [], rejected: [], stats: { events: events.length, candidates: 0 } }

phase('Verify')
const judged = await parallel(candidates.map((c) => () =>
  parallel([
    () => agent(`Evidence check. Candidate rule: "${c.rule}". Supporting events: ${JSON.stringify(c.events)}. ` +
      `Would this rule have PREVENTED a real, repeated mistake (>=2 distinct occasions)? Reject if one-off, vague, or unenforceable. Set keep=false if unsure.`,
      { label: `verify:${c.id}`, phase: 'Verify', schema: VERDICT }),
    () => agent(`Skeptic. Argue why candidate rule "${c.rule}" is a FALSE POSITIVE: overfit to one session, already implied by common sense, or would cause annoying false alarms. Set falsePositive accordingly.`,
      { label: `skeptic:${c.id}`, phase: 'Verify', schema: VERDICT }),
  ]).then(([v, s]) => ({ candidate: c, keep: !!(v && v.keep) && !(s && s.falsePositive) }))))

const survivors = judged.filter(Boolean).filter((j) => j.keep).map((j) => j.candidate)
const rejected = judged.filter(Boolean).filter((j) => !j.keep).map((j) => j.candidate.rule)
log(`Verify: ${survivors.length} survived, ${rejected.length} rejected`)
if (!survivors.length) return { proposals: [], rejected, stats: { events: events.length, candidates: candidates.length } }

phase('Distill')
const distilled = await agent(
  `Turn these verified candidates into concrete rule proposals. For each: exact rule text (terse, imperative, one line where possible), ` +
  `target file (${scope === 'global' ? '~/.claude/CLAUDE.md or ~/.claude/rules/<topic>.md' : 'project CLAUDE.md'}), a one-line WHY, and the strongest supporting evidence quote. Do NOT write any files.\n\nSURVIVORS:\n${JSON.stringify(survivors)}`,
  { phase: 'Distill', schema: PROPOSALS })

return {
  proposals: distilled.proposals || [],
  rejected,
  stats: { events: events.length, candidates: candidates.length, survivors: survivors.length },
}
