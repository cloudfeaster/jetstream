#!/usr/bin/env bash
#
# Scan the repo's lockfiles for known vulnerabilities with trivy, using the
# repo's .trivy.yaml. Temporary exceptions are jetstream's, for the tools it
# installs (.jetstream/trivyignore, written by jetstream sync), and the repo's,
# for its own dependencies (.trivyignore).

set -euo pipefail

if [[ $# != 0 ]]; then
    echo "usage: $(basename "$0")" >&2
    exit 1
fi

# The tools this script runs are installed next to it, in .venv/bin.
PATH="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd):${PATH}"
toplevel="$(git rev-parse --show-toplevel)"
cd "${toplevel}"

# trivy reads only one ignore file, so scan with both in one.
ignorefile="$(mktemp)"
trap 'rm -f "${ignorefile}"' EXIT
for exceptions in .jetstream/trivyignore .trivyignore; do
    if [[ -f "${exceptions}" ]]; then
        cat "${exceptions}"
    fi
done > "${ignorefile}"

trivy fs --quiet --config .trivy.yaml --ignorefile "${ignorefile}" .
