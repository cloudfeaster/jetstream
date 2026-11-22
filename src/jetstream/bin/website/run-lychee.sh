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

# "<site>\n<base>\n": site as an origin, as lychee writes the URLs it parses
# (https://example.org, with no default port or trailing slash), and base
# without its leading and trailing slashes. Node reads a .ts config by
# stripping its types, so it can't read TypeScript that only compiling
# could, such as an enum.
site_and_base="$(node --input-type=module -e '
import { pathToFileURL } from "node:url";
let config;
try {
    config = (await import(pathToFileURL(process.argv[1]).href)).default;
} catch (error) {
    if (error.code !== "ERR_UNSUPPORTED_TYPESCRIPT_SYNTAX") throw error;
    console.error("*** run-lychee.sh: " + process.argv[1] + " uses TypeScript that Node can only compile, not strip, such as an enum; use a const object instead (" + error.message + ")");
    process.exit(1);
}
console.log(config.site ? new URL(config.site).origin : "");
console.log((config.base ?? "").replace(/^\/+|\/+$/g, ""));
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
    remap+=(--remap "^${site//./\\.}/ file://${root}/")
fi
# lychee resolves a scheme-relative link (//host/path) against the page's
# file:// URL, giving file://host/path; the deployed site would use its own
# scheme. A local file's URL has no host (file:///...), so it can't match.
scheme="${site%%://*}"
remap+=(--remap "^file://([^/]+)/ ${scheme:-https}://\$1/")

lychee \
    --no-progress \
    "${offline[@]}" \
    --include-fragments \
    --index-files index.html \
    --root-dir "${root}" \
    "${remap[@]}" \
    dist
