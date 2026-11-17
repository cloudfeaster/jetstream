#!/usr/bin/env bash
#
# Lint the repo's Markdown with mado, using the repo's mado.toml.

set -euo pipefail

if [ $# != 0 ]; then
    echo "usage: $(basename "$0")" >&2
    exit 1
fi

# The tools this script runs are installed next to it, in .venv/bin.
PATH="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd):${PATH}"
cd "$(git rev-parse --show-toplevel)"

# mado lints stdin instead of "." when stdin has data, and waits forever on
# an open pipe that never sends any, so give it nothing to read.
mado check . < /dev/null
