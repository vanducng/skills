#!/usr/bin/env node
// Lints a message for a person who reads it in Grok Bot (SKILL.md rules 1-5). Exit 0 clean, 1 findings, 2 usage.
"use strict";
const fs = require("node:fs");

const STATUS_MAX_WORDS = 80;
const LOCAL_PATH = /(^|[\s(`])(~\/|\/(Users|home|Volumes|private|tmp|var|opt|srv)\/)\S*/;
const TABLE_RULE = /^\s*\|?\s*:?-{3,}:?\s*\|/;
const NESTED_ITEM = /^\s{2,}([-*+]|\d+\.)\s/;
const BLOCKQUOTE = /^\s*>/;
const HTML = /<(details|summary|br|table|div|span|b|i|u)[\s/>]/i;
const CARD_TITLE = /^\*\*Decision (\d+): (.*)\*\*$/;
const OPTION = /^([A-D])\. \S/;
const RECOMMENDATION = /^Recommendation: ([A-D])\b/;
const REPLY_HINT = /reply with a letter/i;

function check(text) {
  const findings = [];
  const add = (line, rule, message) => findings.push({ line, rule, message });
  const lines = text.split(/\r?\n/);
  let fenced = false;
  let card = null;
  const cards = [];
  lines.forEach((raw, i) => {
    const n = i + 1;
    if (/^\s*```/.test(raw)) fenced = !fenced;
    if (fenced || /^\s*```/.test(raw)) return;
    const path = raw.match(LOCAL_PATH);
    if (path) add(n, "LOCAL_PATH", `a local path the person cannot open: ${path[0].trim()}; link it or say what it shows`);
    if (TABLE_RULE.test(raw)) add(n, "TABLE", "a table: rendering in Grok Bot is unverified; use a list");
    if (NESTED_ITEM.test(raw)) add(n, "NESTED_LIST", "a nested list: rendering in Grok Bot is unverified; flatten it");
    if (BLOCKQUOTE.test(raw)) add(n, "BLOCKQUOTE", "a blockquote: rendering in Grok Bot is unverified");
    if (HTML.test(raw)) add(n, "HTML", "raw HTML does not render in Grok Bot");
    const title = raw.match(CARD_TITLE);
    if (title) {
      card = { line: n, question: title[2], options: "", recommendations: [] };
      cards.push(card);
    } else if (card && OPTION.test(raw)) {
      card.options += raw[0];
    } else if (card && RECOMMENDATION.test(raw)) {
      card.recommendations.push(raw.match(RECOMMENDATION)[1]);
    }
  });
  for (const c of cards) {
    const marks = (c.question.match(/\?/g) || []).length;
    if (marks !== 1 || !c.question.endsWith("?")) add(c.line, "ONE_QUESTION", "a card title is one question ending in '?'; split the others into their own cards");
    if (!/^(AB|ABC|ABCD)$/.test(c.options)) add(c.line, "OPTIONS", `options are "${c.options}"; want 2 to 4 lettered from A`);
    if (c.recommendations.length !== 1) add(c.line, "RECOMMENDATION", `${c.recommendations.length} Recommendation lines; want exactly 1`);
    else if (!c.options.includes(c.recommendations[0])) add(c.line, "RECOMMENDATION", `recommends ${c.recommendations[0]}, which is not an option`);
  }
  const firstCard = cards.length ? cards[0].line - 1 : lines.length;
  const statusWords = lines.slice(0, firstCard).join(" ").split(/\s+/).filter(Boolean).length;
  if (statusWords > STATUS_MAX_WORDS) add(1, "STATUS_LENGTH", `the status is ${statusWords} words; keep it to ${STATUS_MAX_WORDS}`);
  if (cards.length && !REPLY_HINT.test(text)) add(lines.length, "REPLY_HINT", "end with 'Reply with a letter, or in your own words.'");
  return { cards: cards.length, findings };
}

function main(argv) {
  const json = argv.includes("--json");
  const files = argv.filter((a) => a !== "--json");
  if (files.length !== 1) {
    process.stderr.write("usage: check-message.cjs <message.md> [--json]\n");
    return 2;
  }
  const result = check(fs.readFileSync(files[0], "utf8"));
  if (json) process.stdout.write(JSON.stringify({ ok: result.findings.length === 0, ...result }) + "\n");
  else for (const f of result.findings) process.stdout.write(`${files[0]}:${f.line}: ${f.rule}: ${f.message}\n`);
  return result.findings.length ? 1 : 0;
}

if (require.main === module) process.exitCode = main(process.argv.slice(2));
module.exports = { check };
