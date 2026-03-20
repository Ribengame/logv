#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
VERSION="${VERSION:-0.1.0}"
ARCH="${ARCH:-all}"
PKG_NAME="logv"
BUILD_ROOT="$ROOT_DIR/dist/deb-build/${PKG_NAME}_${VERSION}_${ARCH}"
DATA_ROOT="$BUILD_ROOT/data"
CONTROL_ROOT="$BUILD_ROOT/control"
INSTALL_DIR="$DATA_ROOT/opt/logv"
VENV_DIR="$INSTALL_DIR/.venv"
PACKAGE_PATH="$ROOT_DIR/dist/${PKG_NAME}_${VERSION}_${ARCH}.deb"

require_tool() {
  local tool="$1"
  if ! command -v "$tool" >/dev/null 2>&1; then
    echo "Missing required tool: $tool" >&2
    exit 1
  fi
}

require_tool ar
require_tool tar
require_tool python3

rm -rf "$BUILD_ROOT"
mkdir -p "$CONTROL_ROOT" "$INSTALL_DIR" "$DATA_ROOT/usr/bin"

cp -R "$ROOT_DIR"/logv "$INSTALL_DIR"/
cp "$ROOT_DIR"/pyproject.toml "$INSTALL_DIR"/
cp "$ROOT_DIR"/README.md "$INSTALL_DIR"/
cp "$ROOT_DIR"/requirements.txt "$INSTALL_DIR"/
cp "$ROOT_DIR"/LICENSE "$INSTALL_DIR"/

export PIP_DISABLE_PIP_VERSION_CHECK=1

python3 -m venv "$VENV_DIR"
"$VENV_DIR/bin/pip" install -r "$INSTALL_DIR/requirements.txt"
"$VENV_DIR/bin/pip" install "$INSTALL_DIR"

SITE_PACKAGES_DIR="$("$VENV_DIR/bin/python" -c 'import sysconfig; print(sysconfig.get_path("purelib"))')"
rm -rf \
  "$SITE_PACKAGES_DIR"/pip \
  "$SITE_PACKAGES_DIR"/pip-*.dist-info \
  "$SITE_PACKAGES_DIR"/setuptools \
  "$SITE_PACKAGES_DIR"/setuptools-*.dist-info \
  "$SITE_PACKAGES_DIR"/pkg_resources \
  "$SITE_PACKAGES_DIR"/wheel \
  "$SITE_PACKAGES_DIR"/wheel-*.dist-info
rm -f "$VENV_DIR"/bin/pip "$VENV_DIR"/bin/pip3 "$VENV_DIR"/bin/pip3.*
find "$VENV_DIR" -type d -name __pycache__ -prune -exec rm -rf {} +
find "$VENV_DIR" -type f -name '*.pyc' -delete

cat > "$DATA_ROOT/usr/bin/logv" <<'EOF'
#!/usr/bin/env bash
exec /opt/logv/.venv/bin/python -m logv.main "$@"
EOF
chmod 755 "$DATA_ROOT/usr/bin/logv"

cat > "$CONTROL_ROOT/control" <<EOF
Package: $PKG_NAME
Version: $VERSION
Section: utils
Priority: optional
Architecture: $ARCH
Maintainer: Oskar Gerlicz Kowalczuk <oskar@gerlicz.space>
Depends: python3
Description: Fast CLI/TUI log viewer for Linux terminals
 A zero-config log viewer with streaming parser, filters,
 timeline analytics, and Textual-based TUI.
EOF

mkdir -p "$ROOT_DIR/dist"
(
  cd "$DATA_ROOT"
  find opt usr -type f -print0 | sort -z | xargs -0 md5sum | sed "s#  #  #" > "$CONTROL_ROOT/md5sums"
)

printf '2.0\n' > "$BUILD_ROOT/debian-binary"
tar -C "$CONTROL_ROOT" -czf "$BUILD_ROOT/control.tar.gz" .
tar -C "$DATA_ROOT" -czf "$BUILD_ROOT/data.tar.gz" .
ar rcs "$PACKAGE_PATH" "$BUILD_ROOT/debian-binary" "$BUILD_ROOT/control.tar.gz" "$BUILD_ROOT/data.tar.gz"

echo "Built $PACKAGE_PATH"
