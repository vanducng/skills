"use strict";
const test = require("node:test");
const assert = require("node:assert/strict");
const fs = require("node:fs");
const path = require("node:path");
const { check } = require("./check-message.cjs");

const rules = (text) => check(text).findings.map((f) => f.rule);
const GOOD = fs.readFileSync(path.join(__dirname, "../evals/04-clean-draft/fixture/message.md"), "utf8");

test("the clean eval draft passes", () => {
  assert.deepEqual(check(GOOD), { cards: 1, findings: [] });
});

test("a local path is flagged, a link is not", () => {
  assert.deepEqual(rules("Log at /srv/team/build.log.\n"), ["LOCAL_PATH"]);
  assert.deepEqual(rules("See `~/work/x`.\n"), ["LOCAL_PATH"]);
  assert.deepEqual(rules("See [the run](https://ci.example.com/var/runs/9).\n"), []);
});

test("unverified markdown is flagged outside code fences only", () => {
  assert.deepEqual(rules("| a | b |\n|---|---|\n| 1 | 2 |\n"), ["TABLE"]);
  assert.deepEqual(rules("- a\n  - b\n"), ["NESTED_LIST"]);
  assert.deepEqual(rules("> quoted\n"), ["BLOCKQUOTE"]);
  assert.deepEqual(rules("one<br>two\n"), ["HTML"]);
  assert.deepEqual(rules("```\n| a |\n|---|\n  - b\n```\n"), []);
});

test("a card has one question, options from A and one recommendation that is an option", () => {
  const card = (title, body) => `**Decision 1: ${title}**\n${body}\nReply with a letter, or in your own words.\n`;
  assert.deepEqual(rules(card("Merge now?", "A. Yes\nB. No\nRecommendation: A, it is green.")), []);
  assert.deepEqual(rules(card("Merge now? And deploy?", "A. Yes\nB. No\nRecommendation: A.")), ["ONE_QUESTION"]);
  assert.deepEqual(rules(card("Merge now?", "A. Yes\nC. No\nRecommendation: A.")), ["OPTIONS"]);
  assert.deepEqual(rules(card("Merge now?", "A. Yes\nB. No")), ["RECOMMENDATION"]);
  assert.deepEqual(rules(card("Merge now?", "A. Yes\nB. No\nRecommendation: C.")), ["RECOMMENDATION"]);
  assert.deepEqual(rules("**Decision 1: Merge now?**\nA. Yes\nB. No\nRecommendation: A.\n"), ["REPLY_HINT"]);
});

test("a long status is flagged", () => {
  assert.deepEqual(rules(`${"word ".repeat(81)}\n`), ["STATUS_LENGTH"]);
});
