#!/bin/sh
# install.sh — Download and install the vd CLI binary.
# Usage: curl -fsSL https://raw.githubusercontent.com/vanducng/skills/main/install.sh | sh
#
# Environment overrides:
#   VERSION     — e.g. "0.1.0" (default: latest non-prerelease)
#   INSTALL_DIR — destination directory (default: /usr/local/bin)

set -eu

REPO="vanducng/skills"
BINARY="vd"
INSTALL_DIR="${INSTALL_DIR:-/usr/local/bin}"

# ── Detect OS and arch ───────────────────────────────────────────────────────

detect_os() {
  case "$(uname -s)" in
    Darwin) echo "darwin" ;;
    Linux)  echo "linux" ;;
    *)      echo "Unsupported OS: $(uname -s)" >&2; exit 1 ;;
  esac
}

detect_arch() {
  case "$(uname -m)" in
    x86_64)  echo "x86_64" ;;
    aarch64|arm64) echo "arm64" ;;
    *)        echo "Unsupported arch: $(uname -m)" >&2; exit 1 ;;
  esac
}

OS="$(detect_os)"
ARCH="$(detect_arch)"

# ── Resolve version ───────────────────────────────────────────────────────────

if [ -z "${VERSION:-}" ]; then
  VERSION="$(curl -fsSL "https://api.github.com/repos/${REPO}/releases" \
    | grep '"tag_name"' \
    | grep '"vd/v' \
    | grep -v 'rc\|alpha\|beta\|pre' \
    | head -1 \
    | sed 's/.*"vd\/v\([^"]*\)".*/\1/')"
  if [ -z "$VERSION" ]; then
    echo "error: could not determine latest vd release" >&2
    exit 1
  fi
fi

TAG="vd/v${VERSION}"
ARCHIVE="${BINARY}_${OS}_${ARCH}.tar.gz"
BASE_URL="https://github.com/${REPO}/releases/download/${TAG}"
ARCHIVE_URL="${BASE_URL}/${ARCHIVE}"
CHECKSUM_URL="${BASE_URL}/checksums.txt"

# ── Print plan (TTY only) ─────────────────────────────────────────────────────

if [ -t 1 ]; then
  echo "Installing ${BINARY} v${VERSION} (${OS}/${ARCH}) → ${INSTALL_DIR}/${BINARY}"
fi

# ── Download to temp dir ──────────────────────────────────────────────────────

TMP="$(mktemp -d)"
trap 'rm -rf "$TMP"' EXIT

curl -fsSL -o "${TMP}/${ARCHIVE}"       "${ARCHIVE_URL}"
curl -fsSL -o "${TMP}/checksums.txt"    "${CHECKSUM_URL}"

# ── Verify checksum ───────────────────────────────────────────────────────────

cd "$TMP"
# Extract only the line for this archive; shasum -a 256 --check needs it
grep "${ARCHIVE}" checksums.txt > "${TMP}/check.txt"
if command -v sha256sum >/dev/null 2>&1; then
  sha256sum --check --status "${TMP}/check.txt"
elif command -v shasum >/dev/null 2>&1; then
  shasum -a 256 --check --status "${TMP}/check.txt"
else
  echo "warning: no sha256sum or shasum found — skipping checksum verification" >&2
fi

# ── Extract and install ───────────────────────────────────────────────────────

tar -xzf "${TMP}/${ARCHIVE}" -C "${TMP}"

INSTALL_PATH="${INSTALL_DIR}/${BINARY}"

if [ -w "${INSTALL_DIR}" ]; then
  mv "${TMP}/${BINARY}" "${INSTALL_PATH}"
else
  if [ -t 0 ]; then
    echo "sudo required to install to ${INSTALL_DIR}"
    sudo mv "${TMP}/${BINARY}" "${INSTALL_PATH}"
  else
    echo "error: ${INSTALL_DIR} is not writable and stdin is not a TTY (cannot prompt for sudo)" >&2
    echo "       Set INSTALL_DIR to a writable path, e.g.: INSTALL_DIR=\$HOME/.local/bin sh install.sh" >&2
    exit 1
  fi
fi

chmod +x "${INSTALL_PATH}"

if [ -t 1 ]; then
  echo "Installed: $("${INSTALL_PATH}" --version)"
fi
