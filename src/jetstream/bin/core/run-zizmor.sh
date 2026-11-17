#!/usr/bin/env bash
#
# Audit the repo's GitHub Actions workflows with zizmor's auditor persona
# (every finding, however unlikely).
#
#   run-zizmor.sh [--persona regular|pedantic|auditor]

set -euo pipefail

usage() {
    echo "usage: $(basename "$0") [--persona regular|pedantic|auditor]" >&2
}

persona=auditor
while [ $# -gt 0 ]; do
    case "$1" in
        --persona)
            if [ $# -lt 2 ] || [[ ! "$2" =~ ^(regular|pedantic|auditor)$ ]]; then
                usage
                exit 1
            fi
            persona="$2"
            shift 2
            ;;
        *)
            usage
            exit 1
            ;;
    esac
done

# The tools this script runs are installed next to it, in .venv/bin.
PATH="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd):${PATH}"
cd "$(git rev-parse --show-toplevel)"

if [ -z "$(git ls-files -- .github/workflows .github/actions)" ]; then
    exit 0
fi

zizmor --offline "--persona=${persona}" .
