#!/usr/bin/env node
// Stand-in for the workbench skill's resolver, outside a rig: prints the bench record for --id.
const path = require("path");
const i = process.argv.indexOf("--id");
if (process.argv[2] !== "resolve" || i < 0 || !process.argv[i + 1]) { console.error("usage: records.cjs resolve --id <id>"); process.exit(2); }
const dir = path.join(process.cwd(), ".workbench", process.argv[i + 1]);
console.log(`mode: bench\ndir: ${dir}\nspec: ${dir}/SPEC.md\nprogress: ${dir}/PROGRESS.md`);
