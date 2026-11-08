#!/usr/bin/env node
// Maps a task kind to the rig template under $PROJECTS_ROOT/specs/rigs/<template>.
// feature requires --profile low|medium|high. bugfix, sop and content reject --profile.
// Seat ids are <pod>.<member> as in the template. `model` names the routing role that
// `fleet/bin/rig-to-pi convert` resolves for the seat, or `terminal` for the operator's Pi shell.

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

const seat = (id, model) => ({ id, model });
const solo = [seat("dev.build", "build")];
const studio = [seat("research.writer", "writer")];
const workshop = [
  seat("orch.human", "terminal"),
  seat("orch.lead", "lead"),
  seat("dev.build", "build"),
  seat("dev.qa", "qa"),
  seat("dev.review", "review"),
];
const factory = [
  seat("orch.human", "terminal"),
  seat("orch.lead", "lead"),
  seat("orch.advisor", "advisor"),
  seat("orch.pm", "pm"),
  seat("dev.build", "build"),
  seat("dev.qa", "qa"),
  seat("dev.design", "design"),
  seat("review.r1", "review"),
];

const kinds = {
  feature: {
    profiles: {
      low: {
        template: "solo",
        models: "role",
        sliceTemplate: "placeholder",
        seats: solo,
        rule: "One seat writes the change. No review seat.",
      },
      medium: {
        template: "workshop",
        models: "role",
        sliceTemplate: "placeholder",
        seats: workshop,
        rule: "Lead coordinates. One writer. QA runs the change; a fresh reviewer from another model family reads the pushed head.",
      },
      high: {
        template: "factory",
        models: "role",
        sliceTemplate: "placeholder",
        seats: factory,
        rule: "Lead agrees the plan with the operator before implementation. One writer. Design and PM seats for user-visible behavior; advisor for a second opinion. A second reviewer (review.r2) is added with rig add when the slice needs one.",
      },
    },
  },
  bugfix: {
    template: "workshop",
    models: "role",
    sliceTemplate: "bug-fix",
    seats: workshop,
    rule: "Reproduce the failure before any edit. Same seats as a medium feature.",
  },
  sop: {
    template: "solo",
    models: "role",
    sliceTemplate: "placeholder",
    seats: solo,
    rule: "Follow the procedure already written for this org and project. One seat. Do not invent steps or extra seats.",
  },
  content: {
    template: "studio",
    models: "role",
    sliceTemplate: "placeholder",
    seats: studio,
    rule: "Research, plan, write for one named reader. Sources with checked-on dates for every fact a reader acts on. Small site changes in scope. Publishing, deploys and messages to people wait for the operator.",
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
  rows.push({ kind: "content", profile: null, ...kinds.content });
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
  fail("Pass --kind feature|bugfix|sop|content. feature also requires --profile low|medium|high.");
}
if (!Object.prototype.hasOwnProperty.call(kinds, kind)) {
  fail(`Unknown --kind ${kind}. Use feature, bugfix, sop, or content.`);
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
