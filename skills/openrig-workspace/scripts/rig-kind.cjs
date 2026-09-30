#!/usr/bin/env node
// Maps a task kind to the rig template under $PROJECTS_ROOT/specs/rigs/<template>.
// feature requires --profile low|medium|high. bugfix and sop reject --profile.

const args = process.argv.slice(2);
const json = args.includes("--json");
const list = args.includes("--list");

function flag(name) {
  const i = args.indexOf(name);
  if (i === -1) return null;
  const value = args[i + 1];
  if (!value || value.startsWith("--")) return "";
  return value;
}

const kinds = {
  feature: {
    profiles: {
      low: {
        template: "feature-low",
        models: "default",
        sliceTemplate: "placeholder",
        seats: [{ id: "task.owner", model: "default" }],
        rule: "One seat writes the change. No review seat.",
      },
      medium: {
        template: "normal",
        models: "default",
        sliceTemplate: "placeholder",
        seats: [
          { id: "task.owner", model: "default" },
          { id: "task.impl", model: "default" },
          { id: "task.review", model: "default" },
        ],
        rule: "Owner coordinates. One writer. Fresh reviewer.",
      },
      high: {
        template: "feature-high",
        models: "role",
        sliceTemplate: "placeholder",
        seats: [
          { id: "lead.owner", model: "owner" },
          { id: "dev.impl", model: "implement" },
          { id: "product.pm", model: "design" },
          { id: "review.review", model: "review" },
        ],
        rule: "Lead agrees the plan with the operator before implementation. One writer. Fresh reviewer. Product seat for user-visible behavior.",
      },
    },
  },
  bugfix: {
    template: "bugfix",
    models: "default",
    sliceTemplate: "bug-fix",
    seats: [
      { id: "task.owner", model: "default" },
      { id: "task.impl", model: "default" },
      { id: "task.review", model: "default" },
    ],
    rule: "Reproduce the failure before any edit. Same seats as a medium feature.",
  },
  sop: {
    template: "sop",
    models: "default",
    sliceTemplate: "placeholder",
    seats: [{ id: "task.owner", model: "default" }],
    rule: "Follow the procedure already written for this org and project. One seat. Do not invent steps or extra seats.",
  },
};

function fail(message) {
  const payload = { ok: false, error: message };
  if (json) process.stdout.write(`${JSON.stringify(payload)}\n`);
  else process.stderr.write(`${message}\n`);
  process.exit(1);
}

function emit(payload) {
  if (json) {
    process.stdout.write(`${JSON.stringify({ ok: true, ...payload })}\n`);
    return;
  }
  const lines = [
    `kind: ${payload.kind}`,
    payload.profile ? `profile: ${payload.profile}` : null,
    `template: ${payload.template}`,
    `models: ${payload.models}`,
    `sliceTemplate: ${payload.sliceTemplate}`,
    `seats: ${payload.seats.map((s) => `${s.id}=${s.model}`).join(", ")}`,
    `rule: ${payload.rule}`,
  ].filter(Boolean);
  process.stdout.write(`${lines.join("\n")}\n`);
}

if (list) {
  const rows = [];
  rows.push({ kind: "feature", profile: "low", ...kinds.feature.profiles.low });
  rows.push({ kind: "feature", profile: "medium", ...kinds.feature.profiles.medium });
  rows.push({ kind: "feature", profile: "high", ...kinds.feature.profiles.high });
  rows.push({ kind: "bugfix", profile: null, ...kinds.bugfix });
  rows.push({ kind: "sop", profile: null, ...kinds.sop });
  if (json) process.stdout.write(`${JSON.stringify(rows)}\n`);
  else {
    for (const row of rows) {
      emit(row);
      process.stdout.write("\n");
    }
  }
  process.exit(0);
}

const kind = flag("--kind");
const profile = flag("--profile");
if (!kind) {
  fail("Pass --kind feature|bugfix|sop. feature also requires --profile low|medium|high.");
}
if (!Object.prototype.hasOwnProperty.call(kinds, kind)) {
  fail(`Unknown --kind ${kind}. Use feature, bugfix, or sop.`);
}

if (kind === "feature") {
  if (!profile) fail("feature requires --profile low|medium|high.");
  const chosen = kinds.feature.profiles[profile];
  if (!chosen) fail(`Unknown --profile ${profile}. Use low, medium, or high.`);
  emit({ kind, profile, ...chosen });
  process.exit(0);
}

if (profile) fail(`${kind} does not take --profile.`);
emit({ kind, profile: null, ...kinds[kind] });
