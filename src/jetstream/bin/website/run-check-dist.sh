#!/usr/bin/env bash
#
# Fail if the built site (dist/, from astro build), which is deployed as it
# is, has something in it a site shouldn't publish: a secret (gitleaks), a
# source map, a hidden file or folder other than .well-known/, or metadata in
# an image (jetstream.dist_check).

set -euo pipefail

if [[ $# != 0 ]]; then
    echo "usage: $(basename "$0")" >&2
    exit 1
fi

# The tools this script runs are installed next to it, in .venv/bin.
bin_dir="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
toplevel="$(git rev-parse --show-toplevel)"
cd "${toplevel}"

if [[ ! -d dist ]]; then
    echo "*** $(basename "$0"): no dist/: build the site first (node_modules/.bin/astro build)" >&2
    exit 1
fi

status=0
"${bin_dir}/gitleaks" dir --redact --no-banner --log-level=warn dist || status=1
if [[ ${status} == 1 ]]; then
    echo "*** $(basename "$0"): a secret in dist/, above: take it out of the file it came from, usually in public/; a false positive goes in .gitleaksignore" >&2
fi
if ! "${bin_dir}/python" -m jetstream.dist_check dist; then
    echo "*** $(basename "$0"): dist/ has what a site shouldn't publish, above: remove it from public/ (or turn off what made it), and strip an image's metadata (exiftool -all= <image>)" >&2
    status=1
fi
exit "${status}"
