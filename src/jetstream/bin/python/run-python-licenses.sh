#!/usr/bin/env bash
#
# Fail if a product dependency, one of the repo's [project] dependencies or
# theirs, has a license licensing.md doesn't allow in a product
# (jetstream.python_licenses). Dev dependencies, jetstream and the tools it
# installs among them, are development tools, so they're left out.

set -euo pipefail

if [[ $# != 0 ]]; then
    echo "usage: $(basename "$0")" >&2
    exit 1
fi

# The tools this script runs are installed next to it, in .venv/bin.
bin_dir="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
toplevel="$(git rev-parse --show-toplevel)"
cd "${toplevel}"

export_="$(uv export --quiet --frozen --no-dev --no-emit-project --no-hashes)"

status=0
"${bin_dir}/python" -m jetstream.python_licenses pyproject.toml <<< "${export_}" || status=$?
if [[ ${status} == 1 ]]; then
    echo "*** $(basename "$0"): the licenses above aren't allowed in a product dependency, or need a review (.jetstream/docs/core/licensing.md); move a package only the repo's development needs to [dependency-groups] dev, or replace it" >&2
fi
exit "${status}"
