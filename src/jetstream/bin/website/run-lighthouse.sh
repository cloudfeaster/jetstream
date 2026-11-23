#!/usr/bin/env bash
#
# Check the built site (dist/, from astro build) against jetstream's
# Lighthouse budgets (decision 25): performance at least 0.90, and
# accessibility, best practices and SEO at least 0.95. Lighthouse CI serves
# dist/ under the site's base, as it's deployed, and audits up to 5 of its
# pages, the shallowest first, 3 runs each; the reports go in .lighthouseci/.
#
# Lighthouse CI is jetstream's one Node tool. Its package.json and
# package-lock.json ship in jetstream, and the first run, or the first after
# a jetstream release changes them, installs it into .venv with npm ci. It
# needs Chrome: Google's own package, whose AppArmor profile lets Chrome use
# its sandbox on Ubuntu 23.10 and later, or any Chrome named by CHROME_PATH.

set -euo pipefail

if [[ $# != 0 ]]; then
    echo "usage: $(basename "$0")" >&2
    exit 1
fi

# The tools this script runs are installed next to it, in .venv/bin.
bin_dir="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PATH="${bin_dir}:${PATH}"
toplevel="$(git rev-parse --show-toplevel)"
cd "${toplevel}"

if [[ ! -d dist ]]; then
    echo "*** $(basename "$0"): no dist/: build the site first (node_modules/.bin/astro build)" >&2
    exit 1
fi

# the site's base, from its Astro config
site_and_base="$(run-astro-config.sh)"
base="$(sed -n 2p <<< "${site_and_base}")"

# Lighthouse CI, from jetstream's lockfile, into .venv/jetstream-node
package="$("${bin_dir}/python" -c 'import importlib.resources; print(importlib.resources.files("jetstream") / "node")')"
tools="${bin_dir}/../jetstream-node"
if ! cmp -s "${package}/package-lock.json" "${tools}/package-lock.json" || [[ ! -x "${tools}/node_modules/.bin/lhci" ]]; then
    rm -rf "${tools}"
    mkdir -p "${tools}"
    cp -R "${package}/package.json" "${package}/package-lock.json" "${package}/stubs" "${tools}/"
    # No package in the lockfile has an install script, so none is run.
    npm ci --prefix "${tools}" --ignore-scripts --no-audit --no-fund --loglevel=error
fi

# Lighthouse CI's server serves --collect.staticDistDir, so dist/ goes where
# the site's base puts it; its page discovery doesn't follow that symlink, so
# the pages are named, on any host (it uses its own).
root="$(mktemp -d)"
trap 'rm -rf "${root}"' EXIT
if [[ -n "${base}" ]]; then
    mkdir -p "$(dirname "${root}/${base}")"
    ln -s "${toplevel}/dist" "${root}/${base}"
else
    rmdir "${root}"
    ln -s "${toplevel}/dist" "${root}"
fi
urls="$(node --input-type=module -e '
import { readdirSync } from "node:fs";
const [base] = process.argv.slice(1);
const pages = readdirSync("dist", { recursive: true })
    .filter((path) => path.endsWith(".html"))
    .map((path) => path.replace(/(^|\/)index\.html$/, (_, slash) => slash))
    .sort((a, b) => a.split("/").length - b.split("/").length || a.localeCompare(b))
    .slice(0, 5);
for (const page of pages) console.log("http://localhost/" + (base ? base + "/" : "") + page);
' "${base}")"
collect=()
while IFS= read -r url; do
    collect+=("--collect.url=${url}")
done <<< "${urls}"

"${tools}/node_modules/.bin/lhci" autorun \
    --config="${package}/lighthouserc.json" \
    --collect.staticDistDir="${root}" \
    "${collect[@]}"
