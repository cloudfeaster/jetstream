#!/usr/bin/env bash
#
# Score every tracked *.py file with pyscn (complexity, dead code, clones,
# coupling and cohesion), and fail if the health score is below the floor.
# For the details, run `pyscn analyze --html .`.

set -euo pipefail

MIN_HEALTH_SCORE=90

if [[ $# != 0 ]]; then
    echo "usage: $(basename "$0")" >&2
    exit 1
fi

# The tools this script runs are installed next to it, in .venv/bin.
PATH="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd):${PATH}"
toplevel="$(git rev-parse --show-toplevel)"
cd "${toplevel}"

file_list="$(mktemp)"
report="$(mktemp)"
log="$(mktemp)"
trap 'rm -f "${file_list}" "${report}" "${log}"' EXIT
git ls-files -z -- '*.py' > "${file_list}"

files=()
while IFS= read -r -d '' file; do
    files+=("${file}")
done < "${file_list}"

if [[ ${#files[@]} -eq 0 ]]; then
    exit 0
fi

# pyscn writes a summary, a README badge and a plug to stderr; show them only if it fails.
if ! pyscn analyze --json --output - "${files[@]}" > "${report}" 2> "${log}"; then
    cat "${log}" >&2
    exit 1
fi
score="$(jq '.summary.health_score' "${report}")"
grade="$(jq -r '.summary.grade' "${report}")"

if [[ "${score}" -lt "${MIN_HEALTH_SCORE}" ]]; then
    echo "pyscn: health score ${score} (${grade}) is below ${MIN_HEALTH_SCORE}; run \`pyscn analyze --html .\` for the details" >&2
    exit 1
fi
echo "pyscn: health score ${score} (${grade})"
