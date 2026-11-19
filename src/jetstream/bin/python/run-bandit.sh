#!/usr/bin/env bash
#
# Scan every tracked *.py file for security issues with bandit, using the
# [tool.bandit] table in the repo's pyproject.toml (which leaves out tests/).

set -euo pipefail

if [[ $# != 0 ]]; then
    echo "usage: $(basename "$0")" >&2
    exit 1
fi

# The tools this script runs are installed next to it, in .venv/bin.
PATH="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd):${PATH}"
toplevel="$(git rev-parse --show-toplevel)"
cd "${toplevel}"

file_list="$(mktemp)"
trap 'rm -f "${file_list}"' EXIT
git ls-files -z -- '*.py' > "${file_list}"

files=()
while IFS= read -r -d '' file; do
    files+=("${file}")
done < "${file_list}"

if [[ ${#files[@]} -eq 0 ]]; then
    exit 0
fi

# bandit reads pyproject.toml only when it's named with -c.
bandit --quiet --configfile pyproject.toml "${files[@]}"
