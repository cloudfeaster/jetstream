#!/usr/bin/env bash
#
# Check the repo's declared dependencies against what its code imports, with
# deptry: a missing, unused, transitive or misplaced dev dependency fails.
# deptry reads its settings from the repo's pyproject.toml, and by default
# leaves out tests/ and .venv.

set -euo pipefail

if [[ $# != 0 ]]; then
    echo "usage: $(basename "$0")" >&2
    exit 1
fi

# The tools this script runs are installed next to it, in .venv/bin.
PATH="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd):${PATH}"
toplevel="$(git rev-parse --show-toplevel)"
cd "${toplevel}"

deptry .
