#!/usr/bin/env bash
#
# pre-commit hook: run mado (https://github.com/akiomik/mado) on the Markdown
# files pre-commit passes in. mado isn't on PyPI (the "mado" package there is
# an unrelated project), so on first use this downloads the pinned release
# into ~/.cache/jetstream/mado/<version>/ and checks its SHA-256 first.
#
# mado reads its config from mado.toml in the current directory, which
# pre-commit sets to the root of the repo being checked.
#

set -o errexit
set -o nounset
set -o pipefail

# bin/check-tool-versions.sh compares this with the latest release of the
# repo below every night. To update, change the version and replace each
# SHA256 with the contents of the release's matching <asset>.sha256 file.
# github-release: akiomik/mado
MADO_VERSION=0.4.0

case "$(uname -s)-$(uname -m)" in
    Linux-x86_64)
        ASSET=mado-Linux-gnu-x86_64.tar.gz
        SHA256=cb540bf0af659b7add3507f57bcd4025f2b6382d1509fb56bf9dd3f624eed380
        ;;
    Linux-aarch64 | Linux-arm64)
        ASSET=mado-Linux-gnu-arm64.tar.gz
        SHA256=a9009893bdf59a81561f69a8de7d7860b3079ca148ec0a33f3ec3688d924c4e4
        ;;
    Darwin-x86_64)
        ASSET=mado-macOS-x86_64.tar.gz
        SHA256=723c21d9e02ef7612bcf62c68a795e63e297f3bece8282a7470b5ca39eb69a60
        ;;
    Darwin-arm64)
        ASSET=mado-macOS-arm64.tar.gz
        SHA256=8a646da7c4381580710594f3de54e65bc1b13e0610a6504d598e1f66f6ec9dff
        ;;
    *)
        echo "mado: unsupported platform $(uname -s)-$(uname -m)" >&2
        exit 1
        ;;
esac

CACHE_DIR="${XDG_CACHE_HOME:-${HOME}/.cache}/jetstream/mado/${MADO_VERSION}"
MADO="${CACHE_DIR}/mado"

sha256() {
    if command -v sha256sum > /dev/null; then
        sha256sum "$1" | awk '{print $1}'
    else
        shasum -a 256 "$1" | awk '{print $1}'
    fi
}

if [ ! -x "${MADO}" ]; then
    TMP_DIR="$(mktemp -d)"
    trap 'rm -rf "${TMP_DIR}"' EXIT

    curl -fsSL --retry 3 \
        -o "${TMP_DIR}/${ASSET}" \
        "https://github.com/akiomik/mado/releases/download/v${MADO_VERSION}/${ASSET}"

    ACTUAL_SHA256="$(sha256 "${TMP_DIR}/${ASSET}")"
    if [ "${ACTUAL_SHA256}" != "${SHA256}" ]; then
        echo "mado: ${ASSET} has SHA-256 ${ACTUAL_SHA256}, expected ${SHA256}" >&2
        exit 1
    fi

    tar -xzf "${TMP_DIR}/${ASSET}" -C "${TMP_DIR}" mado
    mkdir -p "${CACHE_DIR}"
    # Copy then rename, so a hook running in parallel never sees a partial file.
    cp "${TMP_DIR}/mado" "${MADO}.$$"
    chmod +x "${MADO}.$$"
    mv -f "${MADO}.$$" "${MADO}"
fi

# mado lints stdin instead of the given files if stdin has data, and hangs if
# stdin is an open pipe that never closes, so give it an empty stdin.
exec "${MADO}" check "$@" < /dev/null
