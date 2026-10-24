# structured

Unofficial command-line and terminal interface for the [Structured](https://structured.app) day planner.

This project is not affiliated with Structured, unorderly, or Leo Mehlig.

`structured` is a CLI for scripts and agents, and a vim-style TUI for a person. Both talk to Structured Cloud. A terminal with no subcommand opens the TUI.

[![structured demo: text timeline, time zones, refs, subtasks, recurring scope, dry run, and the TUI](docs/assets/demo.gif)](https://asciinema.org/a/1269647)

The demo runs on generic sample tasks. [Play it on asciinema](https://asciinema.org/a/1269647) to pause it or copy the text.

## Install

Download the archive for your machine from the [latest release](https://github.com/vanducng/structured/releases/latest), check it, and put `structured` on `PATH`. Archives exist for `aarch64-apple-darwin` and `x86_64-unknown-linux-gnu`. Upgrading is the same steps.

```bash
tag=$(gh release view --repo vanducng/structured --json tagName -q .tagName)
target=aarch64-apple-darwin
gh release download "$tag" --repo vanducng/structured -p "structured-$tag-$target.tar.gz" -p SHA256SUMS
shasum -a 256 -c SHA256SUMS --ignore-missing
tar -xzf "structured-$tag-$target.tar.gz"
install -m 755 "structured-$tag-$target/structured" ~/.local/bin/structured
```

Or build from source with Rust 1.88 or newer:

```bash
cargo install --git https://github.com/vanducng/structured
```

## Quick start

```bash
structured login                  # once, in a terminal; opens the browser
structured                        # the TUI
structured today --text           # today as a readable timeline
structured now --json             # 12 hours either side of now, as JSON
structured add "Write the note" --day +1 --time 09:30 --subtask Outline
structured done REF               # REF is the "ref" field from --json output
```

To work in another time zone and open the TUI on the rolling 24 hours, put this in `~/.config/structured/config.toml`:

```toml
view = "now"
timezones = ["ET=America/New_York", "Saigon=Asia/Ho_Chi_Minh"]
```

`z` in the TUI switches between the zones. `--tz saigon` does the same for one command.

## Docs

| Page | What it covers |
| --- | --- |
| [CLI](docs/cli.md) | Commands, JSON output and errors, refs, recurring days, the text timeline |
| [TUI](docs/tui.md) | Day and 24h views, time zones, keys, prompts, saving |
| [Configuration](docs/configuration.md) | `config.toml`, `--tz`, files, and environment variables |
| [System architecture](docs/system-architecture.md) | How the CLI, TUI, and Structured Cloud fit together |
| [Tech stack](docs/tech-stack.md) | Language, crates, and services |
| [Development](docs/development-guidelines.md) | Checks, layout, tests, and the TUI screen check |
| [Deployment](docs/deployment.md) | CI, release-please, release assets, and rollback |

## License

MIT. See [LICENSE](LICENSE).
