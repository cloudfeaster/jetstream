#!/usr/bin/env bash
#
# Fail when committing directly to a protected branch (default: main). Work
# goes on a branch and reaches main through a PR.
#
#   run-no-commit-to-branch.sh [<branch> ...]

set -euo pipefail

if [ $# -eq 0 ]; then
    set -- main
fi

# Empty on a detached HEAD, as in CI's checkout of a PR, which is never a commit to a branch.
branch="$(git symbolic-ref --quiet --short HEAD || true)"

for protected in "$@"; do
    if [ "${branch}" = "${protected}" ]; then
        echo "*** Don't commit directly to ${protected}: create a branch and open a PR." >&2
        exit 1
    fi
done
