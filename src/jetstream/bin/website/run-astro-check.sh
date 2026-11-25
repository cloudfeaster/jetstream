#!/usr/bin/env bash
#
# Check the site's .astro components, TypeScript and content collections, as
# astro check does. astro is the site's own devDependency, which npm ci
# installs into node_modules (cfg4dev.sh does that locally, and
# jetstream-lint.yaml in CI). @astrojs/check and TypeScript are jetstream's:
# the first run installs them into .venv (run-install-node-tool.sh).

set -euo pipefail

if [[ $# != 0 ]]; then
    echo "usage: $(basename "$0")" >&2
    exit 1
fi

# The tools this script runs are installed next to it, in .venv/bin.
bin_dir="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
toplevel="$(git rev-parse --show-toplevel)"
cd "${toplevel}"

if [[ ! -f node_modules/astro/package.json ]]; then
    echo "*** $(basename "$0"): astro isn't in node_modules: add it to package.json's devDependencies, then run npm install" >&2
    exit 1
fi

tools="$("${bin_dir}/run-install-node-tool.sh" astro-check astro-check)"

# what astro check does: generate the types, the content collections' among
# them, then check
export NODE_ENV=production
node_modules/.bin/astro sync
"${tools}/node_modules/.bin/astro-check" --root .
