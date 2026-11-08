---
slice: demo
candidate_sha: abc1234
artifact_type: rev1-r1
verdict: x
money_evidence: review
---
---
axes: {spec: fail, standards: pass}
tier: Quick
patch_id: 0000000000000000000000000000000000000000
diff_digest: "sha256:00"
reviewed_at: 2026-11-07T11:00:00Z
reviewer_seat: "dev.review"
findings:
  - {id: "F1", axis: standards, tag: Important, status: open, text: "console.log left in src/greet.js"}
---

# Review verdict
