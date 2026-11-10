#!/usr/bin/env node
// The proof contract each work type starts with (ADR-0022 D1): `contract.cjs --list`, or `contract.cjs <type>` for the
// checkbox lines to put under "## Proof contract" in the record's SPEC.md. Exit 2 on an unknown type.
"use strict";
const TYPES = {
  "greenfield": ["A walking skeleton is deployed and a `verify-<app>` run drives it.", "CI runs on every push before any feature lands."],
  "brownfield-entry": ["An agent-readiness audit of the repo is recorded.", "A `verify-<app>` run and a feature map exist.", "One known behavior is reproduced before any change."],
  "feature": ["A before/after pair on the real surface (screenshot pair, or measured output pair).", "A verdict from a reviewer who did not write it, and one from a run of the change."],
  "bug-fix": ["A check that fails on the old code and passes on the new code.", "The failing case is kept as a regression test."],
  "triage": ["The report is classified, and reproduced or rejected with evidence.", "It is handed off as a slice an agent can pick up."],
  "investigation": ["The answer cites `file:line` and data for each claim.", "Each claim is labelled measured, inferred or guess."],
  "refactor": ["The same tests and outputs before and after (golden diff zero).", "A measured simplification (lines, branches or dependencies removed)."],
  "sop": ["Each step's output is captured."],
  "data-engineering": ["Built in a dev schema, audited (tests, row counts, diff against prod), then published.", "The proof says whether the audited schema was promoted or rebuilt."],
  "data-analysis": ["The metric is defined in one sentence.", "The number is reconciled against a known reference.", "The uncertainty is stated."],
  "bi-dashboard": ["A question sheet: each row has its audience, the decision it supports and a one-sentence metric definition, answered by the asker (vd:bi-dash).",
    "An HTML mockup on synthetic data, each chart tracing to a sheet row, with the asker's sign-off recorded.",
    "A field map: every mockup field mapped to a model column as exists, variant (with the choice) or missing, with nulls, outliers and duplicate spellings profiled.",
    "Every KPI reconciled to a reference (source-system count or prior report) within a stated tolerance.",
    "UAT on real data: a screenshot answers each sheet row inside its time-to-read budget, and design fidelity is 9 or more against the mockup.",
    "A metric glossary: definition, source, logic, owner and refresh cadence."],
};
const arg = process.argv[2];
if (!arg || arg === "--help") { process.stderr.write("usage: contract.cjs --list | <type>\n"); process.exit(2); }
if (arg === "--list") { process.stdout.write(Object.keys(TYPES).join("\n") + "\n"); process.exit(0); }
const key = arg.toLowerCase().replace(/[\s_]+/g, "-");
if (!TYPES[key]) { process.stderr.write(`unknown work type '${arg}': one of ${Object.keys(TYPES).join(", ")}\n`); process.exit(2); }
process.stdout.write(TYPES[key].map(l => `- [ ] ${l}`).join("\n") + "\n");
