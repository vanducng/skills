# zsh startup: diagnose and fix

## Measure

- `python3 scripts/zsh-startup-profile.py --env clean` shows what a fresh terminal pays; `--env inherited` shows agent and nested shells, which inherit an exported `FPATH`.
- Read three things: `compinit calls` (should be 1), `compdump calls` (0 on a warm start; any other value means a full completion rebuild), and the top startup-file lines.
- Under heavy load every fork is slow. Re-measure when the load drops, or run the same config on an idle host.

## Root causes, by impact

| Symptom in the profile | Cause | Fix |
|---|---|---|
| `compinit` more than once, `compdump` on every start | several `compinit` calls: the framework's, one in `.zshrc`, an installer-appended `compinit -C` | keep one: let Oh My Zsh run it, put every `fpath` addition before sourcing it, delete the rest |
| `compdump` every start despite a "24 h" guard | `~/.zcompdump(#qN.mh+24)` without `setopt extendedglob` is a literal string, so the test is always true | remove the guard, or enable `extendedglob` first |
| `compdump` only in some kinds of shell | `brew shellenv` exports `FPATH`; nested and agent shells inherit a different fpath, and Oh My Zsh deletes its dump whenever the recorded fpath differs, so the two kinds of shell keep invalidating each other | key the dump by fpath (snippet below) |
| completions missing for tools set up after `compinit` | fpath appended after `compinit`; a trailing `compinit -C` reloads the dump and wipes later `compdef`s | move fpath additions above the framework; drop the trailing call |
| `eval "$(tool init)"` lines at 50-400 ms each | the tool runs on every start | cache its output per binary (helper below) |
| `pyenv rehash` taking hundreds of ms | `pyenv init -` emits a rehash | `pyenv init - --no-rehash`; pyenv's pip hook rehashes after installs |
| `gopass show`, `op read`, `gh auth token` per shell | a secret fetched for a single consumer | fetch it in a wrapper for that consumer; this also stops exporting the secret into every process |
| `brew shellenv` around 80 ms | it spawns brew | inline its output for the fixed prefix, keeping `export FPATH` |

## One dump per fpath

```zsh
typeset -U fpath
fpath=(<extra completion dirs> $fpath)
ZSH_COMPDUMP="${XDG_CACHE_HOME:-$HOME/.cache}/zsh/zcompdump-$ZSH_VERSION-${$(print -r -- $fpath | cksum)%% *}"
[[ -d ${ZSH_COMPDUMP:h} ]] || mkdir -p ${ZSH_COMPDUMP:h}
source $ZSH/oh-my-zsh.sh
```

Do not sort fpath to merge variants: order decides which completion function wins.

## Cache helper (verified under a concurrency stress test)

```zsh
_cached_eval() {
  local bin=${commands[$1]:A} cache=${XDG_CACHE_HOME:-$HOME/.cache}/zsh/eval/${(j:-:)@}.zsh key
  [[ -n $bin ]] || return 0
  [[ -r $cache ]] && read -r key < $cache
  if [[ $key != "# $bin" || $bin -nt $cache ]]; then
    [[ -d ${cache:h} ]] || mkdir -p ${cache:h}
    { print -r -- "# $bin"; command "$@" } >| $cache.$$ && mv -f $cache.$$ $cache || { rm -f $cache.$$; return 1 }
  fi
  source $cache
}
```

- The key is the resolved binary path (`:A` catches Homebrew upgrades) plus mtime (catches in-place self-updates).
- Write to `$cache.$$`, then `mv`. Writing in place let parallel shells source a half-written file and silently skip init: 6 of 60 shells fully loaded before the fix, 60 of 60 after.
- Keep stderr, so a failing tool prints its error instead of vanishing.
- **Never cache `mise activate`**, or anything whose output depends on the caller's environment. Run from a shell where mise is already active, it emits `export PATH='<that shell's PATH>'`, which freezes PATH for every later shell.
- Cache only outputs you have checked are identical in clean and inherited environments.

## Verify parity before declaring done

1. Before editing, snapshot both environments: PATH entries, `command -v` for key tools, `${#_comps}` and specific `_comps[x]`, `${#aliases}`, `${#functions}`, `precmd_functions`, `chpwd_functions`, key env vars.
2. Take the same snapshot after the edit and diff. Only intended differences may appear.
3. PATH marker: `env PATH="/tmp/marker:$PATH" zsh -lic 'echo ${path[(I)*marker]}'` must print a nonzero index.
4. Concurrency: start 12 `zsh -ic` at once with an empty, isolated `XDG_CACHE_HOME`; every shell must define the expected functions.
5. Startup best-of-3 in both environments.

## Gotchas

- `$pre PATH=x zsh` with an empty `$pre`: the assignment is not recognized after expansion, so zsh tries to run `PATH=x` as a command. Use `env -u FPATH PATH=x zsh`.
- powerlevel10k's "gitstatus failed to initialize" under heavy load is noise, not a config bug.
- Many `~/.zcompdump*.<user>.<pid>` leftovers are past rebuild races; delete them once a single `compinit` is in place.
- A stowed dotfile is live the moment you save it. Edit, verify, then commit.
