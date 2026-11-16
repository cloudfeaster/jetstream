#!/usr/bin/env bash
#
# Pin the mado hooks to another mado release: set MADO_VERSION and each
# platform's SHA-256 in hooks/core/install-mado.sh from the release's .sha256
# files, and replace the vendored config schema with that release's.
#
# Run it when bin/check-tool-versions.sh reports mado is out of date, then run
# pre-commit to regenerate jetstream's mado.toml and review the diff.
#

set -o errexit
set -o nounset
set -o pipefail

usage() {
    echo "usage: $(basename "$0") <version, e.g. 0.4.0>" >&2
}

if [ $# != 1 ] || [[ ! "$1" =~ ^[0-9]+\.[0-9]+\.[0-9]+$ ]]; then
    usage
    exit 1
fi
VERSION="$1"

REPO_ROOT_DIR="$(git rev-parse --show-toplevel)"
INSTALL_SCRIPT="${REPO_ROOT_DIR}/hooks/core/install-mado.sh"
RELEASE_URL="https://github.com/akiomik/mado/releases/download/v${VERSION}"

TMP_DIR="$(mktemp -d)"
trap 'rm -rf "${TMP_DIR}"' EXIT

cp "${INSTALL_SCRIPT}" "${TMP_DIR}/install-mado.sh"
sed -i -e "s/^MADO_VERSION=.*/MADO_VERSION=${VERSION}/" "${TMP_DIR}/install-mado.sh"

# Each SHA256= line follows the ASSET= line it belongs to.
while IFS= read -r ASSET; do
    SHA256="$(curl -fsSL --retry 3 "${RELEASE_URL}/${ASSET}.sha256" | awk '{print $1}')"
    if [[ ! "${SHA256}" =~ ^[0-9a-f]{64}$ ]]; then
        echo "${ASSET}.sha256: expected a SHA-256, got >>>${SHA256}<<<" >&2
        exit 1
    fi
    awk -v asset="${ASSET}" -v sha256="${SHA256}" '
        $0 ~ "^ *ASSET=" asset "$" { found = 1 }
        found && /^ *SHA256=/ { sub(/SHA256=.*/, "SHA256=" sha256); found = 0 }
        { print }
    ' "${TMP_DIR}/install-mado.sh" > "${TMP_DIR}/install-mado.sh.new"
    mv "${TMP_DIR}/install-mado.sh.new" "${TMP_DIR}/install-mado.sh"
done < <(sed -n -e 's/^ *ASSET=//p' "${INSTALL_SCRIPT}")

curl -fsSL --retry 3 \
    -o "${TMP_DIR}/schema.json" \
    "https://raw.githubusercontent.com/akiomik/mado/v${VERSION}/pkg/json-schema/mado.json"
python3 -c 'import json, sys; json.load(open(sys.argv[1]))' "${TMP_DIR}/schema.json"

# Only change the repo once every download has worked.
cp "${TMP_DIR}/install-mado.sh" "${INSTALL_SCRIPT}"
find "${REPO_ROOT_DIR}/hooks/core" -name 'mado-*.schema.json' -delete
cp "${TMP_DIR}/schema.json" "${REPO_ROOT_DIR}/hooks/core/mado-${VERSION}.schema.json"
git -C "${REPO_ROOT_DIR}" add --all hooks/core

echo "mado pinned to ${VERSION}. Now run pre-commit to regenerate mado.toml, and review the diff."
exit 0
