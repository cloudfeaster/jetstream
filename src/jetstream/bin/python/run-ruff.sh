#!/usr/bin/env bash
#
# Lint and format-check every tracked *.py file with ruff, using the
# [tool.ruff] tables in the repo's pyproject.toml. Nothing is changed: run
# `ruff check --fix` and `ruff format` to fix what it reports.

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

# --force-exclude applies the repo's [tool.ruff] exclude to the files named here.
status=0
ruff check --force-exclude "${files[@]}" || status=$?
ruff format --check --force-exclude "${files[@]}" || status=$?
exit "${status}"
