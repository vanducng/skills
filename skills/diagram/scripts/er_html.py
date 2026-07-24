#!/usr/bin/env python3
"""Generate a self-contained interactive ERD as a single HTML file.

Deterministic (no LLM): takes a schema JSON (introspected from Postgres or any
source) + optional meta (domain groups, classifications, descriptions) and emits
one HTML file with a Cytoscape.js graph whose nodes are real HTML ER cards
(header band + group colour + PK/FK column styling) rendered via
cytoscape-node-html-label. Features:
- draggable nodes (edges follow), pan/zoom, re-layout
- single-click a table -> spotlight it + all its downstream relationships (transitive), dim the rest
- double-click a table -> details drawer (columns, types, PK/FK/audit, FK ON DELETE, incoming refs, indexes)
- live search, domain-group filters, audit/framework/columns toggles
- collapsible left (filters) + right (details) sidebars
- keyboard shortcuts + a ? help overlay

Schema JSON shape (list of tables):
  [{"table","rows","pk":[...],
    "columns":[{"column","type","udt","nullable","default","ord"}],
    "fks":[{"column","ref_table","ref_column","on_delete","constraint"}],
    "indexes":[{"name","def"}]}]

Meta JSON shape (all keys optional):
  {"title","groups":{name:{"color","tables":[...]}},
   "framework_tables":[...],"classifications":{table:str},
   "descriptions":{table:str},"audit_columns":[...]}

Usage:
  er_html.py --schema schema.json [--meta meta.json] [-o out.html] [--cdn]
  er_html.py --print-sql                      # emit the Postgres introspection SQL
  er_html.py --print-sql --dialect mysql      # emit the MySQL 8.0+/MariaDB 10.5+ introspection SQL
"""

from __future__ import annotations

import argparse
import json
import sys
import urllib.request
from pathlib import Path

# All ship self-contained UMD bundles (no dynamic chunk imports) → inlinable + offline.
CYTO_URL = "https://cdn.jsdelivr.net/npm/cytoscape@3.30.2/dist/cytoscape.min.js"
NHL_URL = "https://cdn.jsdelivr.net/npm/cytoscape-node-html-label@1.2.2/dist/cytoscape-node-html-label.min.js"

INTROSPECT_SQL = r"""
WITH cols AS (
  SELECT c.table_name, json_agg(json_build_object(
    'column', c.column_name, 'type', c.data_type, 'udt', c.udt_name,
    'nullable', c.is_nullable, 'default', c.column_default, 'ord', c.ordinal_position
  ) ORDER BY c.ordinal_position) AS columns
  FROM information_schema.columns c WHERE c.table_schema='public' GROUP BY c.table_name),
pks AS (
  SELECT tc.table_name, json_agg(kcu.column_name) AS pk_cols
  FROM information_schema.table_constraints tc
  JOIN information_schema.key_column_usage kcu ON tc.constraint_name=kcu.constraint_name
  WHERE tc.constraint_type='PRIMARY KEY' AND tc.table_schema='public' GROUP BY tc.table_name),
fks AS (
  -- pg_catalog with positional pairing: conkey[i] ↔ confkey[i] (correct for composite FKs; no cartesian)
  SELECT c.conrelid::regclass::text AS table_name, json_agg(json_build_object(
    'column', a.attname, 'ref_table', c.confrelid::regclass::text, 'ref_column', af.attname,
    'on_delete', CASE c.confdeltype WHEN 'c' THEN 'CASCADE' WHEN 'n' THEN 'SET NULL' WHEN 'd' THEN 'SET DEFAULT' WHEN 'r' THEN 'RESTRICT' ELSE 'NO ACTION' END,
    'constraint', c.conname) ORDER BY k.ord) AS fks
  FROM pg_constraint c
  JOIN LATERAL unnest(c.conkey) WITH ORDINALITY AS k(attnum,ord) ON true
  JOIN pg_attribute a ON a.attrelid=c.conrelid AND a.attnum=k.attnum
  JOIN LATERAL unnest(c.confkey) WITH ORDINALITY AS kf(attnum,ford) ON kf.ford=k.ord
  JOIN pg_attribute af ON af.attrelid=c.confrelid AND af.attnum=kf.attnum
  WHERE c.contype='f' AND c.connamespace='public'::regnamespace
  GROUP BY c.conrelid),
idx AS (
  SELECT tablename AS table_name, json_agg(json_build_object('name', indexname, 'def', indexdef)) AS indexes
  FROM pg_indexes WHERE schemaname='public' GROUP BY tablename),
rc AS (SELECT relname AS table_name, n_live_tup AS rows FROM pg_stat_user_tables)
SELECT json_agg(json_build_object(
  'table', t.table_name, 'rows', COALESCE(rc.rows,0), 'pk', COALESCE(pk.pk_cols,'[]'::json),
  'columns', cols.columns, 'fks', COALESCE(fk.fks,'[]'::json), 'indexes', COALESCE(i.indexes,'[]'::json)
) ORDER BY t.table_name)
FROM (SELECT table_name FROM information_schema.tables WHERE table_schema='public' AND table_type='BASE TABLE') t
JOIN cols ON cols.table_name=t.table_name
LEFT JOIN pks pk ON pk.table_name=t.table_name
LEFT JOIN fks fk ON fk.table_name=t.table_name
LEFT JOIN idx i ON i.table_name=t.table_name
LEFT JOIN rc ON rc.table_name=t.table_name;
"""

# MySQL 8.0+ / MariaDB 10.5+ (needs JSON_ARRAYAGG). Run against the target DB so DATABASE() resolves:
#   mysql -N --raw -D <db> -e "$(er_html.py --print-sql --dialect mysql)" > schema.json
# --raw is required: default --batch mode escapes control chars and corrupts the embedded JSON.
# Array element order is undefined here (JSON_ARRAYAGG); er_html sorts columns by `ord` on load.
INTROSPECT_SQL_MYSQL = r"""
SELECT JSON_ARRAYAGG(JSON_OBJECT(
  'table', t.TABLE_NAME,
  'rows', COALESCE(t.TABLE_ROWS,0),
  'pk', COALESCE((SELECT JSON_ARRAYAGG(pk.COLUMN_NAME) FROM (
          SELECT COLUMN_NAME FROM information_schema.KEY_COLUMN_USAGE
          WHERE TABLE_SCHEMA=DATABASE() AND TABLE_NAME=t.TABLE_NAME AND CONSTRAINT_NAME='PRIMARY'
          ORDER BY ORDINAL_POSITION) pk), JSON_ARRAY()),
  'columns', (SELECT JSON_ARRAYAGG(JSON_OBJECT(
          'column', c.COLUMN_NAME, 'type', c.DATA_TYPE, 'udt', c.COLUMN_TYPE,
          'nullable', c.IS_NULLABLE, 'default', c.COLUMN_DEFAULT, 'ord', c.ORDINAL_POSITION))
        FROM information_schema.COLUMNS c
        WHERE c.TABLE_SCHEMA=DATABASE() AND c.TABLE_NAME=t.TABLE_NAME),
  'fks', COALESCE((SELECT JSON_ARRAYAGG(JSON_OBJECT(
          'column', kcu.COLUMN_NAME, 'ref_table', kcu.REFERENCED_TABLE_NAME,
          'ref_column', kcu.REFERENCED_COLUMN_NAME, 'on_delete', rc.DELETE_RULE,
          'constraint', kcu.CONSTRAINT_NAME))
        FROM information_schema.KEY_COLUMN_USAGE kcu
        JOIN information_schema.REFERENTIAL_CONSTRAINTS rc
          ON rc.CONSTRAINT_SCHEMA=kcu.TABLE_SCHEMA AND rc.CONSTRAINT_NAME=kcu.CONSTRAINT_NAME
        WHERE kcu.TABLE_SCHEMA=DATABASE() AND kcu.TABLE_NAME=t.TABLE_NAME
          AND kcu.REFERENCED_TABLE_NAME IS NOT NULL), JSON_ARRAY()),
  'indexes', COALESCE((SELECT JSON_ARRAYAGG(idx.ix) FROM (
          SELECT JSON_OBJECT('name', s.INDEX_NAME, 'def',
            CONCAT(IF(MAX(s.NON_UNIQUE)=0,'UNIQUE INDEX ','INDEX '), s.INDEX_NAME,
                   ' (', GROUP_CONCAT(s.COLUMN_NAME ORDER BY s.SEQ_IN_INDEX SEPARATOR ', '), ')')) AS ix
          FROM information_schema.STATISTICS s
          WHERE s.TABLE_SCHEMA=DATABASE() AND s.TABLE_NAME=t.TABLE_NAME AND s.INDEX_NAME<>'PRIMARY'
          GROUP BY s.INDEX_NAME) idx), JSON_ARRAY())
)) AS schema_json
FROM information_schema.TABLES t
WHERE t.TABLE_SCHEMA=DATABASE() AND t.TABLE_TYPE='BASE TABLE';
"""

INTROSPECT_SQL_BY_DIALECT = {"postgres": INTROSPECT_SQL, "mysql": INTROSPECT_SQL_MYSQL}


def _fetch(url: str) -> str:
    with urllib.request.urlopen(url, timeout=30) as r:  # noqa: S310
        return r.read().decode("utf-8")


_DBML_TYPE = {
    "int4": "int", "int8": "bigint", "int2": "smallint", "bool": "boolean", "varchar": "varchar",
    "text": "text", "float8": "float", "float4": "float", "numeric": "numeric", "jsonb": "jsonb",
    "json": "json", "uuid": "uuid", "bytea": "bytea", "timestamp": "timestamp", "timestamptz": "timestamptz",
    "date": "date", "time": "time", "vector": "vector", "tsvector": "tsvector",
}
_DBML_DELETE = {"CASCADE": "cascade", "SET NULL": "set null", "SET DEFAULT": "set default", "RESTRICT": "restrict"}


