#!/usr/bin/env bash
# Export one sheet tab to a one-page, gridline-free PDF (gog sheets export has no gid option).
# usage: export-tab-pdf.sh <gog-client> <email> <client-json> <spreadsheet-id> <gid> <out.pdf>
set -euo pipefail
export GOG_HOME="${GOG_HOME:-$HOME/.config/vd/gog}"
CLIENT=$1 EMAIL=$2 CJ=$3 SID=$4 GID=$5 OUT=$6
umask 077
T=$(mktemp)
trap 'rm -f "$T"' EXIT
gog --client "$CLIENT" auth tokens export "$EMAIL" --out "$T" --overwrite >/dev/null 2>&1
ACC=$(python3 - "$T" "$CJ" <<'EOF'
import json, sys, urllib.parse, urllib.request
t = json.load(open(sys.argv[1]))
c = json.load(open(sys.argv[2]))
c = c.get("installed") or c.get("web") or c
d = urllib.parse.urlencode({"client_id": c["client_id"], "client_secret": c["client_secret"],
                            "refresh_token": t["refresh_token"], "grant_type": "refresh_token"}).encode()
print(json.load(urllib.request.urlopen("https://oauth2.googleapis.com/token", d))["access_token"])
EOF
)
# scale=4 = fit to page; drop it to get fit-to-width across pages
curl -sS -fL -H "Authorization: Bearer $ACC" -o "$OUT" \
  "https://docs.google.com/spreadsheets/d/$SID/export?format=pdf&gid=$GID&size=letter&portrait=true&scale=4&gridlines=false&printtitle=false&sheetnames=false&pagenum=UNDEFINED&fzr=false&top_margin=0.5&bottom_margin=0.5&left_margin=0.5&right_margin=0.5"
pdfinfo "$OUT" | grep Pages
