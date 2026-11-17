#!/usr/bin/env bash
#
# Compile every D2 diagram source to SVG. A source at <dir>/images/d2/<name>.d2
# becomes <dir>/images/<name>.svg, and both are committed. run-check-svg.sh
# checks they stay in step.

set -euo pipefail

if [ $# != 0 ]; then
    echo "usage: $(basename "$0")" >&2
    exit 1
fi

# The tools this script runs are installed next to it, in .venv/bin.
PATH="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd):${PATH}"
cd "$(git rev-parse --show-toplevel)"

status=0
while IFS= read -r -d '' d2_file; do
    d2_dir="$(dirname "${d2_file}")"
    if [ "$(basename "${d2_dir}")" != d2 ] || [ "$(basename "$(dirname "${d2_dir}")")" != images ]; then
        echo "D2 source outside an images/d2 directory: ${d2_file}" >&2
        status=1
        continue
    fi
    svg_file="$(dirname "${d2_dir}")/$(basename "${d2_file%.d2}").svg"
    if ! output="$(d2 --sketch "${d2_file}" "${svg_file}" 2>&1)"; then
        echo "${output}" >&2
        status=1
    fi
done < <(git ls-files -z --cached --others --exclude-standard -- '*.d2')
exit "${status}"
