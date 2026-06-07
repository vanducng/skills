#!/usr/bin/env node
// Convert a .dbml file -> er_html.py schema JSON (so DBML can be loaded into the interactive ERD).
// Requires @dbml/core:  npm i @dbml/core   (or:  npm i -g @dbml/cli  which bundles it)
// Usage:  node dbml_to_schema.mjs schema.dbml > schema.json
import { readFileSync } from "node:fs";

const file = process.argv[2];
if (!file) { console.error("usage: node dbml_to_schema.mjs <file.dbml> > schema.json"); process.exit(1); }

const { Parser } = await import("@dbml/core");
const db = new Parser().parse(readFileSync(file, "utf8"), "dbml");
const schema = db.schemas[0];

const tables = schema.tables.map((t) => {
  const pk = t.fields.filter((f) => f.pk).map((f) => f.name);
  const columns = t.fields.map((f, i) => ({
    column: f.name,
    type: f.type.type_name,
    udt: f.type.type_name,
    nullable: f.not_null || f.pk ? "NO" : "YES",
    default: f.dbdefault ? String(f.dbdefault.value) : null,
    ord: i + 1,
  }));
  const indexes = (t.indexes || []).map((ix) => ({
    name: ix.name || `${t.name}_${(ix.columns || []).map((c) => c.value).join("_")}`,
    def: `${ix.unique ? "UNIQUE " : ""}INDEX (${(ix.columns || []).map((c) => c.value).join(", ")})`,
  }));
  return { table: t.name, rows: 0, pk, columns, fks: [], indexes };
});
const byName = Object.fromEntries(tables.map((t) => [t.table, t]));

for (const ref of schema.refs || []) {
  const [a, b] = ref.endpoints;
  // the '*' (many) side holds the FK; fall back to the first endpoint
  const child = a.relation === "*" ? a : b.relation === "*" ? b : a;
  const parent = child === a ? b : a;
  const t = byName[child.tableName];
  if (!t) continue;
  const cf = child.fieldNames, pf = parent.fieldNames;       // composite-aware: one row per column pair
  const cons = `${child.tableName}_${cf.join("_")}_fkey`;
  cf.forEach((col, i) => t.fks.push({
    column: col,
    ref_table: parent.tableName,
    ref_column: pf[Math.min(i, pf.length - 1)],
    on_delete: (ref.onDelete || "NO ACTION").toUpperCase(),
    constraint: cons,
  }));
}

process.stdout.write(JSON.stringify(tables, null, 2));
