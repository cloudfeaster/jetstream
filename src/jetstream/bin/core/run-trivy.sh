#!/usr/bin/env bash
#
# Scan the repo's lockfiles for known vulnerabilities with trivy, using the
# repo's .trivy.yaml. Temporary exceptions go in the repo's .trivyignore.

set -euo pipefail

if [[ $# != 0 ]]; then
    echo "usage: $(basename "$0")" >&2
    exit 1
fi

# The tools this script runs are installed next to it, in .venv/bin.
PATH="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd):${PATH}"
toplevel="$(git rev-parse --show-toplevel)"
cd "${toplevel}"

trivy fs --quiet --config .trivy.yaml .