def emit_dbml(schema: list[dict], meta: dict) -> str:
    """Render the schema JSON as DBML (dbdiagram.io / dbdocs.io format)."""
    out: list[str] = [f'Project "{meta.get("title", "database")}" {{\n  database_type: \'{meta.get("database_type", "PostgreSQL")}\'\n}}\n']
    for t in sorted(schema, key=lambda x: x["table"]):
        pk = set(t.get("pk") or [])
        out.append(f'Table {t["table"]} {{')
        for c in t["columns"]:
            ty = _DBML_TYPE.get(c.get("udt", ""), c.get("udt") or c.get("type") or "text")
            s = []
            if c["column"] in pk:
                s.append("pk")
            if c.get("nullable") == "NO" and c["column"] not in pk:
                s.append("not null")
            seg = f"  {c['column']} {ty}"
            if s:
                seg += f" [{', '.join(s)}]"
            out.append(seg)
        out.append("}\n")
    # relationships (long form, with ON DELETE) - child.col > parent.col (many-to-one); composite = one Ref
    for t in sorted(schema, key=lambda x: x["table"]):
        groups: dict[str, dict] = {}
        for f in t.get("fks") or []:
            g = groups.setdefault(f.get("constraint") or f["column"], {"cols": [], "rcols": [], "ref": f["ref_table"], "od": f.get("on_delete")})
            g["cols"].append(f["column"])
            g["rcols"].append(f["ref_column"])
        for g in groups.values():
            d = _DBML_DELETE.get((g["od"] or "").upper())
            setting = f" [delete: {d}]" if d else ""
            if len(g["cols"]) > 1:
                lhs, rhs = f'{t["table"]}.({", ".join(g["cols"])})', f'{g["ref"]}.({", ".join(g["rcols"])})'
            else:
                lhs, rhs = f'{t["table"]}.{g["cols"][0]}', f'{g["ref"]}.{g["rcols"][0]}'
            out.append(f"Ref: {lhs} > {rhs}{setting}")
    # domain groups → TableGroups
    for g, info in (meta.get("groups") or {}).items():
        tbls = [x for x in (info.get("tables") or []) if any(s["table"] == x for s in schema)]
        if tbls:
            out.append(f'\nTableGroup "{g}" {{\n' + "\n".join(f"  {x}" for x in tbls) + "\n}")
    return "\n".join(out) + "\n"


def _esc(s: str) -> str:
    return s.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")


def build_html(schema: list[dict], meta: dict, *, cdn: bool) -> str:
    title = meta.get("title", "Database - Entity Relationship Diagram")
    payload = json.dumps({"schema": schema, "meta": meta}, separators=(",", ":"))
    if cdn:
        head_libs = f'<script src="{CYTO_URL}"></script>\n<script src="{NHL_URL}"></script>'
    else:
        try:
            cyto, nhl = _fetch(CYTO_URL), _fetch(NHL_URL)
        except Exception as exc:  # noqa: BLE001
            print(f"[er_html] asset inline failed ({exc}); falling back to CDN", file=sys.stderr)
            return build_html(schema, meta, cdn=True)
        head_libs = f"<script>{cyto}</script>\n<script>{nhl}</script>"
    return _TEMPLATE.replace("__TITLE__", _esc(title)).replace("__LIBS__", head_libs).replace("__PAYLOAD__", payload)


def main() -> int:
    ap = argparse.ArgumentParser(description="Generate a self-contained interactive ERD HTML.")
    ap.add_argument("--schema", help="Path to schema JSON.")
    ap.add_argument("--meta", help="Path to meta JSON (groups/classifications/descriptions).")
    ap.add_argument("-o", "--out", default="erd.html", help="Output HTML path.")
    ap.add_argument("--cdn", action="store_true", help="Link libs from CDN instead of inlining (smaller file, needs internet).")
    ap.add_argument("--print-sql", action="store_true", help="Print the introspection SQL for --dialect and exit.")
    ap.add_argument("--dialect", choices=sorted(INTROSPECT_SQL_BY_DIALECT), default="postgres",
                    help="SQL dialect for --print-sql (default: postgres).")
    ap.add_argument("--emit-dbml", metavar="FILE", help="Write the schema as DBML (dbdocs/dbdiagram) instead of HTML.")
    args = ap.parse_args()

    if args.print_sql:
        print(INTROSPECT_SQL_BY_DIALECT[args.dialect].strip())
        return 0
    if not args.schema:
        ap.error("--schema is required (or use --print-sql)")

    schema = json.loads(Path(args.schema).read_text())
    for t in schema:  # MySQL JSON_ARRAYAGG order is undefined; the details drawer renders columns in array order
        t.get("columns", []).sort(key=lambda c: c.get("ord") or 0)
    meta = json.loads(Path(args.meta).read_text()) if args.meta else {}
    if args.emit_dbml:
        Path(args.emit_dbml).write_text(emit_dbml(schema, meta))
        print(f"[er_html] wrote {Path(args.emit_dbml).resolve()} (DBML, {len(schema)} tables)")
        return 0
    html = build_html(schema, meta, cdn=args.cdn)
    out = Path(args.out)
    out.write_text(html)
    print(f"[er_html] wrote {out.resolve()} ({len(html) // 1024} KB, {len(schema)} tables)")
    return 0


_TEMPLATE = r"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8"/>
<meta name="viewport" content="width=device-width, initial-scale=1"/>
<title>__TITLE__</title>
__LIBS__
<style>
:root{
  --bg:#0f1419; --panel:#161c24; --panel2:#1b232d; --line:#2a3441; --line2:#374352;
  --ink:#e6edf3; --muted:#8b98a8; --accent:#4ea1ff;
  --pk:#ffd479; --fk:#7ee0c0; --cascade:#ff7b72; --setnull:#79c0ff; --noaction:#8b98a8; --chip:#222c38;
}
*{box-sizing:border-box}
html,body{margin:0;height:100%;background:var(--bg);color:var(--ink);
  font:14px/1.45 -apple-system,BlinkMacSystemFont,"Segoe UI",Roboto,Helvetica,Arial,sans-serif}
