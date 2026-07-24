// Template - adapt DIMENSIONS / votes before running.
// Ultra review: find issues per dimension, then adversarially refute each finding.
// Returns only confirmed findings; the main skill assembles + posts the GitHub review.
export const meta = {
  name: 'adversarial-review',
  description: 'Review a diff across dimensions, adversarially verify each finding, return only confirmed findings',
  phases: [
    { title: 'Review', detail: 'one agent per review dimension finds candidate issues' },
    { title: 'Verify', detail: 'per finding: independent refuters, majority-refute drops it' },
  ],
}

const A = args || {}
// How to obtain the diff inside agents: a PR number, or any git/gh command.
const target = A.diffCmd || (A.pr ? `gh pr diff ${A.pr}` : 'git diff')
const votes = A.votes || 3

const DIMENSIONS = [
  { key: 'correctness', prompt: 'off-by-one, nil/null deref, swallowed errors, races/goroutine leaks, untested edge cases (empty/zero/max/unicode/timezone/DST)' },
  { key: 'security', prompt: 'injection (SQL/command/template/XSS), hardcoded secrets, auth scoping (userID vs tenantID), SSRF / path traversal / open redirect' },
  { key: 'reliability', prompt: 'retries without idempotency keys, unbounded queues/caches, network calls missing timeouts, irreversible migrations' },
  { key: 'performance', prompt: 'N+1 queries, full scans on hot paths vs existing indexes, allocations in hot loops - flag ONLY with concrete evidence' },
  { key: 'api', prompt: 'renamed/removed exports, changed response shape/status codes, config schema change without a compat shim' },
  { key: 'tests', prompt: 'new code paths uncovered, missing edge-case tests, mixed mock/real-DB conventions, no regression test for the bug being fixed' },
]

const FINDINGS = {
  type: 'object', required: ['findings'],
  properties: { findings: { type: 'array', items: {
    type: 'object', required: ['file', 'problem'],
    properties: {
      file: { type: 'string' },
      line: { type: 'number' },
      severity: { type: 'string' }, // critical | important | suggestion
      problem: { type: 'string' },
    },
  } } },
}
const VERDICT = {
  type: 'object', required: ['refuted'],
  properties: { refuted: { type: 'boolean' }, reason: { type: 'string' } },
}

// Pipeline: each dimension's findings verify as soon as that dimension finishes (no barrier).
const results = await pipeline(
  DIMENSIONS,
  (d) => agent(`Review the diff (\`${target}\`) for ${d.key} issues: ${d.prompt}. ` +
    `Read full files around each hunk, not just the hunk. Return findings with file, line, severity, and a one-sentence problem naming the concrete failure mode.`,
    { label: `review:${d.key}`, phase: 'Review', schema: FINDINGS }),
  (review, d) => parallel((review.findings || []).map((f) => () =>
    parallel(Array.from({ length: votes }, (_, i) => () =>
      agent(`Try to REFUTE this ${d.key} finding. Read the real code via \`${target}\` context. ` +
        `Finding: "${f.problem}" at ${f.file}:${f.line || '?'}. Is it real, or a false positive (already handled, unreachable, misread)? Default refuted=true if uncertain.`,
        { label: `refute:${d.key}:${f.file}:${f.line || 0}:${i}`, phase: 'Verify', schema: VERDICT })))
      .then((vs) => {
        const r = vs.filter(Boolean)
        const real = r.filter((v) => !v.refuted).length > r.length / 2
        return { ...f, dimension: d.key, real, refuters: r.length }
      }))))

const all = results.flat().filter(Boolean)
const confirmed = all.filter((f) => f.real)
const dropped = all.filter((f) => !f.real)
log(`Confirmed ${confirmed.length}/${all.length} findings (${dropped.length} refuted by majority)`)
return { confirmed, dropped }
