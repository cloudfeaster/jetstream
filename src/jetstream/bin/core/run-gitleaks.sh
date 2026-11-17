#!/usr/bin/env bash
#
# Scan the repo's git history for secrets with gitleaks. Findings are redacted
# in the output. A false positive goes in the repo's .gitleaksignore.

set -euo pipefail

if [ $# != 0 ]; then
    echo "usage: $(basename "$0")" >&2
    exit 1
fi

# The tools this script runs are installed next to it, in .venv/bin.
PATH="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd):${PATH}"
cd "$(git rev-parse --show-toplevel)"

gitleaks git --redact --no-banner --log-level=warn .
