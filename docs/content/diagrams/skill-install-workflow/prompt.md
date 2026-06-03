## Original
Skill catalog installation workflow for vanducng/skills. Start: user wants to install skills. Step 1 choose target runtime: Claude Code plugin marketplace, Claude Code dev symlinks, Codex user scope, or Codex repo scope. Step 2 install or verify vd CLI when using CLI-managed paths: brew install vanducng/tap/vd or go install github.com/vanducng/vd-cli/v2/cmd/vd@latest, then vd --version. Decision: Claude plugin mode? If yes run /plugin marketplace add vanducng/skills then /plugin install vd@vd-skills; update path runs /plugin marketplace update vd-skills then /plugin install vd@vd-skills. If Claude dev symlinks, run vd install claude --dev --dry-run then vd install claude --dev, linking skills to /Users/vanducng/.claude/skills. If Codex user scope, run vd install codex --dry-run then vd install codex, linking skills to /Users/vanducng/.agents/skills. If Codex repo scope, run vd install codex --scope repo --dry-run then vd install codex --scope repo, linking skills to repo .agents/skills. Common verification: vd list, vd doctor, bash scripts/validate.sh. End state: runtime discovers canonical skill IDs like vd:research and user invokes them with runtime prefix.

## Preset
mono

## Refined
<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 2520 720" width="100%" height="auto">
<style><![CDATA[
:root {
  --bg: #ffffff;
  --primary: #0a0a0a;
  --accent: #0a0a0a;
  --success: #0a0a0a;
  --error: #0a0a0a;
  --muted: #737373;
}
@media (prefers-color-scheme: dark) {
  :root {
    --bg: #0a0a0a;
    --primary: #fafafa;
    --accent: #fafafa;
    --success: #fafafa;
    --error: #fafafa;
    --muted: #a3a3a3;
  }
}
.canvas { fill: var(--bg); }
.boundary { fill: none; stroke: var(--muted); stroke-width: 1; }
.service { fill: var(--bg); stroke: var(--primary); stroke-width: 2; }
.process { fill: var(--bg); stroke: var(--primary); stroke-width: 2; }
.state { fill: var(--bg); stroke: var(--primary); stroke-width: 2; }
.decision { fill: var(--bg); stroke: var(--primary); stroke-width: 2; }
.accent-stroke { stroke: var(--accent); stroke-width: 3.5; }
.connection-sync { stroke: var(--primary); stroke-width: 2; fill: none; }
.connection-async { stroke: var(--primary); stroke-width: 2;
... (16306 chars total)

## Image model
(SVG-only run, no image-gen model)

## Image
v1.svg


## Iteration v2
**Feedback:** Simplify the workflow into fewer boxes and cleaner swimlanes. Avoid connector lines crossing through labels or shapes. Use short multiline labels: Start, Choose target host, Install vd CLI only for CLI-managed paths, Claude plugin marketplace, Claude dev symlinks, Codex user scope, Codex repo scope, Verify install, Ready to invoke. Put commands as secondary small code text inside each branch, not full long sentences. Use a light readable background, strong contrast, and leave generous whitespace between columns. The core workflow is: start -> choose target host -> one of four branches: Claude plugin mode runs plugin marketplace add/install/update; Claude dev symlinks runs vd install claude --dev dry-run then apply; Codex user scope runs vd install codex dry-run then apply; Codex repo scope runs vd install codex --scope repo dry-run then apply. All branches converge to verification: vd list, vd doctor, bash scripts/validate.sh -> runtime discovers canonical vd:* skills.

**Refined:**
<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 2520 500" width="100%" height="auto">
<style><![CDATA[
:root {
  --bg: #ffffff;
  --primary: #0a0a0a;
  --accent: #0a0a0a;
  --success: #0a0a0a;
  --error: #0a0a0a;
  --muted: #737373;
}
@media (prefers-color-scheme: dark) {
  :root {
    --bg: #0a0a0a;
    --primary: #fafafa;
    --accent: #fafafa;
    --success: #fafafa;
    --error: #fafafa;
    --muted: #a3a3a3;
  }
}
.canvas { fill: var(--bg); }
.boundary { fill: none; stroke: var(--muted); stroke-width: 1; }
.service { fill: var(--bg); stroke: var(--primary); stroke-width: 2; }
.process { fill: var(--bg); stroke: var(--primary); stroke-width: 2; }
.state { fill: var(--bg); stroke: var(--primary); stroke-width: 2; }
.accent-stroke { stroke: var(--primary); stroke-width: 3.5; }
.connection-sync { stroke: var(--primary); stroke-width: 2; fill: none; }
.connection-async { stroke: var(--primary); stroke-width: 2; fill: none; stroke-dasharray: 6 4; }
.connection-error { stroke: var(-
... (11749 chars total)

**File:** v2.svg


## Manual finish v3
The generated v1/v2 variants preserved the install workflow but had connector
overlaps and cramped labels. v3 keeps the same versioned diagram intent and
hand-finishes the SVG into a simpler branch-and-converge layout.

**File:** v3.svg
