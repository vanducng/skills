#!/usr/bin/env bash
# Export profile cookies + localStorage as Playwright-compatible storageState JSON.
# Profile must be currently open. Requires Node 18+ and npx (auto-installs @playwright/test).
# Usage: profile-export.sh <name> [out.json]

set -euo pipefail
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# shellcheck source=_lib.sh
source "$SCRIPT_DIR/_lib.sh"

NAME="$(require_name "${1:-}")"
OUT="${2:-storageState-$NAME.json}"
PORT="$(port_for "$NAME")"

cdp_alive "$PORT" || die "profile '$NAME' not running on :$PORT — open it first"
command -v npx >/dev/null 2>&1 || die "npx not found (install Node 18+)"

# Inline Node: connect over CDP (does NOT kill the underlying Chrome), dump storageState, disconnect.
NODE_SCRIPT=$(cat <<'EOF'
const { chromium } = require('@playwright/test');
const fs = require('fs');
const port = process.env.BP_PORT;
const out  = process.env.BP_OUT;
(async () => {
  const browser = await chromium.connectOverCDP(`http://localhost:${port}`);
  const ctx = browser.contexts()[0];
  if (!ctx) { console.error('no context found on target'); process.exit(2); }
  const state = await ctx.storageState();
  fs.writeFileSync(out, JSON.stringify(state, null, 2));
  await browser.close();           // disconnects client only, leaves Chrome running
  console.error(`exported -> ${out} (${state.cookies.length} cookies · ${state.origins.length} origins)`);
})().catch(e => { console.error(e.message); process.exit(1); });
EOF
)

BP_PORT="$PORT" BP_OUT="$OUT" npx -y -p '@playwright/test' node -e "$NODE_SCRIPT"
chmod 600 "$OUT"
