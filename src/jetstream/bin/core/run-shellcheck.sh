#!/usr/bin/env bash
#
# Lint every tracked *.sh file with shellcheck, using the repo's .shellcheckrc.

set -euo pipefail

if [ $# != 0 ]; then
    echo "usage: $(basename "$0")" >&2
    exit 1
fi

# The tools this script runs are installed next to it, in .venv/bin.
PATH="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd):${PATH}"
cd "$(git rev-parse --show-toplevel)"

files=()
while IFS= read -r -d '' file; do
    files+=("${file}")
done < <(git ls-files -z -- '*.sh')

if [ ${#files[@]} -eq 0 ]; then
    exit 0
fi

shellcheck "${files[@]}"
