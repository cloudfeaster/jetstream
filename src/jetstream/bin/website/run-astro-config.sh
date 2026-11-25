#!/usr/bin/env bash
#
# Print the site's `site` and `base`, from its Astro config, one per line:
# site as an origin, as browsers and lychee write URLs (https://example.org,
# with no default port or trailing slash), and base without its leading and
# trailing slashes. Either line is empty when the config doesn't set it.
# run-lychee.sh and run-lighthouse.sh use it to check the built site as it's
# deployed, under its base.
#
# Node reads a .ts config by stripping its types, so it can't read TypeScript
# that only compiling could, such as an enum.

set -euo pipefail

if [[ $# != 0 ]]; then
    echo "usage: $(basename "$0")" >&2
    exit 1
fi

toplevel="$(git rev-parse --show-toplevel)"
cd "${toplevel}"

if ! command -v node > /dev/null; then
    echo "*** $(basename "$0"): node isn't installed: install Node, at the major version in .nvmrc" >&2
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

node --input-type=module -e '
import { pathToFileURL } from "node:url";
let config;
try {
    config = (await import(pathToFileURL(process.argv[1]).href)).default;
} catch (error) {
    if (error.code !== "ERR_UNSUPPORTED_TYPESCRIPT_SYNTAX") throw error;
    console.error("*** run-astro-config.sh: " + process.argv[1] + " uses TypeScript that Node can only compile, not strip, such as an enum; use a const object instead (" + error.message + ")");
    process.exit(1);
}
console.log(config.site ? new URL(config.site).origin : "");
console.log((config.base ?? "").replace(/^\/+|\/+$/g, ""));
' "${config}"
