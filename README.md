# logv

`logv` is a fast, offline-first CLI/TUI log viewer for Linux terminals.

It is built for the common workflow of:

- opening huge log files quickly
- spotting errors without writing ad-hoc `grep` chains
- switching between plain text and JSON logs without changing tools
- following live logs with useful context instead of raw `tail -f`

Think of it as a lightweight blend of `less`, `jq`, `grep`, and `tail -f`, with a simpler entrypoint:

```bash
logv app.log
```

![logv screenshot](https://github.com/Ribengame/logv/blob/main/screenshots/logv.png)

*logs from simple ping command*

## Why `logv`

Most terminal log workflows are powerful but fragmented. You end up bouncing between:

- `less` for navigation
- `grep` or regex for filtering
- `jq` for JSON logs
- `tail -f` for live streams
- custom shell aliases for colors and quick views

`logv` pulls the common cases into one tool:

- one command to open a log file
- automatic JSON/plain-text detection
- level-aware coloring
- fast search and filtering
- grouped repeated messages
- stack trace blocks
- timeline summaries
- bounded-memory live mode

## Features

### Core viewing

- zero-config entrypoint: `logv app.log`
- interactive TUI powered by Textual
- plain streaming mode for scripts and pipes
- bounded memory usage in interactive mode for large files

### Log intelligence

- level detection for `ERROR`, `WARN`, `INFO`, `DEBUG`
- automatic JSON and plain-text parsing
- timestamp detection
- stack trace grouping into a single logical event
- repeated-message grouping by normalized fingerprints

### Highlighting

- HTTP status highlighting for `4xx` and `5xx`
- IP address highlighting
- URL highlighting
- timestamp highlighting
- stack trace line highlighting

### Filtering and search

- level filters via `--level` and interactive filters
- regex filters via `--regex`
- free-text search
- quick interactive filters such as `/error` and `/warn`

### Live mode

- `logv -f app.log`
- follows appended data like `tail -f`
- keeps the interface responsive
- detects bursts of `ERROR` events

### Timeline

- per-bucket error timeline
- spike detection for error bursts
- compact terminal-friendly sparkline summary

## Installation

### Quick install

Clone the repository and let `install.sh` choose the installation strategy automatically:

```bash
git clone https://github.com/Ribengame/logv && cd logv && sudo ./install.sh
```

Installation behavior:

- Debian-like systems: build and install a local `.deb`
- other Linux distributions: install a portable build into `/opt/logv`
- wrapper command exposed as `/usr/bin/logv`

### Arch Linux

`logv` is available on AUR as `logv`.

- `yay -S logv`
- `paru -S logv`

AUR package:

- https://aur.archlinux.org/packages/logv

### Debian / Ubuntu

If you have a built package:

```bash
sudo apt install ./logv_0.1.0_all.deb
```

Or install with `dpkg`:

```bash
sudo dpkg -i ./logv_0.1.0_all.deb
```

To build the Debian package locally:

```bash
./packaging/build_deb.sh
```

### From source

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
pip install .
```

### Local system install

```bash
sudo ./install.sh
```

## Quick start

Open a file in TUI mode:

```bash
logv app.log
```

Follow a live log:

```bash
logv -f app.log
```

Filter by level:

```bash
logv app.log --level error
```

Use regex filtering:

```bash
logv app.log --regex "timeout|refused|5.."
```

Export matched events:

```bash
logv app.log --plain --level error --export filtered-errors.log
```

Save a session summary:

```bash
logv app.log --plain --save-session session.json
```

## Usage examples

Structured JSON logs:

```bash
logv app.json
```

Plain mode for shell workflows:

```bash
logv app.log --plain
```

Grouping repeated messages:

```bash
logv app.log --group
```

Combining filters:

```bash
logv app.log --level error --regex "postgres|timeout"
```

## TUI controls

- `Up` / `Down`: navigate rows
- `/`: search within the current buffer
- `f`: open filter prompt
- `g`: toggle grouping
- `t`: toggle timeline panel
- `r`: reload file
- `?`: show help
- `q`: quit

## Filter syntax

Examples:

- `/error`
- `/warn`
- `level:error,warn`
- `regex:timeout|refused`
- `gateway timeout`
- `re:5[0-9]{2}`

## Project layout

```text
logv/
├── logv/
│   ├── main.py
│   ├── parser.py
│   ├── highlighter.py
│   ├── filters.py
│   ├── timeline.py
│   ├── tui.py
│   ├── live.py
│   └── utils.py
├── samples/
├── tests/
├── packaging/
├── PKGBUILD
├── pyproject.toml
└── requirements.txt
```

## Development

Run tests:

```bash
python3 -m unittest discover -s tests -v
```

Run the sample log:

```bash
logv samples/app.log
```

Prepare AUR metadata from an upstream GitHub repo:

```bash
./packaging/prepare_aur.sh \
  --upstream-url https://github.com/Ribengame/logv \
  --aur-remote ssh://aur@aur.archlinux.org/logv.git
```

## Notes

- TUI loads the full file for smaller logs and falls back to bounded history for larger inputs.
- Plain mode keeps memory usage low by streaming events instead of loading the whole file into memory.
- The Debian package bundles its Python runtime environment under `/opt/logv` and exposes `/usr/bin/logv`.
- `logv` works fully offline at runtime.

## License

MIT. See [`LICENSE`](LICENSE).
