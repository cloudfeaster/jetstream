#!/usr/bin/env bash
#
# Check the links in the built site (dist/, from astro build) with lychee:
# links between its pages and files, and #fragments. With --external, links
# to other sites too; without it, lychee makes no network requests.
#
# Links are checked as the deployed site would resolve them. The site's
# `site` and `base`, read from its Astro config, map root-relative links
# (/<base>/...) and absolute links to the site itself (<site>/<base>/...)
# onto dist/.

set -euo pipefail

usage() {
    echo "usage: $(basename "$0") [--external]" >&2
    exit 1
}

offline=(--offline)
if [[ $# == 1 && $1 == --external ]]; then
    offline=()
elif [[ $# != 0 ]]; then
    usage
fi

# The tools this script runs are installed next to it, in .venv/bin.
PATH="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd):${PATH}"
toplevel="$(git rev-parse --show-toplevel)"
cd "${toplevel}"

if [[ ! -d dist ]]; then
    echo "*** $(basename "$0"): no dist/: build the site first (node_modules/.bin/astro build)" >&2
    exit 1
fi

config=""
for name in astro.config.mjs astro.config.mts astro.config.ts astro.config.js; do
    if [[ -f "${name}" ]]; then
        config="${name}"
        break
    fi
done
if [[ -z "${config}" ]]; then
    echo "*** $(basename "$0"): no astro.config.mjs (or .mts, .ts, .js)" >&2
    exit 1
fi

# "<site>\n<base>\n", each without its trailing slash, and base without its leading one
site_and_base="$(node --input-type=module -e '
import { pathToFileURL } from "node:url";
const config = (await import(pathToFileURL(process.argv[1]).href)).default;
const trim = (value) => (value ?? "").replace(/^\/+|\/+$/g, "");
console.log((config.site ?? "").replace(/\/+$/, ""));
console.log(trim(config.base));
' "${config}")"
site="$(sed -n 1p <<< "${site_and_base}")"
base="$(sed -n 2p <<< "${site_and_base}")"

# lychee resolves a root-relative link under --root-dir, so dist/ goes where
# the site's base puts it.
root="$(mktemp -d)"
trap 'rm -rf "${root}"' EXIT
if [[ -n "${base}" ]]; then
    mkdir -p "$(dirname "${root}/${base}")"
    ln -s "${toplevel}/dist" "${root}/${base}"
else
    rmdir "${root}"
    ln -s "${toplevel}/dist" "${root}"
fi

remap=()
if [[ -n "${site}" ]]; then
    # the site's own absolute links are checked against dist/, not the deployed site
    # (site is a scheme, host and port, so . is the only regex character in it)
    remap=(--remap "^${site//./\\.}/ file://${root}/")
fi

lychee \
    --no-progress \
    "${offline[@]}" \
    --include-fragments \
    --index-files index.html \
    --root-dir "${root}" \
    "${remap[@]}" \
    dist
