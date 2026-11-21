#!/usr/bin/env bash
#
# Check the licenses of the repo's product dependencies, its [project]
# dependencies and theirs, against jetstream's [tool.licensecheck] keys
# (licensing.md). Dev dependencies, jetstream and the tools it installs among
# them, are development tools, so they're left out.

set -euo pipefail

if [[ $# != 0 ]]; then
    echo "usage: $(basename "$0")" >&2
    exit 1
fi

# The tools this script runs are installed next to it, in .venv/bin.
PATH="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd):${PATH}"
toplevel="$(git rev-parse --show-toplevel)"
cd "${toplevel}"

# A temporary folder, because licensecheck reads a requirements file only by its .txt name.
tmp="$(mktemp -d)"
trap 'rm -rf "${tmp}"' EXIT
requirements="${tmp}/requirements.txt"
uv export --quiet --frozen --no-dev --no-emit-project --no-hashes > "${requirements}"

# licensecheck fails when there's nothing to check, as in a new repo with no
# product dependencies yet, whose export is only uv's comment header.
if ! grep --quiet --invert-match '^#' "${requirements}"; then
    exit 0
fi

licensecheck --requirements-paths "${requirements}" --show-only-failing --zero
