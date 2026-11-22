#!/usr/bin/env bash
#
# Check the site's .astro components, TypeScript and content collections with
# astro check. astro, @astrojs/check and typescript are the site's own
# devDependencies, which npm ci installs into node_modules (cfg4dev.sh does
# that locally, and jetstream-lint.yaml in CI).

set -euo pipefail

if [[ $# != 0 ]]; then
    echo "usage: $(basename "$0")" >&2
    exit 1
fi

toplevel="$(git rev-parse --show-toplevel)"
cd "${toplevel}"

for package in astro @astrojs/check typescript; do
    if [[ ! -f "node_modules/${package}/package.json" ]]; then
        echo "*** $(basename "$0"): ${package} isn't in node_modules: add astro, @astrojs/check and typescript to package.json's devDependencies, then run npm install" >&2
        exit 1
    fi
done

node_modules/.bin/astro check
