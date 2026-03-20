# logv

`logv` is a fast offline-first CLI/TUI log viewer for Linux terminals.

## Highlights

- zero-config entrypoint: `logv app.log`
- colorized levels and intelligent highlighting
- JSON and plain-text auto detection
- regex search and level filters
- repeated-message grouping and stack trace blocks
- live mode with burst detection
- Textual TUI with stats and timeline panels
- streaming parser and bounded in-memory buffers for large logs

## Install

### Local development

```bash
python3 -m venv .venv
. .venv/bin/activate
pip install -r requirements.txt
pip install .
```

### System install

```bash
sudo ./install.sh
```

### Build a Debian package

```bash
./packaging/build_deb.sh
```

### Build an Arch package

```bash
makepkg -si
```

## Usage

```bash
logv app.log
logv -f app.log
logv app.log --level error --regex "timeout|5.."
logv app.json --plain --export filtered.log
```

## TUI keys

- `Up/Down`: navigate
- `/`: search within current buffer
- `f`: set filter expression
- `g`: toggle grouping
- `t`: toggle timeline panel
- `r`: reload file
- `?`: help
- `q`: quit

## Filter expressions

- `/error`
- `/warn`
- `level:error,warn`
- `regex:timeout|refused`
- `gateway timeout`

## Notes

- TUI opens the full file for smaller logs and tails the last `--max-events` records for large files.
- Plain mode keeps streaming through the whole file and uses minimal memory.
