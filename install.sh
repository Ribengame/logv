#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
INSTALL_DIR="/opt/logv"
VENV_DIR="$INSTALL_DIR/.venv"
WRAPPER="/usr/bin/logv"

if [[ "${EUID}" -ne 0 ]]; then
  echo "Run as root: sudo ./install.sh"
  exit 1
fi

mkdir -p "$INSTALL_DIR"
cp -R "$ROOT_DIR"/logv "$INSTALL_DIR"/
cp "$ROOT_DIR"/pyproject.toml "$INSTALL_DIR"/
cp "$ROOT_DIR"/README.md "$INSTALL_DIR"/
cp "$ROOT_DIR"/requirements.txt "$INSTALL_DIR"/

python3 -m venv "$VENV_DIR"
"$VENV_DIR/bin/pip" install --upgrade pip
"$VENV_DIR/bin/pip" install -r "$INSTALL_DIR/requirements.txt"
"$VENV_DIR/bin/pip" install "$INSTALL_DIR"

cat > "$WRAPPER" <<'EOF'
#!/usr/bin/env bash
exec /opt/logv/.venv/bin/logv "$@"
EOF

chmod 755 "$WRAPPER"
echo "Installed logv to $WRAPPER"
