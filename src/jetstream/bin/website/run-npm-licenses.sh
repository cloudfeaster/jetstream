#!/usr/bin/env bash
#
# Fail if a product dependency in package-lock.json, one that isn't a dev
# dependency, has a license licensing.md doesn't allow in a product. The
# site's devDependencies (Astro and the rest of its toolchain) are
# development tools, so they aren't checked (decision 24).

set -euo pipefail

if [[ $# != 0 ]]; then
    echo "usage: $(basename "$0")" >&2
    exit 1
fi

# The tools this script runs are installed next to it, in .venv/bin.
bin_dir="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
toplevel="$(git rev-parse --show-toplevel)"
cd "${toplevel}"

if [[ ! -f package-lock.json ]]; then
    echo "*** $(basename "$0"): no package-lock.json" >&2
    exit 1
fi

status=0
"${bin_dir}/python" -m jetstream.npm_licenses package-lock.json || status=$?
if [[ ${status} == 1 ]]; then
    echo "*** $(basename "$0"): the licenses above aren't allowed in a product dependency (.jetstream/docs/core/licensing.md); move a package that only builds the site to devDependencies, or replace it" >&2
fi
exit "${status}"
