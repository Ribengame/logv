#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
VERSION="${VERSION:-0.1.0}"
ARCH="${ARCH:-all}"
PKG_NAME="logv"
BUILD_ROOT="$ROOT_DIR/dist/deb/${PKG_NAME}_${VERSION}_${ARCH}"
INSTALL_DIR="$BUILD_ROOT/opt/logv"
VENV_DIR="$INSTALL_DIR/.venv"

rm -rf "$BUILD_ROOT"
mkdir -p "$BUILD_ROOT/DEBIAN" "$INSTALL_DIR" "$BUILD_ROOT/usr/bin"

cp -R "$ROOT_DIR"/logv "$INSTALL_DIR"/
cp "$ROOT_DIR"/pyproject.toml "$INSTALL_DIR"/
cp "$ROOT_DIR"/README.md "$INSTALL_DIR"/
cp "$ROOT_DIR"/requirements.txt "$INSTALL_DIR"/

python3 -m venv "$VENV_DIR"
"$VENV_DIR/bin/pip" install --upgrade pip
"$VENV_DIR/bin/pip" install -r "$INSTALL_DIR/requirements.txt"
"$VENV_DIR/bin/pip" install "$INSTALL_DIR"

cat > "$BUILD_ROOT/usr/bin/logv" <<'EOF'
#!/usr/bin/env bash
exec /opt/logv/.venv/bin/logv "$@"
EOF
chmod 755 "$BUILD_ROOT/usr/bin/logv"

cat > "$BUILD_ROOT/DEBIAN/control" <<EOF
Package: $PKG_NAME
Version: $VERSION
Section: utils
Priority: optional
Architecture: $ARCH
Maintainer: OpenAI Codex <codex@example.invalid>
Depends: python3
Description: Fast CLI/TUI log viewer for Linux terminals
 A zero-config log viewer with streaming parser, filters,
 timeline analytics, and Textual-based TUI.
EOF

mkdir -p "$ROOT_DIR/dist"
dpkg-deb --build "$BUILD_ROOT" "$ROOT_DIR/dist/${PKG_NAME}_${VERSION}_${ARCH}.deb"
echo "Built $ROOT_DIR/dist/${PKG_NAME}_${VERSION}_${ARCH}.deb"
