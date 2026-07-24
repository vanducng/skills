// Template - adapt rulesSource / target before running.
// Forward direction: enforce existing rules with one verifier agent per rule.
// Returns confirmed violations (skeptic-filtered); the main session reports them.
export const meta = {
  name: 'check-rules',
  description: 'Load the rule set, run one verifier per rule against a diff/codebase, skeptic-filter false positives',
  phases: [
    { title: 'Load', detail: 'read the rule set into an enumerated list' },
    { title: 'Check', detail: 'one verifier agent per rule vs the target' },
    { title: 'Skeptic', detail: 'refute weak violations to cut false positives' },
  ],
}

const A = args || {}
const rulesSource = A.rulesSource || 'project' // global | project
const target = A.target || 'git diff'
const ruleHome = rulesSource === 'global'
  ? '~/.claude/CLAUDE.md and ~/.claude/rules/*.md'
  : 'the project CLAUDE.md and docs/code-standards.md (if present)'

const RULES = {
  type: 'object', required: ['rules'],
  properties: { rules: { type: 'array', items: {
    type: 'object', required: ['id', 'text'],
    properties: { id: { type: 'string' }, text: { type: 'string' } },
  } } },
}
const VIOLATION = {
  type: 'object', required: ['violated'],
  properties: {
    violated: { type: 'boolean' },
    file: { type: 'string' },
    line: { type: 'number' },
    evidence: { type: 'string' },
  },
}
const REFUTE = {
  type: 'object', required: ['refuted'],
  properties: { refuted: { type: 'boolean' }, reason: { type: 'string' } },
}

phase('Load')
const loaded = await agent(
  `Read the rule set at ${ruleHome}. Return each concrete, checkable rule as { id, text }. Skip headers, prose, and rules that cannot be checked against code.`,
  { phase: 'Load', schema: RULES })
const rules = loaded.rules || []
log(`Load: ${rules.length} checkable rules`)
if (!rules.length) return { violations: [], checked: 0 }

// One verifier per rule (Check), then a skeptic per flagged violation (Skeptic) - pipelined, no barrier.
const results = await pipeline(
  rules,
  (rule) => agent(`Does \`${target}\` violate this rule? Rule: "${rule.text}". Read the actual changed code. Report violated + file:line + evidence, or violated=false.`,
    { label: `check:${rule.id}`, phase: 'Check', schema: VIOLATION }).then((v) => ({ rule, v })),
  ({ rule, v }) => {
    if (!v || !v.violated) return { rule, v, confirmed: false }
    return agent(`Skeptic. A check flagged rule "${rule.text}" as violated at ${v.file}:${v.line} (evidence: ${v.evidence}). ` +
      `Refute it: is the code actually fine (handled elsewhere, out of scope, misread)? Default refuted=true unless the evidence is concrete.`,
      { label: `refute:${rule.id}`, phase: 'Skeptic', schema: REFUTE })
      .then((r) => ({ rule, v, confirmed: !(r && r.refuted) }))
  })

const violations = results.filter(Boolean).filter((x) => x.confirmed)
  .map((x) => ({ rule: x.rule.text, file: x.v.file, line: x.v.line, evidence: x.v.evidence }))
log(`Check: ${violations.length} confirmed violations of ${rules.length} rules`)
return { violations, checked: rules.length }