#app{display:grid;grid-template-columns:300px 1fr;grid-template-rows:52px 1fr;height:100vh;transition:grid-template-columns .16s ease}
#app.lhide{grid-template-columns:0 1fr}
#app.lhide aside{transform:translateX(-100%)}
header{grid-column:1/3;display:flex;align-items:center;gap:14px;padding:0 14px;background:var(--panel);border-bottom:1px solid var(--line)}
header h1{font-size:15px;font-weight:600;margin:0;white-space:nowrap;overflow:hidden;text-overflow:ellipsis;max-width:32vw}
header .stats{color:var(--muted);font-size:12px;display:flex;gap:14px;flex-wrap:wrap}
header .stats b{color:var(--ink);font-weight:600}
header .spacer{flex:1}
button.tool{background:var(--chip);color:var(--ink);border:1px solid var(--line2);border-radius:7px;padding:6px 10px;cursor:pointer;font-size:12px}
button.tool:hover{border-color:var(--accent)}
aside{background:var(--panel);border-right:1px solid var(--line);overflow-y:auto;padding:12px;transition:transform .16s ease}
aside h2{font-size:11px;letter-spacing:.08em;text-transform:uppercase;color:var(--muted);margin:16px 0 8px}
aside h2:first-child{margin-top:0}
.gtools{float:right;font-weight:400}
.gtools a{color:var(--accent);cursor:pointer;margin-left:9px;text-transform:none;letter-spacing:0}
.gtools a:hover{text-decoration:underline}
.search{width:100%;background:var(--panel2);border:1px solid var(--line2);border-radius:8px;color:var(--ink);padding:8px 10px;font-size:13px}
.search:focus{outline:none;border-color:var(--accent)}
.toggle{display:flex;align-items:center;gap:8px;padding:5px 2px;cursor:pointer;color:var(--ink);user-select:none}
.toggle input{accent-color:var(--accent);width:15px;height:15px}
.grp{display:flex;align-items:center;gap:8px;padding:5px 2px;cursor:pointer;border-radius:6px}
.grp:hover{background:var(--panel2)}
.grp .dot{width:11px;height:11px;border-radius:3px;flex:none}
.grp .gname{flex:1;font-size:13px}.grp .gn{color:var(--muted);font-size:11px}
.tlist{display:flex;flex-direction:column;gap:1px;margin-top:4px}
.titem{display:flex;align-items:center;gap:8px;padding:5px 8px;border-radius:6px;cursor:pointer;font-size:13px}
.titem:hover{background:var(--panel2)}
.titem.sel{background:#243244;outline:1px solid var(--accent)}
.titem .dot{width:8px;height:8px;border-radius:2px;flex:none}
.titem .tn{flex:1;overflow:hidden;text-overflow:ellipsis;white-space:nowrap}
.titem .rc{color:var(--muted);font-size:11px}
.titem .eye{flex:none;color:var(--muted);font-size:12px;opacity:.55;width:14px;text-align:center}
.titem:hover .eye{opacity:1}
.titem .eye:hover{color:var(--accent)}
.titem.off{opacity:.5}
.titem.off .tn{text-decoration:line-through}
.showhidden{font-size:12px;color:var(--accent);cursor:pointer;padding:5px 8px;margin-bottom:2px}
.showhidden:hover{text-decoration:underline}
.titem.hide{display:none}
main{position:relative;overflow:hidden;background:radial-gradient(circle at 1px 1px,#1c2530 1px,transparent 0) 0 0/22px 22px,var(--bg)}
#cy{width:100%;height:100%;position:absolute;inset:0;z-index:1}
#hull{position:absolute;inset:0;width:100%;height:100%;pointer-events:none;z-index:0}
#minimap{position:absolute;right:14px;top:14px;width:200px;height:130px;background:rgba(15,20,25,.88);
  border:1px solid var(--line2);border-radius:8px;overflow:hidden;z-index:6;display:none;cursor:pointer}
#minimap.on{display:block}
#minimap canvas{display:block;width:100%;height:100%}
/* ER card (rendered as an HTML node label by cytoscape-node-html-label) */
.erd-card{width:230px;background:var(--panel2);border:1px solid color-mix(in srgb,var(--c) 50%,var(--line));
  border-radius:9px;overflow:hidden;font-family:ui-monospace,SFMono-Regular,Menlo,monospace;
  box-shadow:0 6px 18px rgba(0,0,0,.35);transition:opacity .12s}
.erd-h{display:flex;align-items:center;gap:7px;padding:6px 10px;font-size:12.5px;font-weight:600;color:var(--ink);
  background:color-mix(in srgb,var(--c) 22%,var(--panel));border-bottom:2px solid var(--c)}
.erd-dot{width:9px;height:9px;border-radius:3px;background:var(--c);flex:none}
.erd-name{flex:1;min-width:0;overflow:hidden;text-overflow:ellipsis;white-space:nowrap;font-family:-apple-system,Segoe UI,Roboto,sans-serif;letter-spacing:.01em}
.erd-meta{color:var(--muted);font-size:10px;font-weight:500}
.erd-cols{padding:4px 0}
.erd-col{display:flex;align-items:center;gap:6px;height:17px;line-height:17px;padding:0 10px;font-size:11px;white-space:nowrap}
.erd-col .g{width:11px;text-align:center;flex:none;font-size:10px}
.erd-col .g.pk{color:var(--pk)}.erd-col .g.fk{color:var(--fk)}.erd-col .g.au{color:var(--accent)}.erd-col .g.x{color:#4a5666}
.erd-col .cn{flex:1;color:var(--ink);overflow:hidden;text-overflow:ellipsis}
.erd-col .ct{color:var(--muted);font-size:10px}
.erd-col.more{color:var(--muted);font-style:italic;font-size:10px;padding-left:27px}
.erd-col.hot{background:color-mix(in srgb,var(--c) 30%,transparent);border-left:2px solid var(--c)}
.erd-col.hot .cn{color:#fff;font-weight:700}
.erd-card{pointer-events:none}
.erd-ex{margin-left:5px;flex:none;color:var(--muted);font-size:13px;line-height:1;cursor:pointer;pointer-events:auto}
.erd-ex:hover{color:var(--ink)}
.erd-hide{margin-left:3px;font-size:15px}
.erd-hide:hover{color:var(--cascade)}
.erd-col.more.erd-exp{pointer-events:auto;cursor:pointer}
.erd-col.more.erd-exp:hover{color:var(--accent)}
.mini{margin-left:auto;background:var(--panel2);color:var(--ink);border:1px solid var(--line2);border-radius:6px;padding:2px 7px;font-size:12px}
.erd-card.fade{opacity:.3}
.erd-card.dim{opacity:.12}
.erd-card.hi{opacity:1}
.erd-card.sel{box-shadow:0 0 0 2px #fff,0 8px 22px rgba(0,0,0,.5)}
.erd-card.gone{display:none}
.hint{position:absolute;left:50%;top:14px;transform:translateX(-50%);background:var(--panel);border:1px solid var(--line2);border-radius:20px;padding:6px 14px;color:var(--muted);font-size:12px;pointer-events:none}
.legend{position:absolute;left:14px;bottom:14px;background:rgba(22,28,36,.92);border:1px solid var(--line);border-radius:10px;padding:10px 12px;font-size:11px;color:var(--muted);max-width:230px}
.legend b{color:var(--ink);display:block;margin:8px 0 6px;font-size:11px;letter-spacing:.05em;text-transform:uppercase}
.legend b:first-child{margin-top:0}
.legend .row{display:flex;align-items:center;gap:7px;margin:3px 0}
.legend .sw{width:22px;height:0;border-top-width:3px;border-top-style:solid}
.legend .bx{width:11px;height:11px;border-radius:3px}
.zoombar{position:absolute;right:14px;bottom:14px;display:flex;gap:6px}
.zoombar button{width:34px;height:34px;border-radius:8px;background:var(--panel);border:1px solid var(--line2);color:var(--ink);font-size:17px;cursor:pointer}
.zoombar button:hover{border-color:var(--accent)}
#docs{position:absolute;top:0;right:0;height:100%;width:440px;max-width:92vw;background:var(--panel);border-left:1px solid var(--line);transform:translateX(100%);transition:transform .18s ease;overflow-y:auto;box-shadow:-12px 0 30px rgba(0,0,0,.35);z-index:8}
#docs.open{transform:translateX(0)}
#docs .dh{position:sticky;top:0;background:var(--panel);border-bottom:1px solid var(--line);padding:16px;display:flex;align-items:flex-start;gap:10px}
#docs .dh .tt{flex:1}#docs .dh h3{margin:0 0 4px;font-size:17px;font-family:ui-monospace,SFMono-Regular,Menlo,monospace}
#docs .dh .cls{font-size:12px;color:var(--muted)}
.x{cursor:pointer;color:var(--muted);font-size:20px;line-height:1;background:none;border:none}
#docs .body{padding:16px}#docs .desc{color:var(--muted);font-size:13px;margin:0 0 14px}
.badges{display:flex;flex-wrap:wrap;gap:6px;margin-bottom:14px}
.badge{font-size:11px;padding:2px 8px;border-radius:20px;background:var(--chip);border:1px solid var(--line2)}
table.cols{width:100%;border-collapse:collapse;font-size:12.5px}
table.cols th{text-align:left;color:var(--muted);font-weight:600;font-size:11px;text-transform:uppercase;letter-spacing:.04em;padding:6px 8px;border-bottom:1px solid var(--line2)}
table.cols td{padding:6px 8px;border-bottom:1px solid var(--line);vertical-align:top}
table.cols td.cn{font-family:ui-monospace,Menlo,monospace;color:var(--ink)}
table.cols td.ty{font-family:ui-monospace,Menlo,monospace;color:var(--muted);font-size:11.5px}
.k{font-size:10px;font-weight:700;padding:1px 5px;border-radius:4px;margin-left:5px}
.k.pk{background:rgba(255,212,121,.16);color:var(--pk)}.k.fk{background:rgba(126,224,192,.14);color:var(--fk)}
.k.au{background:rgba(78,161,255,.13);color:var(--accent)}.k.nn{color:var(--muted);background:var(--chip)}
.reltbl{width:100%;border-collapse:collapse;font-size:12.5px;margin-top:6px}
.reltbl td{padding:5px 8px;border-bottom:1px solid var(--line)}
.od{font-size:10px;font-weight:700;padding:1px 6px;border-radius:4px}
.od.CASCADE{background:rgba(255,123,114,.16);color:var(--cascade)}
.od.SETNULL{background:rgba(121,192,255,.16);color:var(--setnull)}
.od.NOACTION{background:var(--chip);color:var(--noaction)}
#docs h4{font-size:11px;letter-spacing:.07em;text-transform:uppercase;color:var(--muted);margin:18px 0 6px}
code.mono{font-family:ui-monospace,Menlo,monospace;font-size:11.5px;color:var(--muted);word-break:break-all}
.empty{color:var(--muted);font-style:italic;font-size:12px}
.kbd-q{display:inline-block;min-width:15px;text-align:center;border:1px solid var(--line2);border-radius:4px;padding:0 4px;font:600 11px ui-monospace,Menlo,monospace;background:var(--bg)}
kbd{display:inline-block;min-width:18px;text-align:center;border:1px solid var(--line2);border-bottom-width:2px;border-radius:5px;padding:1px 6px;font:600 11px ui-monospace,Menlo,monospace;background:var(--panel2);color:var(--ink)}
.ov{position:absolute;inset:0;background:rgba(6,9,13,.6);backdrop-filter:blur(2px);display:none;align-items:center;justify-content:center;z-index:20}
.ov.open{display:flex}
.ovpanel{background:var(--panel);border:1px solid var(--line2);border-radius:14px;width:660px;max-width:92vw;max-height:86vh;overflow:auto;box-shadow:0 24px 60px rgba(0,0,0,.5)}
.dbmlsub{font-size:11px;color:var(--muted);font-weight:400;margin-left:8px}
.dbmlsrc{margin:0;padding:14px 18px;font-family:ui-monospace,SFMono-Regular,Menlo,monospace;font-size:12px;line-height:1.55;color:var(--ink);white-space:pre;overflow:auto;max-height:76vh;tab-size:2}
.dbmlsrc .kw{color:var(--accent)}
.ovh{display:flex;align-items:center;justify-content:space-between;padding:16px 18px;border-bottom:1px solid var(--line)}
.ovh h3{margin:0;font-size:15px}
.ovbody{display:grid;grid-template-columns:1fr 1fr;gap:10px 28px;padding:16px 18px}
.ovcol h4{margin:0 0 8px;font-size:11px;letter-spacing:.07em;text-transform:uppercase;color:var(--muted)}
.kr{display:flex;align-items:center;gap:10px;padding:4px 0;font-size:13px;color:var(--ink)}
.kr span:first-child{flex:none;min-width:104px;color:var(--muted)}
.ovtip{padding:12px 18px 18px;color:var(--muted);font-size:12.5px;border-top:1px solid var(--line)}
.ovtip code{font-family:ui-monospace,Menlo,monospace;font-size:11.5px;color:var(--ink)}
.ins-grp{font-size:11px;letter-spacing:.06em;text-transform:uppercase;color:var(--muted);margin:14px 0 6px}
.ins-grp:first-child{margin-top:0}
.ins-row{display:flex;gap:8px;align-items:baseline;padding:5px 8px;border-radius:6px;cursor:pointer;font-size:12.5px}
.ins-row:hover{background:var(--panel2)}
.ins-row .tb{font-family:ui-monospace,Menlo,monospace;color:var(--ink);flex:none;min-width:140px}
.ins-row .ms{color:var(--muted)}
.ins-sev{width:7px;height:7px;border-radius:50%;flex:none;align-self:center}
.ins-sev.warn{background:var(--accent2,#ffb454)}.ins-sev.info{background:#5a6878}
.ins-ok{color:var(--fk);font-size:13px}
@media(max-width:560px){.ovbody{grid-template-columns:1fr}}
</style>
</head>
<body>
<div id="app">
  <header>
    <button class="tool" id="btnLeft" title="Toggle filters panel ([)">☰</button>
    <h1>__TITLE__</h1>
    <div class="stats" id="stats"></div>
    <div class="spacer"></div>
    <button class="tool" id="btnAll">Clear</button>
    <button class="tool" id="btnInsights" title="Schema insights">⚑ Insights</button>
    <button class="tool" id="btnDbml" title="View DBML source (dbdiagram.io / dbdocs)">DBML</button>
    <button class="tool" id="btnShare" title="Copy a shareable link (state in URL)">🔗 Share</button>
    <button class="tool" id="btnLayout" title="Re-run layout (g)">Re-layout</button>
    <button class="tool" id="btnFit" title="Fit (f)">Fit</button>
    <button class="tool" id="btnReset">Reset</button>
    <button class="tool" id="btnHelp" title="Keyboard shortcuts (?)">⌨ <span class="kbd-q">?</span></button>
  </header>
  <aside>
    <h2>Search</h2>
    <input class="search" id="search" placeholder="Filter tables / columns…" autocomplete="off"/>
    <h2>View options</h2>
    <label class="toggle"><input type="checkbox" id="optCols" checked/> Columns on nodes</label>
    <label class="toggle"><input type="checkbox" id="optAudit"/> Show audit columns</label>
    <label class="toggle"><input type="checkbox" id="optFramework"/> Show framework tables</label>
    <label class="toggle"><input type="checkbox" id="optDim" checked/> Dim unrelated on select</label>
    <label class="toggle"><input type="checkbox" id="optFocus"/> Focus selected (hide others)</label>
    <label class="toggle"><input type="checkbox" id="optGroupAreas"/> Group areas (hulls)</label>
    <label class="toggle">Highlight depth <select id="optDepth" class="mini"><option value="1" selected>1 hop</option><option value="2">2 hops</option><option value="3">3 hops</option><option value="99">All</option></select></label>
    <h2>Find path</h2>
    <select class="search" id="pathFrom" style="margin-bottom:6px"></select>
    <select class="search" id="pathTo" style="margin-bottom:6px"></select>
    <div style="display:flex;gap:6px"><button class="tool" id="btnPath" style="flex:1">Find path</button><button class="tool" id="btnPathClear">Clear</button></div>
    <div id="pathMsg" style="color:var(--muted);font-size:11.5px;margin-top:6px"></div>
    <h2>Domain groups<span class="gtools"><a id="grpAll">all</a><a id="grpNone">clear</a></span></h2>
    <div id="groups"></div>
    <h2>Tables</h2>
    <div class="tlist" id="tlist"></div>
  </aside>
  <main>
    <canvas id="hull"></canvas>
    <div id="cy"></div>
    <div id="minimap"><canvas id="mmcv"></canvas></div>
    <div class="hint" id="hint">click table = highlight • click line = show the two joined tables • double-click = details • drag to arrange • ? for shortcuts</div>
    <div class="legend" id="legend"></div>
    <div class="zoombar">
      <button id="zin" title="Zoom in (+)">+</button><button id="zout" title="Zoom out (−)">−</button><button id="zfit" title="Fit (f)">⤢</button>
    </div>
    <div id="docs">
      <div class="dh"><div class="tt"><h3 id="dTitle"></h3><div class="cls" id="dCls"></div></div><button class="x" id="dClose">×</button></div>
      <div class="body" id="dBody"></div>
    </div>
    <div id="help" class="ov"><div class="ovpanel">
      <div class="ovh"><h3>Keyboard shortcuts &amp; how to use</h3><button class="x" id="helpClose">×</button></div>
      <div class="ovbody">
        <div class="ovcol">
          <h4>Canvas</h4>
          <div class="kr"><span><kbd>click</kbd></span><span>highlight a table + all its children's relationships</span></div>
          <div class="kr"><span><kbd>double-click</kbd></span><span>open entity details</span></div>
          <div class="kr"><span>click <kbd>line</kbd></span><span>spotlight the two joined tables + their join columns</span></div>
          <div class="kr"><span><kbd>drag</kbd></span><span>move a node (edges follow)</span></div>
          <div class="kr"><span><kbd>scroll</kbd></span><span>zoom · drag bg = pan</span></div>
          <div class="kr"><span><kbd>+</kbd> <kbd>−</kbd></span><span>zoom in / out</span></div>
          <div class="kr"><span><kbd>f</kbd> / <kbd>0</kbd></span><span>fit &amp; center</span></div>
          <div class="kr"><span><kbd>g</kbd></span><span>re-run layout</span></div>
        </div>
        <div class="ovcol">
          <h4>Filter &amp; panels</h4>
          <div class="kr"><span><kbd>/</kbd></span><span>focus search</span></div>
          <div class="kr"><span><kbd>a</kbd></span><span>toggle audit columns</span></div>
          <div class="kr"><span><kbd>t</kbd></span><span>toggle framework tables</span></div>
          <div class="kr"><span><kbd>c</kbd></span><span>toggle columns on nodes</span></div>
          <div class="kr"><span><kbd>n</kbd></span><span>toggle dim-unrelated</span></div>
          <div class="kr"><span><kbd>[</kbd></span><span>toggle filters sidebar</span></div>
          <div class="kr"><span><kbd>]</kbd></span><span>toggle details sidebar</span></div>
          <div class="kr"><span>card <kbd>×</kbd></span><span>hide entity (sidebar ◉ eye / "show N hidden" to restore)</span></div>
          <div class="kr"><span><kbd>s</kbd></span><span>clear selection</span></div>
          <div class="kr"><span><kbd>r</kbd></span><span>reset filters &amp; layout</span></div>
          <div class="kr"><span><kbd>Esc</kbd></span><span>close help / details / clear</span></div>
        </div>
      </div>
      <div class="ovtip">Also: <b>Find path</b> (sidebar) traces the shortest FK chain between two tables · <b>⚑ Insights</b> lints the schema (missing PK, FK type mismatch, unindexed FK, orphans) · <b>Group areas</b> draws domain hulls · the <b>minimap</b> (top-right) navigates · <b>🔗 Share</b> copies a link with your filters &amp; selection; dragged positions are saved automatically.</div>
    </div></div>
    <div id="insights" class="ov"><div class="ovpanel">
      <div class="ovh"><h3>Schema insights</h3><button class="x" id="insClose">×</button></div>
      <div class="body" id="insBody" style="padding:16px"></div>
    </div></div>
    <div id="dbml" class="ov"><div class="ovpanel">
      <div class="ovh"><h3>DBML<span class="dbmlsub">dbdiagram.io / dbdocs source</span></h3><div style="display:flex;gap:8px;align-items:center"><button class="tool" id="dbmlCopy">Copy</button><button class="x" id="dbmlClose">×</button></div></div>
      <pre class="dbmlsrc" id="dbmlSrc"></pre>
    </div></div>
  </main>
</div>
<script id="data" type="application/json">__PAYLOAD__</script>
<script>
const DATA=JSON.parse(document.getElementById('data').textContent);
const SCHEMA=DATA.schema, META=DATA.meta||{};
const AUDIT=new Set(META.audit_columns||["created_at","updated_at","created_by","updated_by","deleted_at"]);
const FRAMEWORK=new Set(META.framework_tables||[]);
const GROUPS=META.groups||{};
const PALETTE=["#4ea1ff","#ffb454","#7ee0c0","#c792ea","#f78c6c","#82aaff","#addb67","#ff5370","#89ddff","#f07178"];
const byName={}; SCHEMA.forEach(t=>byName[t.table]=t);
const tgroup={}, gcolor={};
Object.entries(GROUPS).forEach(([g,info],i)=>{gcolor[g]=info.color||PALETTE[i%PALETTE.length];(info.tables||[]).forEach(t=>tgroup[t]=g);});
SCHEMA.forEach(t=>{if(!tgroup[t.table])tgroup[t.table]=FRAMEWORK.has(t.table)?"Framework":"Other";});
if(!gcolor["Framework"])gcolor["Framework"]="#5a6878"; if(!gcolor["Other"])gcolor["Other"]="#8b98a8";
const incoming={}; SCHEMA.forEach(t=>(t.fks||[]).forEach(f=>{(incoming[f.ref_table]=incoming[f.ref_table]||[]).push({from:t.table,...f});}));
const ODCOL={CASCADE:"#ff7b72","SET NULL":"#79c0ff","NO ACTION":"#5a6878"};
const state={audit:false,framework:false,cols:true,dim:true,focus:false,depth:1,groupsOff:new Set(),expanded:new Set(),hidden:new Set(),sel:null,edge:null,path:null,groupAreas:false,q:""};
let _focusSet=null;
let HOT={};  // {table: Set(columns participating in the highlighted relationships)}
const esc=s=>String(s==null?'':s).replace(/[&<>"]/g,m=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;'}[m]));

// undirected FK adjacency + flat edge list (for depth BFS, cardinality, hot-columns)
const adj={}, EDGES=[];
SCHEMA.forEach(t=>(t.fks||[]).forEach(f=>{ if(!byName[f.ref_table])return;
  (adj[t.table]=adj[t.table]||new Set()).add(f.ref_table);
  (adj[f.ref_table]=adj[f.ref_table]||new Set()).add(t.table);
  EDGES.push({src:t.table,tgt:f.ref_table,fkcol:f.column,refcol:f.ref_column,od:f.on_delete||'NO ACTION'});
}));
function relatedSet(name,depth){
  const set=new Set([name]); let frontier=[name],d=0;
  while(frontier.length && d<depth){ const nx=[];
    frontier.forEach(c=>(adj[c]||[]).forEach(n=>{ if(!set.has(n)){set.add(n);nx.push(n);} }));
    frontier=nx; d++; }
  return set;
}
function isUniqueFk(t,col){  // 1:1 when the FK column is unique on the child side, else 1:N
  if((t.pk||[]).length===1 && t.pk[0]===col) return true;
  return (t.indexes||[]).some(i=>/unique/i.test(i.def||'') && (i.def||'').replace(/\s/g,'').includes('('+col+')'));
}
function computeHot(set){
  const hot={};
  EDGES.forEach(e=>{ if(set.has(e.src)&&set.has(e.tgt)){
    (hot[e.src]=hot[e.src]||new Set()).add(e.fkcol); (hot[e.tgt]=hot[e.tgt]||new Set()).add(e.refcol); } });
  return hot;
}
function shortType(c){
  const u=c.udt||c.type||'';
  const m={int4:'int',int8:'bigint',int2:'smallint',bool:'bool',varchar:'varchar',text:'text',float8:'float',
    numeric:'numeric',jsonb:'jsonb',json:'json',uuid:'uuid',vector:'vector',bytea:'bytea',timestamp:'ts',timestamptz:'tstz',date:'date'};
  return m[u]||u||'';
}
function cardCols(t){
  const pk=new Set(t.pk||[]), fkc=new Set((t.fks||[]).map(f=>f.column));
  const exp=state.expanded.has(t.table), hot=HOT[t.table];
  let list=t.columns.slice();
  if(!exp && !state.audit) list=list.filter(c=>!AUDIT.has(c.column)||pk.has(c.column)||fkc.has(c.column));
  if(exp) list.sort((a,b)=>a.ord-b.ord);
  else{ const rank=c=>pk.has(c.column)?0:(fkc.has(c.column)?1:2); list.sort((a,b)=>rank(a)-rank(b)||a.ord-b.ord); }
  const max= exp? 999 : 11, shown=list.slice(0,max);
  let html=shown.map(c=>{
    const k=pk.has(c.column)?'pk':(fkc.has(c.column)?'fk':(AUDIT.has(c.column)?'au':'x'));
    const g=k==='pk'?'◆':(k==='fk'?'→':'·');
    const ht=hot&&hot.has(c.column)?' hot':'';
    return `<div class="erd-col${ht}" title="${esc(c.column)}: ${esc(c.udt||c.type||'')}"><span class="g ${k}">${g}</span><span class="cn">${esc(c.column)}</span><span class="ct">${esc(shortType(c))}</span></div>`;
  }).join('');
  let n=shown.length;
  if(list.length>max){ html+=`<div class="erd-col more erd-exp" data-tbl="${t.table}">+${list.length-max} more - show all</div>`; n++; }
  else if(exp && t.columns.length>6){ html+=`<div class="erd-col more erd-exp" data-tbl="${t.table}">collapse</div>`; n++; }
  return {html,n};
}
function shortNum(n){ n=+n||0; const a=Math.abs(n);
  if(a>=1e9) return (n/1e9).toFixed(a>=1e10?0:1).replace(/\.0$/,'')+'B';
  if(a>=1e6) return (n/1e6).toFixed(a>=1e7?0:1).replace(/\.0$/,'')+'M';
  if(a>=1e3) return (n/1e3).toFixed(a>=1e4?0:1).replace(/\.0$/,'')+'K';
  return ''+n; }
function nodeData(t){
  const cc=state.cols?cardCols(t):{html:'',n:0};
  const w=230, h=30 + (state.cols && cc.n? (cc.n*17+8):0) + 2;
  return {id:t.table, name:t.table, color:gcolor[tgroup[t.table]], group:tgroup[t.table],
    fw:FRAMEWORK.has(t.table)?1:0, expanded:state.expanded.has(t.table),
    meta:`${t.columns.length}c·${shortNum(t.rows||0)}r`, metaTitle:`${t.columns.length} columns · ${(t.rows||0).toLocaleString()} rows`, cols:cc.html, w, h};
}

let cy=null;
function buildElements(){
  const els=SCHEMA.map(t=>({data:nodeData(t)}));
  const seen=new Set();
  SCHEMA.forEach(t=>(t.fks||[]).forEach(f=>{
    if(!byName[f.ref_table]) return;
    const id='e__'+(f.constraint||(t.table+'.'+f.column+'.'+f.ref_table)); if(seen.has(id))return; seen.add(id);  // one edge per FK constraint (composite = 1 edge)
    els.push({data:{id, source:t.table, target:f.ref_table, src:t.table, tgt:f.ref_table,
      fkcol:f.column, refcol:f.ref_column, od:f.on_delete||'NO ACTION',
      scard:isUniqueFk(t,f.column)?'1':'N', odcolor:ODCOL[f.on_delete||'NO ACTION']||'#5a6878'}});
  }));
  return els;
}
function renderCards(){ cy.batch(()=>cy.nodes().forEach(n=>{const d=nodeData(byName[n.id()]);
  n.data('cols',d.cols); n.data('meta',d.meta); n.data('w',d.w); n.data('h',d.h); n.data('expanded',d.expanded);})); requestAnimationFrame(refreshClasses); }

function refreshClasses(){
  if(!cy) return;
  const q=state.q.toLowerCase();
  const set= state.path? new Set(state.path)
           : state.edge? new Set([state.edge.src,state.edge.tgt])
           : (state.sel&&state.dim)? relatedSet(state.sel,state.depth) : null;
  // focus mode: when something is selected, HIDE everything except it + its related set
  _focusSet = state.focus ? (state.path? new Set(state.path)
           : state.edge? new Set([state.edge.src,state.edge.tgt])
           : state.sel? relatedSet(state.sel,state.depth) : null) : null;
  cy.batch(()=>{
    cy.nodes().forEach(n=>{
      const t=n.id();
      const gone=(!state.framework&&n.data('fw'))||state.groupsOff.has(tgroup[t])||state.hidden.has(t)||(_focusSet&&!_focusSet.has(t));
      n.toggleClass('gone',gone);  // canvas display:none → hides node + its edges
      const mq=!q||t.toLowerCase().includes(q)||byName[t].columns.some(c=>c.column.toLowerCase().includes(q));
      // drive card classes via node data so the html-label extension re-renders cards WITH them
      n.data('cls',((gone?'gone ':'')+(!mq?'fade ':'')+(set?(set.has(t)?'hi ':'dim '):'')+(t===state.sel?'sel':'')).trim());
    });
    cy.edges().forEach(e=>{ e.removeClass('dim hi');
      if(set) (set.has(e.data('src'))&&set.has(e.data('tgt')))?e.addClass('hi'):e.addClass('dim'); });
  });
  updateStats(); writeHash(); drawHulls();
}
function select(name,opendocs){ state.sel=name; state.edge=null; state.path=null; HOT=computeHot(relatedSet(name,state.depth)); renderCards(); markList(); if(opendocs)openDocs(name); }
function clearSel(){ state.sel=null; state.edge=null; state.path=null; HOT={}; $('pathMsg')&&($('pathMsg').textContent=''); renderCards(); markList(); }
function selectEdge(d){
  state.edge={id:d.id,src:d.src,tgt:d.tgt,fkcol:d.fkcol,refcol:d.refcol,od:d.od||'NO ACTION'};
  state.sel=null; state.path=null; HOT={};
  if(d.fkcol) HOT[d.src]=new Set([d.fkcol]);
  if(d.refcol) HOT[d.tgt]=new Set([d.refcol]);
  renderCards(); markList(); openRelDocs(state.edge);
}
function openRelDocs(e){
  const card=isUniqueFk(byName[e.src],e.fkcol)?'1:1':'1:N';
  const verb=e.od==='CASCADE'?'also deletes':(e.od==='SET NULL'?'nulls the FK on':'is blocked while there are');
  document.getElementById('dTitle').textContent='Relationship';
  document.getElementById('dCls').textContent=`${tgroup[e.src]} → ${tgroup[e.tgt]}`;
  let h=`<div class="badges"><span class="badge">${card}</span><span class="badge">FK</span><span class="${odClass(e.od)}" style="padding:2px 8px;border-radius:20px">${esc(e.od)}</span></div>`;
  h+=`<table class="reltbl"><tr><td class="cn">${esc(e.src)}.${esc(e.fkcol)}</td><td>child · many (FK)</td></tr>
      <tr><td class="cn">${esc(e.tgt)}.${esc(e.refcol)}</td><td>parent · one (PK/UK)</td></tr></table>`;
  h+=`<h4>On delete</h4><div class="desc">Deleting a <b>${esc(e.tgt)}</b> ${verb} the referencing <b>${esc(e.src)}</b> row(s).</div>`;
  h+=`<h4>Open table</h4><div class="badges"><span class="badge" style="cursor:pointer" onclick="window.__openDocs('${esc(e.src)}')">${esc(e.src)}</span><span class="badge" style="cursor:pointer" onclick="window.__openDocs('${esc(e.tgt)}')">${esc(e.tgt)}</span></div>`;
  document.getElementById('dBody').innerHTML=h;
  document.getElementById('docs').classList.add('open');
}
function markList(){ document.querySelectorAll('.titem').forEach(e=>e.classList.toggle('sel',e.dataset.t===state.sel)); }

/* ---- docs drawer ---- */
const odClass=r=>'od '+((r||'NO ACTION').replace(/\s+/g,''));
function mmType(c){let t=c.type||c.udt||''; if(c.udt==='vector')t='vector'; if(t==='character varying')t='varchar'; if(t==='timestamp without time zone')t='timestamp'; return t;}
function openDocs(name){
  const t=byName[name]; if(!t) return;
  document.getElementById('dTitle').textContent=name;
  const cls=(META.classifications||{})[name];
  document.getElementById('dCls').textContent=[tgroup[name],cls].filter(Boolean).join(' · ');
  const desc=(META.descriptions||{})[name]||'';
  const pk=new Set(t.pk||[]), fkByCol={}; (t.fks||[]).forEach(f=>fkByCol[f.column]=f);
  let h=desc?`<p class="desc">${esc(desc)}</p>`:'';
  h+=`<div class="badges"><span class="badge">${t.columns.length} cols</span><span class="badge">${(t.rows||0).toLocaleString()} rows</span><span class="badge">${(t.fks||[]).length} FK out</span><span class="badge">${(incoming[name]||[]).length} FK in</span></div>`;
  h+=`<table class="cols"><thead><tr><th>Column</th><th>Type</th><th>Null</th><th>Keys</th></tr></thead><tbody>`;
  t.columns.forEach(c=>{
    const fk=fkByCol[c.column]; let keys='';
    if(pk.has(c.column))keys+='<span class="k pk">PK</span>';
    if(fk)keys+='<span class="k fk">FK</span>';
    if(AUDIT.has(c.column))keys+='<span class="k au">audit</span>';
    h+=`<tr><td class="cn">${esc(c.column)}</td><td class="ty">${esc(mmType(c))}</td><td>${c.nullable==='NO'?'<span class="k nn">NOT NULL</span>':''}</td><td>${keys}</td></tr>`;
    if(fk)h+=`<tr><td></td><td colspan="3" class="ty">→ ${esc(fk.ref_table)}.${esc(fk.ref_column)} <span class="${odClass(fk.on_delete)}">ON DELETE ${esc(fk.on_delete||'NO ACTION')}</span></td></tr>`;
  });
  h+=`</tbody></table>`;
  const inc=incoming[name]||[];
  h+=`<h4>Referenced by (${inc.length})</h4>`;
  h+= inc.length? '<table class="reltbl">'+inc.map(f=>`<tr><td class="cn">${esc(f.from)}.${esc(f.column)}</td><td><span class="${odClass(f.on_delete)}">${esc(f.on_delete||'NO ACTION')}</span></td></tr>`).join('')+'</table>' : '<div class="empty">No incoming references.</div>';
  const idx=(t.indexes||[]).filter(i=>!/_pkey$/.test(i.name));
  h+=`<h4>Indexes (${idx.length})</h4>`;
  h+= idx.length? idx.map(i=>`<div style="margin:4px 0"><code class="mono">${esc(i.def||i.name)}</code></div>`).join('') : '<div class="empty">No secondary indexes.</div>';
  document.getElementById('dBody').innerHTML=h;
  document.getElementById('docs').classList.add('open');
}
const closeDocs=()=>document.getElementById('docs').classList.remove('open');

/* ---- sidebar ---- */
function buildSidebar(){
  const gc=document.getElementById('groups'); gc.innerHTML='';
  const counts={}; SCHEMA.forEach(t=>counts[tgroup[t.table]]=(counts[tgroup[t.table]]||0)+1);
  const order=[...Object.keys(GROUPS),"Framework","Other"].filter((v,i,a)=>a.indexOf(v)===i&&counts[v]);
  order.forEach(g=>{
    const row=document.createElement('label'); row.className='grp';
    row.innerHTML=`<input type="checkbox" ${state.groupsOff.has(g)?'':'checked'} style="accent-color:${gcolor[g]}"/><span class="dot" style="background:${gcolor[g]}"></span><span class="gname">${esc(g)}</span><span class="gn">${counts[g]}</span>`;
    row.querySelector('input').addEventListener('change',e=>{e.target.checked?state.groupsOff.delete(g):state.groupsOff.add(g); refreshClasses(); buildTableList();});
    gc.appendChild(row);
  });
  buildTableList();
  const lg=document.getElementById('legend'); let lh='<b>Domain groups</b>';
  order.forEach(g=>lh+=`<div class="row"><span class="bx" style="background:${gcolor[g]}"></span>${esc(g)}</div>`);
  lh+='<b>Edge colour = ON DELETE</b>'+`<div class="row"><span class="sw" style="border-color:${ODCOL.CASCADE}"></span>CASCADE</div><div class="row"><span class="sw" style="border-color:${ODCOL['SET NULL']}"></span>SET NULL</div><div class="row"><span class="sw" style="border-color:${ODCOL['NO ACTION']}"></span>NO ACTION</div>`;
  lh+='<div class="row" style="margin-top:6px">ends: <b style="display:inline;margin:0 4px">1</b>=one · <b style="display:inline;margin:0 4px">N</b>=many (→ points to PK)</div>';
  lg.innerHTML=lh;
}
function listVisible(){ return SCHEMA.filter(t=>!((!state.framework&&FRAMEWORK.has(t.table))||state.groupsOff.has(tgroup[t.table]))).map(t=>t.table); }
function buildTableList(){
  const tl=document.getElementById('tlist'); tl.innerHTML='';
  const vis=new Set(listVisible());
  SCHEMA.slice().sort((a,b)=>a.table.localeCompare(b.table)).forEach(t=>{
    if(!vis.has(t.table))return;
    const off=state.hidden.has(t.table);
    const d=document.createElement('div'); d.className='titem'+(off?' off':''); d.dataset.t=t.table;
    d.innerHTML=`<span class="dot" style="background:${gcolor[tgroup[t.table]]}"></span><span class="tn">${esc(t.table)}</span><span class="rc">${(t.rows||0).toLocaleString()}</span><span class="eye" title="${off?'show':'hide'} entity">${off?'◯':'◉'}</span>`;
    d.querySelector('.eye').addEventListener('click',ev=>{ ev.stopPropagation(); off?state.hidden.delete(t.table):state.hidden.add(t.table); refreshClasses(); buildTableList(); });
    d.addEventListener('click',()=>{ select(t.table,true); focusNode(t.table); });
    tl.appendChild(d);
  });
  // appended last so toggling a node never shifts the rows above it (avoids mis-clicks)
  if(state.hidden.size){ const sh=document.createElement('div'); sh.className='showhidden';
    sh.textContent='⟲ show '+state.hidden.size+' hidden'; sh.addEventListener('click',()=>{state.hidden.clear();refreshClasses();buildTableList();}); tl.appendChild(sh); }
  applySearch(); markList();
}
function applySearch(){
  const q=state.q.toLowerCase();
  document.querySelectorAll('.titem').forEach(e=>{
    const t=byName[e.dataset.t];
    const hit=!q||e.dataset.t.toLowerCase().includes(q)||t.columns.some(c=>c.column.toLowerCase().includes(q));
    e.classList.toggle('hide',!hit);
  });
}
function updateStats(){
  const cols=SCHEMA.reduce((n,t)=>n+t.columns.length,0);
  const cons=new Set(); SCHEMA.forEach(t=>(t.fks||[]).forEach(f=>cons.add(f.constraint||t.table+'.'+f.column)));
  const vis=SCHEMA.filter(t=>!((!state.framework&&FRAMEWORK.has(t.table))||state.groupsOff.has(tgroup[t.table])||state.hidden.has(t.table)||(_focusSet&&!_focusSet.has(t.table)))).length;
  const tl=vis===SCHEMA.length?`<b>${SCHEMA.length}</b> tables`:`<b>${vis}</b>/${SCHEMA.length} tables`;
  document.getElementById('stats').innerHTML=`<span>${tl}</span><span><b>${cols}</b> columns</span><span><b>${cons.size}</b> relationships</span>`;
}
function focusNode(name){ if(!cy)return; const n=cy.$('#'+CSS.escape(name)); if(n.nonempty()) cy.animate({center:{eles:n},zoom:Math.max(cy.zoom(),0.85)},{duration:250}); }

/* ---- cytoscape ---- */
// fit, but keep the initial zoom legible - fit-to-all on a spread layout can zoom so far out that card columns become unreadable
function fitView(){ cy.fit(undefined,45); const z=cy.zoom(), c=Math.max(0.55,Math.min(1.1,z)); if(c!==z) cy.zoom({level:c,renderedPosition:{x:cy.width()/2,y:cy.height()/2}}); }
function runLayout(){ cy.layout({name:'cose',animate:false,padding:50,nodeRepulsion:14000,idealEdgeLength:190,
  nodeDimensionsIncludeLabels:true,randomize:true,componentSpacing:140,gravity:0.25}).run(); fitView(); }
function boot(){
  updateStats();
  applyState(readHash());
  cy=cytoscape({container:document.getElementById('cy'), elements:buildElements(), wheelSensitivity:0.3, minZoom:0.12, maxZoom:4,
    style:[
      {selector:'node',style:{'shape':'round-rectangle','background-opacity':0,'border-width':0,'width':'data(w)','height':'data(h)'}},
      {selector:'node.gone',style:{'display':'none'}},
      {selector:'edge',style:{'curve-style':'unbundled-bezier','control-point-distances':'55','control-point-weights':'0.5',
        'width':1.6,'line-color':'data(odcolor)','target-arrow-shape':'triangle','target-arrow-color':'data(odcolor)','arrow-scale':1,
        'source-label':'data(scard)','target-label':'1','font-size':11,'font-weight':700,'color':'#aeb9c7',
        'source-text-offset':22,'target-text-offset':22,'text-background-color':'#0f1419','text-background-opacity':0.9,
        'text-background-padding':2,'text-background-shape':'round-rectangle','opacity':0.6}},
      {selector:'edge.dim',style:{'opacity':0.04,'source-label':'','target-label':''}},
      {selector:'edge.hi',style:{'opacity':1,'width':3,'line-color':'#4ea1ff','target-arrow-color':'#4ea1ff','color':'#e6edf3','z-index':20}}
    ]});
  cy.nodeHtmlLabel([{query:'node', halign:'center', valign:'center', halignBox:'center', valignBox:'center',
    tpl:d=>`<div class="erd-card ${d.cls||''}" data-tbl="${d.name}" style="--c:${d.color}"><div class="erd-h"><span class="erd-dot"></span><span class="erd-name" title="${esc(d.name)}">${esc(d.name)}</span><span class="erd-meta" title="${esc(d.metaTitle||'')}">${d.meta}</span><span class="erd-ex erd-exp" data-tbl="${d.name}" title="show all columns">${d.expanded?'⊖':'⊕'}</span><span class="erd-ex erd-hide" data-tbl="${d.name}" title="hide entity">×</span></div>${d.cols?`<div class="erd-cols">${d.cols}</div>`:''}</div>`}]);
  const saved=loadPositions();
  if(saved){ cy.batch(()=>cy.nodes().forEach(n=>{const p=saved[n.id()]; if(p)n.position({x:p[0],y:p[1]});})); fitView(); }
  else runLayout();
  let tapT=null,lastId=null;
  cy.on('tap','node',e=>{ const id=e.target.id();
    if(tapT&&lastId===id){ clearTimeout(tapT); tapT=null; lastId=null; openDocs(id); select(id,false); return; }
    lastId=id; tapT=setTimeout(()=>{ tapT=null; lastId=null; select(id,false); },240); });
  cy.on('tap','edge',e=>selectEdge(e.target.data()));  // click a line → spotlight its two tables + join columns
  cy.on('tap',e=>{ if(e.target===cy) clearSel(); });
  cy.on('dragfree','node',savePositions);
  cy.on('render',()=>{drawHulls();drawMinimap();});
  document.getElementById('minimap').classList.add('on');
  fillPathSelects();
  buildSidebar();
  requestAnimationFrame(()=>{requestAnimationFrame(()=>{ refreshClasses(); if(state.sel) select(state.sel,false); })});
  document.getElementById('hint').style.display='block';
}
function fillPathSelects(){
  const opts='<option value=""> -  table  - </option>'+SCHEMA.map(t=>t.table).sort().map(t=>`<option value="${t}">${t}</option>`).join('');
  document.getElementById('pathFrom').innerHTML=opts; document.getElementById('pathTo').innerHTML=opts;
}

/* ---- find path (shortest FK chain between two tables) ---- */
function bfsPath(a,b){
  if(a===b)return[a];
  const prev={}; prev[a]=null; const q=[a];
  while(q.length){ const c=q.shift();
    for(const n of (adj[c]||[])){ if(!(n in prev)){ prev[n]=c;
      if(n===b){ const p=[b]; let x=b; while(prev[x]!=null){x=prev[x];p.unshift(x);} return p; } q.push(n); } } }
  return null;
}
function runFindPath(){
  const a=$('pathFrom').value,b=$('pathTo').value; if(!a||!b)return;
  state.sel=null;state.edge=null;
  const path=bfsPath(a,b);
  if(!path){ state.path=null;HOT={};$('pathMsg').textContent='⚠ no path between '+a+' and '+b; renderCards(); markList(); return; }
  state.path=path; $('pathMsg').textContent=path.join('  →  ');
  HOT={};
  for(let i=0;i<path.length-1;i++){ const x=path[i],y=path[i+1];
    EDGES.filter(e=>(e.src===x&&e.tgt===y)||(e.src===y&&e.tgt===x)).forEach(e=>{
      (HOT[e.src]=HOT[e.src]||new Set()).add(e.fkcol); (HOT[e.tgt]=HOT[e.tgt]||new Set()).add(e.refcol); }); }
  renderCards(); markList();
  const sel=cy.collection(); path.forEach(t=>{const n=cy.$('#'+CSS.escape(t)); if(n&&n.nonempty())sel.merge(n);});
  if(sel.nonempty()) cy.animate({fit:{eles:sel,padding:90}},{duration:300});
}

/* ---- schema insights (lint) ---- */
function computeInsights(){
  const out=[];
  SCHEMA.forEach(t=>{
    if(!(t.pk&&t.pk.length)) out.push({sev:'warn',table:t.table,msg:'no primary key',grp:'Missing primary key'});
    const lead=new Set(t.pk||[]);
    (t.indexes||[]).forEach(i=>{ const m=(i.def||'').match(/\(([^)]+)\)/); if(m) lead.add(m[1].split(',')[0].trim().replace(/["\s]/g,'')); });
    (t.fks||[]).forEach(f=>{
      if(!lead.has(f.column)) out.push({sev:'info',table:t.table,msg:'FK '+f.column+' has no supporting index',grp:'Unindexed FK'});
      const pt=byName[f.ref_table];
      if(pt){ const cc=t.columns.find(c=>c.column===f.column), pc=pt.columns.find(c=>c.column===f.ref_column);
        if(cc&&pc&&cc.udt!==pc.udt) out.push({sev:'warn',table:t.table,msg:'FK '+f.column+' ('+cc.udt+') ≠ '+f.ref_table+'.'+f.ref_column+' ('+pc.udt+')',grp:'FK type mismatch'}); }
    });
    if(!(t.fks||[]).length && !(incoming[t.table]||[]).length && !FRAMEWORK.has(t.table))
      out.push({sev:'info',table:t.table,msg:'orphan table (no relationships)',grp:'Orphan table'});
  });
  return out;
}
function openInsights(){
  const issues=computeInsights(), order=['Missing primary key','FK type mismatch','Unindexed FK','Orphan table'], byg={};
  issues.forEach(i=>(byg[i.grp]=byg[i.grp]||[]).push(i));
  let h= issues.length? '' : '<div class="ins-ok">✓ No issues - every table has a PK, FK types match parents, and FKs are indexed.</div>';
  order.forEach(g=>{ const arr=byg[g]; if(!arr||!arr.length)return;
    h+=`<div class="ins-grp">${g} (${arr.length})</div>`;
    arr.forEach(i=>{ h+=`<div class="ins-row" data-t="${esc(i.table)}"><span class="ins-sev ${i.sev}"></span><span class="tb">${esc(i.table)}</span><span class="ms">${esc(i.msg)}</span></div>`; }); });
  $('insBody').innerHTML=h;
  $('insBody').querySelectorAll('.ins-row').forEach(r=>r.addEventListener('click',()=>{ $('insights').classList.remove('open'); select(r.dataset.t,true); focusNode(r.dataset.t); }));
  $('insights').classList.add('open');
}

/* ---- shareable URL state ---- */
function serialize(){ return {a:+state.audit,f:+state.framework,c:+state.cols,dm:+state.dim,fo:+state.focus,dp:state.depth,ga:+state.groupAreas,go:[...state.groupsOff],hd:[...state.hidden],ex:[...state.expanded],sel:state.sel}; }
let _hashT=null;
function writeHash(){ clearTimeout(_hashT); _hashT=setTimeout(()=>{ try{ history.replaceState(null,'','#s='+encodeURIComponent(JSON.stringify(serialize()))); }catch(e){} },250); }
function readHash(){ try{ const m=(location.hash||'').match(/s=([^&]+)/); return m?JSON.parse(decodeURIComponent(m[1])):null; }catch(e){ return null; } }
function applyState(s){ if(!s)return;
  state.audit=!!s.a;state.framework=!!s.f;state.cols=s.c!==0;state.dim=s.dm!==0;state.focus=!!s.fo;state.depth=s.dp||1;state.groupAreas=!!s.ga;
  state.groupsOff=new Set(s.go||[]);state.hidden=new Set(s.hd||[]);state.expanded=new Set(s.ex||[]);state.sel=s.sel||null;
  $('optAudit').checked=state.audit;$('optFramework').checked=state.framework;$('optCols').checked=state.cols;
  $('optDim').checked=state.dim;$('optFocus')&&($('optFocus').checked=state.focus);$('optDepth').value=String(state.depth);$('optGroupAreas').checked=state.groupAreas; }

/* ---- saved layout (localStorage, per schema) ---- */
const LKEY='erd-pos:'+(META.title||'db');
function savePositions(){ try{ const m={}; cy.nodes().forEach(n=>{const p=n.position();m[n.id()]=[Math.round(p.x),Math.round(p.y)];}); localStorage.setItem(LKEY,JSON.stringify(m)); }catch(e){} }
function loadPositions(){ try{ return JSON.parse(localStorage.getItem(LKEY)||'null'); }catch(e){ return null; } }

/* ---- group hulls (canvas overlay behind the graph) ---- */
function hull(pts){ // convex hull, monotone chain
  pts=pts.slice().sort((a,b)=>a[0]-b[0]||a[1]-b[1]); if(pts.length<3)return pts;
  const cr=(o,a,b)=>(a[0]-o[0])*(b[1]-o[1])-(a[1]-o[1])*(b[0]-o[0]); const lo=[],up=[];
  for(const p of pts){ while(lo.length>=2&&cr(lo[lo.length-2],lo[lo.length-1],p)<=0)lo.pop(); lo.push(p); }
  for(let i=pts.length-1;i>=0;i--){ const p=pts[i]; while(up.length>=2&&cr(up[up.length-2],up[up.length-1],p)<=0)up.pop(); up.push(p); }
  lo.pop();up.pop(); return lo.concat(up);
}
function drawHulls(){
  const cv=$('hull'); if(!cv||!cy)return; const ctx=cv.getContext('2d');
  const dpr=window.devicePixelRatio||1, w=cv.clientWidth, h=cv.clientHeight;
  if(cv.width!==w*dpr||cv.height!==h*dpr){cv.width=w*dpr;cv.height=h*dpr;}
  ctx.setTransform(dpr,0,0,dpr,0,0); ctx.clearRect(0,0,w,h);
  if(!state.groupAreas)return;
  const groups={};
  cy.nodes().forEach(n=>{ if(n.hasClass('gone'))return; const g=tgroup[n.id()], bb=n.renderedBoundingBox();
    (groups[g]=groups[g]||[]).push([bb.x1,bb.y1],[bb.x2,bb.y1],[bb.x2,bb.y2],[bb.x1,bb.y2]); });
  Object.entries(groups).forEach(([g,pts])=>{ if(pts.length<2)return; const col=gcolor[g]||'#8b98a8';
    let poly=hull(pts);
    if(poly.length<3){ const xs=pts.map(p=>p[0]),ys=pts.map(p=>p[1]); poly=[[Math.min(...xs),Math.min(...ys)],[Math.max(...xs),Math.min(...ys)],[Math.max(...xs),Math.max(...ys)],[Math.min(...xs),Math.max(...ys)]]; }
    const cx=poly.reduce((s,p)=>s+p[0],0)/poly.length, cyc=poly.reduce((s,p)=>s+p[1],0)/poly.length, pad=24;
    poly=poly.map(p=>{const dx=p[0]-cx,dy=p[1]-cyc,d=Math.hypot(dx,dy)||1;return [p[0]+dx/d*pad,p[1]+dy/d*pad];});
    ctx.beginPath(); poly.forEach((p,i)=>i?ctx.lineTo(p[0],p[1]):ctx.moveTo(p[0],p[1])); ctx.closePath();
    ctx.fillStyle=col+'14'; ctx.fill(); ctx.lineWidth=1.5; ctx.strokeStyle=col+'55'; ctx.stroke();
    const ty=Math.min(...poly.map(p=>p[1])); ctx.fillStyle=col+'cc'; ctx.font='600 11px -apple-system,sans-serif';
    ctx.fillText(g, cx-ctx.measureText(g).width/2, ty-6);
  });
}

/* ---- minimap (custom, model-space → mini canvas + viewport rect) ---- */
let _mmBox=null;  // {x1,y1,w,h,scale} mapping model→mini, for click-to-pan
function drawMinimap(){
  const cv=$('mmcv'); if(!cv||!cy)return; const ctx=cv.getContext('2d');
  const dpr=window.devicePixelRatio||1, W=cv.clientWidth, H=cv.clientHeight;
  if(!W||!H)return;
  if(cv.width!==W*dpr||cv.height!==H*dpr){cv.width=W*dpr;cv.height=H*dpr;}
  ctx.setTransform(dpr,0,0,dpr,0,0); ctx.clearRect(0,0,W,H);
  const vis=cy.nodes().filter(n=>!n.hasClass('gone')); if(!vis.length)return;
  let x1=1e9,y1=1e9,x2=-1e9,y2=-1e9;
  vis.forEach(n=>{const b=n.boundingBox();x1=Math.min(x1,b.x1);y1=Math.min(y1,b.y1);x2=Math.max(x2,b.x2);y2=Math.max(y2,b.y2);});
  const pad=40; x1-=pad;y1-=pad;x2+=pad;y2+=pad;
  const sc=Math.min(W/(x2-x1),H/(y2-y1)); const ox=(W-(x2-x1)*sc)/2, oy=(H-(y2-y1)*sc)/2;
  const MX=mx=>(mx-x1)*sc+ox, MY=my=>(my-y1)*sc+oy;
  _mmBox={x1,y1,sc,ox,oy};
  cy.edges().filter(e=>!e.source().hasClass('gone')&&!e.target().hasClass('gone')).forEach(e=>{
    const s=e.source().position(),t=e.target().position(); ctx.strokeStyle='rgba(120,140,160,.35)';ctx.lineWidth=0.5;
    ctx.beginPath();ctx.moveTo(MX(s.x),MY(s.y));ctx.lineTo(MX(t.x),MY(t.y));ctx.stroke();});
  vis.forEach(n=>{const b=n.boundingBox();ctx.fillStyle=(gcolor[tgroup[n.id()]]||'#8b98a8')+'cc';
    ctx.fillRect(MX(b.x1),MY(b.y1),Math.max(2,(b.x2-b.x1)*sc),Math.max(2,(b.y2-b.y1)*sc));});
  // viewport rectangle (extent of the visible pane in model space)
  const ext=cy.extent(); ctx.strokeStyle='#4ea1ff';ctx.lineWidth=1.5;
  ctx.strokeRect(MX(ext.x1),MY(ext.y1),(ext.x2-ext.x1)*sc,(ext.y2-ext.y1)*sc);
}
function minimapPan(ev){
  if(!_mmBox||!cy)return; const cv=$('mmcv'); const r=cv.getBoundingClientRect();
  const mx=(ev.clientX-r.left-_mmBox.ox)/_mmBox.sc+_mmBox.x1, my=(ev.clientY-r.top-_mmBox.oy)/_mmBox.sc+_mmBox.y1;
  const z=cy.zoom(); cy.pan({x:cy.width()/2-mx*z, y:cy.height()/2-my*z});
}

/* ---- wire up ---- */
window.__openDocs=name=>{ select(name,true); focusNode(name); };
const $=id=>document.getElementById(id);
$('search').addEventListener('input',e=>{state.q=e.target.value;applySearch();refreshClasses();});
$('optCols').addEventListener('change',e=>{state.cols=e.target.checked;renderCards();});
$('optAudit').addEventListener('change',e=>{state.audit=e.target.checked;renderCards();});
$('optFramework').addEventListener('change',e=>{state.framework=e.target.checked;refreshClasses();buildSidebar();});
$('optDim').addEventListener('change',e=>{state.dim=e.target.checked;refreshClasses();});
$('optFocus').addEventListener('change',e=>{state.focus=e.target.checked;refreshClasses();});
$('optDepth').addEventListener('change',e=>{state.depth=+e.target.value; if(state.sel)select(state.sel,false);});
$('optGroupAreas').addEventListener('change',e=>{state.groupAreas=e.target.checked; drawHulls(); writeHash();});
$('grpAll')&&$('grpAll').addEventListener('click',()=>{state.groupsOff.clear();refreshClasses();buildSidebar();});
$('grpNone')&&$('grpNone').addEventListener('click',()=>{[...new Set(SCHEMA.map(t=>tgroup[t.table]))].forEach(g=>state.groupsOff.add(g));refreshClasses();buildSidebar();});
$('btnPath').addEventListener('click',runFindPath);
$('btnPathClear').addEventListener('click',()=>{state.path=null;$('pathMsg').textContent='';$('pathFrom').value='';$('pathTo').value='';clearSel();});
$('btnInsights').addEventListener('click',openInsights);
$('insClose').addEventListener('click',()=>$('insights').classList.remove('open'));
$('insights').addEventListener('click',e=>{if(e.target===$('insights'))$('insights').classList.remove('open');});
const DBML_TYPE={int4:"int",int8:"bigint",int2:"smallint",bool:"boolean",varchar:"varchar",text:"text",float8:"float",float4:"float",numeric:"numeric",jsonb:"jsonb",json:"json",uuid:"uuid",bytea:"bytea",timestamp:"timestamp",timestamptz:"timestamptz",date:"date",time:"time",vector:"vector",tsvector:"tsvector"};
const DBML_DEL={CASCADE:"cascade","SET NULL":"set null","SET DEFAULT":"set default",RESTRICT:"restrict"};
function emitDBML(){
  const out=[`Project "${META.title||'database'}" {\n  database_type: '${META.database_type||'PostgreSQL'}'\n}\n`];
  const tabs=[...SCHEMA].sort((a,b)=>a.table.localeCompare(b.table)), present=new Set(SCHEMA.map(t=>t.table));
  for(const t of tabs){ const pk=new Set(t.pk||[]); out.push(`Table ${t.table} {`);
    for(const c of t.columns){ let ty=DBML_TYPE[c.udt]; if(ty===undefined)ty=c.udt||c.type||"text";
      const a=[]; if(pk.has(c.column))a.push("pk"); else if(c.nullable==="NO")a.push("not null");
      out.push(`  ${c.column} ${ty}`+(a.length?` [${a.join(", ")}]`:"")); }
    out.push("}\n"); }
  for(const t of tabs){ const order=[],gr={};
    for(const f of t.fks||[]){ const k=f.constraint||f.column; if(!gr[k]){gr[k]={cols:[],rcols:[],ref:f.ref_table,od:f.on_delete,inf:f.inferred};order.push(k);} gr[k].cols.push(f.column); gr[k].rcols.push(f.ref_column); }
    for(const k of order){ const g=gr[k],s=[]; const d=DBML_DEL[(g.od||'').toUpperCase()]; if(d)s.push(`delete: ${d}`); if(g.inf)s.push("note: 'inferred'");
      const set=s.length?` [${s.join(", ")}]`:'';
      const lhs=g.cols.length>1?`${t.table}.(${g.cols.join(", ")})`:`${t.table}.${g.cols[0]}`;
      const rhs=g.cols.length>1?`${g.ref}.(${g.rcols.join(", ")})`:`${g.ref}.${g.rcols[0]}`;
      out.push(`Ref: ${lhs} > ${rhs}${set}`); } }
  for(const g of Object.keys(GROUPS).sort()){ const tbls=(GROUPS[g].tables||[]).filter(x=>present.has(x)); if(tbls.length) out.push(`\nTableGroup "${g}" {\n  ${tbls.join("\n  ")}\n}`); }
  return out.join("\n")+"\n";
}
$('btnDbml').addEventListener('click',()=>{ $('dbmlSrc').textContent=emitDBML(); $('dbml').classList.add('open'); });
$('dbmlClose').addEventListener('click',()=>$('dbml').classList.remove('open'));
$('dbml').addEventListener('click',e=>{ if(e.target===$('dbml'))$('dbml').classList.remove('open'); });
$('dbmlCopy').addEventListener('click',()=>{ const b=$('dbmlCopy'),o=b.textContent; if(navigator.clipboard)navigator.clipboard.writeText($('dbmlSrc').textContent); b.textContent='✓ copied'; setTimeout(()=>b.textContent=o,1200); });
$('btnShare').addEventListener('click',()=>{ writeHash(); const u=location.href;
  const done=()=>{const b=$('btnShare');const t=b.textContent;b.textContent='✓ copied';setTimeout(()=>b.textContent=t,1200);};
  (navigator.clipboard?navigator.clipboard.writeText(u).then(done,done):done()); });
let _mmDrag=false;
$('minimap').addEventListener('mousedown',e=>{_mmDrag=true;minimapPan(e);e.preventDefault();});
window.addEventListener('mousemove',e=>{if(_mmDrag)minimapPan(e);});
window.addEventListener('mouseup',()=>{_mmDrag=false;});
// expand/collapse all columns on a single entity (header ⊕ or the "+N more" row)
document.addEventListener('pointerdown',e=>{ const ex=e.target.closest('.erd-exp'); if(!ex)return;
  e.stopPropagation(); const t=ex.dataset.tbl; state.expanded.has(t)?state.expanded.delete(t):state.expanded.add(t); renderCards(); },true);
// hide a single entity (header ×) - restore via the sidebar eye or "show N hidden"
document.addEventListener('pointerdown',e=>{ const h=e.target.closest('.erd-hide'); if(!h)return;
  e.stopPropagation(); state.hidden.add(h.dataset.tbl); refreshClasses(); buildTableList(); },true);
$('dClose').addEventListener('click',closeDocs);
$('btnAll').addEventListener('click',()=>{clearSel();closeDocs();});
$('btnFit').addEventListener('click',()=>cy&&cy.fit(undefined,45));
$('btnLayout').addEventListener('click',()=>{ if(!cy)return; try{localStorage.removeItem(LKEY);}catch(e){} runLayout(); savePositions(); drawHulls(); });
$('zfit').addEventListener('click',()=>cy&&cy.fit(undefined,45));
$('zin').addEventListener('click',()=>cy&&cy.zoom({level:cy.zoom()*1.3,renderedPosition:{x:cy.width()/2,y:cy.height()/2}}));
$('zout').addEventListener('click',()=>cy&&cy.zoom({level:cy.zoom()/1.3,renderedPosition:{x:cy.width()/2,y:cy.height()/2}}));
$('btnLeft').addEventListener('click',()=>$('app').classList.toggle('lhide'));
const toggleHelp=()=>$('help').classList.toggle('open');
$('btnHelp').addEventListener('click',toggleHelp);
$('helpClose').addEventListener('click',()=>$('help').classList.remove('open'));
$('help').addEventListener('click',e=>{if(e.target===$('help'))$('help').classList.remove('open');});
$('btnReset').addEventListener('click',()=>{
  state.audit=false;state.framework=false;state.cols=true;state.dim=true;state.depth=1;state.groupAreas=false;
  state.groupsOff.clear();state.expanded.clear();state.hidden.clear();state.sel=null;state.edge=null;state.path=null;state.q='';HOT={};
  ['optAudit','optFramework','optGroupAreas'].forEach(i=>$(i).checked=false);['optCols','optDim'].forEach(i=>$(i).checked=true);
  $('search').value='';$('optDepth').value='1';$('pathMsg').textContent='';$('pathFrom').value='';$('pathTo').value='';
  try{localStorage.removeItem(LKEY);}catch(e){}
  renderCards();buildSidebar();refreshClasses();closeDocs();runLayout();savePositions();
});
document.addEventListener('keydown',e=>{
  const inInput=/^(INPUT|TEXTAREA)$/.test(document.activeElement.tagName);
  if(e.key==='Escape'){ if($('help').classList.contains('open'))$('help').classList.remove('open'); else if($('insights').classList.contains('open'))$('insights').classList.remove('open'); else if($('docs').classList.contains('open'))closeDocs(); else if(state.sel||state.edge||state.path)clearSel(); if(inInput)document.activeElement.blur(); return; }
  if(inInput) return;
  switch(e.key){
    case '/': e.preventDefault(); $('search').focus(); break;
    case '?': toggleHelp(); break;
    case 'f': case '0': cy&&cy.fit(undefined,45); break;
    case 'g': cy&&runLayout(); break;
    case '+': case '=': cy&&cy.zoom({level:cy.zoom()*1.3,renderedPosition:{x:cy.width()/2,y:cy.height()/2}}); break;
    case '-': cy&&cy.zoom({level:cy.zoom()/1.3,renderedPosition:{x:cy.width()/2,y:cy.height()/2}}); break;
    case 'a': $('optAudit').click(); break;
    case 't': $('optFramework').click(); break;
    case 'c': $('optCols').click(); break;
    case 'n': $('optDim').click(); break;
    case 's': clearSel(); closeDocs(); break;
    case 'r': $('btnReset').click(); break;
    case '[': $('btnLeft').click(); break;
    case ']': $('docs').classList.toggle('open'); break;
  }
});
if(window.cytoscape) boot(); else window.addEventListener('load',boot);
</script>
</body>
</html>
"""

if __name__ == "__main__":
    raise SystemExit(main())
