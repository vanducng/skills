# Install ego lite

Read this file only when ego lite isn't installed yet, or when the user asks to install ego lite. For day-to-day browser work, go back to `SKILL.md`.

The ego-browser skill depends on the ego lite browser: the `ego-browser` command is provided by the ego lite app. Once ego lite is installed and you've gone through onboarding once, the environment is ready and there are no further environment issues.

ego lite website: https://lite.ego.app/

## Install steps (macOS only)

The install script lives at `scripts/install.sh` in this skill and supports macOS only. It will:

- Download the ego lite installer (a DMG) for your CPU architecture (arm64 / x64).
- Install `ego lite.app` to `/Applications` (falling back to `~/Applications` when needed).
- Strip the quarantine attribute to keep Gatekeeper from blocking the first launch.
- After installing, launch the `ego lite` app.

Run the script (use the script's actual path under this skill's directory):

```bash
sh skills/ego-browser/scripts/install.sh
```

After installing, the script opens the ego lite app directly. If ego lite is already installed, the script skips the download and opens the app directly.

After the script opens the ego lite app, the user completes the first-run onboarding in the app:

- Choose to import data from Chrome or another browser as needed.
- Onboarding registers the `ego-browser` command on the PATH (usually under `~/.local/bin`).

Onboarding is a step the user completes in the GUI. After the script opens ego lite, wait for the user to confirm they've finished onboarding before continuing.

## After installing: confirm `ego-browser` is available

Once the user has finished onboarding, confirm the command is ready:

```bash
command -v ego-browser
```

If it reports that the command isn't found, `~/.local/bin` is most likely not on the current PATH. Fix it temporarily and retry:

```bash
export PATH="$HOME/.local/bin:$PATH"
command -v ego-browser
```

Once the command exists, verify the runtime with a minimal heredoc:

```bash
ego-browser nodejs <<'EOF'
const facadeReady =
  typeof taskSpaces === 'object' &&
  typeof page === 'object' &&
  typeof browser === 'object'
const legacyReady =
  typeof useOrCreateTaskSpace === 'function' &&
  typeof openOrReuseTab === 'function' &&
  typeof pageInfo === 'function'

if (!facadeReady && !legacyReady) {
  throw new Error('ego-browser helper runtime is outdated')
}
console.log(`ego-browser ready: ${facadeReady ? 'facade' : 'legacy'}`)
EOF
```

Printing `ego-browser ready: facade` or `ego-browser ready: legacy` means the environment is ready. Before writing browser code, read `$HOME/.local/share/ego/ego-skills/SKILL.md`; it ships with the active app and defines the matching helper names and signatures.

## After that, return to the original task

Once the environment is ready, return to the user's original task and follow the task-space API documented by the app-embedded skill, while preserving the lifecycle and confirmation policies in `SKILL.md`.

## Troubleshooting

- **Not macOS**: the script supports macOS only (`uname -s` is `Darwin`). On other platforms, have the user download and install from the ego lite website at https://lite.ego.app/.
- **Download failed**: the script retries 3 times automatically; if it still fails, it's usually a network issue - have the user check their network and retry.
- **Gatekeeper still blocks it**: the script already tries to strip quarantine; if the first launch is still blocked, have the user allow ego lite manually under System Settings → Privacy & Security.
- **Command still unavailable after onboarding**: confirm `~/.local/bin` is on the PATH (see above); or have the user reopen ego lite, finish onboarding, and retry.
- **Facade globals are missing**: if the legacy readiness check passes, the runtime is ready; follow `$HOME/.local/share/ego/ego-skills/SKILL.md` instead of treating the missing facade as an install failure. If neither surface exists, ask the user before running `ego-browser upgrade`. After the upgrade, re-read both skills because the app, CLI, installed skill, and runtime API may all have changed.
