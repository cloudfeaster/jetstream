#!/usr/bin/env bash
#
# Fail if a tracked JSON file is invalid, or isn't formatted the way `jq .`
# formats it. Files matching a pattern (git pathspec glob) in the repo's
# .jsonlintignore are skipped, e.g. .vscode/* (VS Code settings are JSONC).

set -euo pipefail

if [[ $# != 0 ]]; then
    echo "usage: $(basename "$0")" >&2
    exit 1
fi

# The tools this script runs are installed next to it, in .venv/bin.
PATH="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd):${PATH}"
toplevel="$(git rev-parse --show-toplevel)"
cd "${toplevel}"

pathspecs=('*.json')
if [[ -f .jsonlintignore ]]; then
    while IFS= read -r pattern; do
        case "${pattern}" in
            '' | '#'*) ;;
            *) pathspecs+=(":!${pattern}") ;;
        esac
    done < .jsonlintignore
fi

file_list="$(mktemp)"
trap 'rm -f "${file_list}"' EXIT
git ls-files -z -- "${pathspecs[@]}" > "${file_list}"

invalid=0
unformatted=0
while IFS= read -r -d '' file; do
    if ! jq . "${file}" > /dev/null 2>&1; then
        echo "Invalid JSON: ${file}" >&2
        invalid=$((invalid + 1))
    elif ! jq . "${file}" | cmp -s - "${file}"; then
        echo "Unformatted JSON: ${file} (fix with: jq . ${file} > tmp && mv tmp ${file})" >&2
        unformatted=$((unformatted + 1))
    fi
done < "${file_list}"

if [[ "${invalid}" -gt 0 ]] || [[ "${unformatted}" -gt 0 ]]; then
    echo "JSON lint failed: ${invalid} invalid file(s), ${unformatted} unformatted file(s)" >&2
    exit 1
fi
