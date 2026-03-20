#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
VERSION="${VERSION:-0.1.0}"
INSTALL_MODE="${LOGV_INSTALL_MODE:-auto}"
INSTALL_DIR="/opt/logv"
VENV_DIR="$INSTALL_DIR/.venv"
WRAPPER="/usr/bin/logv"

log() {
  printf '[logv-install] %s\n' "$*"
}

require_root() {
  if [[ "${EUID}" -ne 0 ]]; then
    echo "Run as root: sudo ./install.sh" >&2
    exit 1
  fi
}

command_exists() {
  command -v "$1" >/dev/null 2>&1
}

require_tool() {
  local tool="$1"
  if ! command_exists "$tool"; then
    echo "Missing required tool: $tool" >&2
    exit 1
  fi
}

detect_linux_family() {
  local id=""
  local id_like=""

  if [[ -r /etc/os-release ]]; then
    # shellcheck disable=SC1091
    . /etc/os-release
    id="${ID:-}"
    id_like="${ID_LIKE:-}"
  fi

  case " ${id} ${id_like} " in
    *debian*|*ubuntu*|*linuxmint*|*pop*)
      echo "debian"
      ;;
    *arch*|*endeavouros*|*manjaro*)
      echo "arch"
      ;;
    *fedora*|*rhel*|*centos*|*rocky*|*almalinux*)
      echo "rpm"
      ;;
    *)
      echo "generic"
      ;;
  esac
}

strip_build_only_runtime() {
  local site_packages_dir
  site_packages_dir="$("$VENV_DIR/bin/python" -c 'import sysconfig; print(sysconfig.get_path("purelib"))')"

  rm -rf \
    "$site_packages_dir"/pip \
    "$site_packages_dir"/pip-*.dist-info \
    "$site_packages_dir"/setuptools \
    "$site_packages_dir"/setuptools-*.dist-info \
    "$site_packages_dir"/pkg_resources \
    "$site_packages_dir"/wheel \
    "$site_packages_dir"/wheel-*.dist-info

  rm -f "$VENV_DIR"/bin/pip "$VENV_DIR"/bin/pip3 "$VENV_DIR"/bin/pip3.*
  find "$VENV_DIR" -type d -name __pycache__ -prune -exec rm -rf {} +
  find "$VENV_DIR" -type f -name '*.pyc' -delete
}

write_wrapper() {
  cat > "$WRAPPER" <<'EOF'
#!/usr/bin/env bash
exec /opt/logv/.venv/bin/python -m logv.main "$@"
EOF
  chmod 755 "$WRAPPER"
}

portable_install() {
  require_root
  require_tool python3

  log "Installing portable build into $INSTALL_DIR"
  rm -rf "$INSTALL_DIR"
  mkdir -p "$INSTALL_DIR"

  cp -R "$ROOT_DIR"/logv "$INSTALL_DIR"/
  cp "$ROOT_DIR"/pyproject.toml "$INSTALL_DIR"/
  cp "$ROOT_DIR"/README.md "$INSTALL_DIR"/
  cp "$ROOT_DIR"/requirements.txt "$INSTALL_DIR"/
  cp "$ROOT_DIR"/LICENSE "$INSTALL_DIR"/

  export PIP_DISABLE_PIP_VERSION_CHECK=1
  python3 -m venv "$VENV_DIR"
  "$VENV_DIR/bin/pip" install -r "$INSTALL_DIR/requirements.txt"
  "$VENV_DIR/bin/pip" install "$INSTALL_DIR"

  strip_build_only_runtime
  write_wrapper

  log "Installed logv to $WRAPPER"
}

debian_install() {
  require_root
  require_tool python3
  require_tool dpkg

  log "Detected Debian-like system; building local .deb package"
  "$ROOT_DIR/packaging/build_deb.sh"

  local package_path="$ROOT_DIR/dist/logv_${VERSION}_all.deb"
  if [[ ! -f "$package_path" ]]; then
    echo "Expected package not found: $package_path" >&2
    exit 1
  fi

  log "Installing $package_path"
  if ! dpkg -i "$package_path"; then
    if command -v apt-get >/dev/null 2>&1; then
      apt-get install -f -y
    else
      echo "dpkg reported missing dependencies and apt-get is not available." >&2
      exit 1
    fi
  fi

  log "Installed logv from Debian package"
}

arch_install_yay() {
  require_tool yay

  if [[ "${EUID}" -eq 0 ]]; then
    local target_user="${SUDO_USER:-}"
    if [[ -z "$target_user" || "$target_user" == "root" ]]; then
      echo "On Arch, run this script from your user account with sudo so it can invoke yay safely." >&2
      echo "Example: git clone https://github.com/Ribengame/logv && cd logv && sudo ./install.sh" >&2
      exit 1
    fi

    if command_exists sudo; then
      log "Detected Arch-like system; installing AUR package via yay as ${target_user}"
      sudo -H -u "$target_user" yay -S --needed logv
      return
    fi

    if command_exists runuser; then
      log "Detected Arch-like system; installing AUR package via yay as ${target_user}"
      runuser -u "$target_user" -- yay -S --needed logv
      return
    fi

    echo "Unable to drop privileges to ${target_user}. Install sudo or run the script as that user." >&2
    exit 1
  fi

  log "Detected Arch-like system; installing AUR package via yay"
  yay -S --needed logv
}

main() {
  local family
  local mode
  family="$(detect_linux_family)"
  mode="$INSTALL_MODE"

  if [[ "$mode" == "auto" ]]; then
    if [[ "$family" == "debian" ]]; then
      mode="deb"
    elif [[ "$family" == "arch" ]] && command_exists yay; then
      mode="aur"
    else
      mode="portable"
    fi
  fi

  log "Detected Linux family: $family"
  log "Selected install mode: $mode"

  case "$mode" in
    aur)
      arch_install_yay
      ;;
    deb)
      debian_install
      ;;
    portable)
      portable_install
      ;;
    *)
      echo "Unsupported LOGV_INSTALL_MODE: $mode" >&2
      echo "Use one of: auto, aur, deb, portable" >&2
      exit 1
      ;;
  esac
}

main "$@"
