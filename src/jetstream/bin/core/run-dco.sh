#!/usr/bin/env bash
#
# commit-msg hook: fail unless the commit message has a Developer Certificate
# of Origin sign-off by the commit's author, as `git commit -s` adds.
#
#   run-dco.sh <commit message file>

set -euo pipefail

if [ $# != 1 ]; then
    echo "usage: $(basename "$0") <commit message file>" >&2
    exit 1
fi

# `git var GIT_AUTHOR_IDENT` is "Name <email> <timestamp> <timezone>".
author="$(git var GIT_AUTHOR_IDENT | sed -E 's/ [0-9]+ [-+][0-9]{4}$//')"

if ! grep -qxF "Signed-off-by: ${author}" "$1"; then
    echo "*** The commit message needs a DCO sign-off: 'Signed-off-by: ${author}'." >&2
    echo "*** Commit with 'git commit -s' (or amend with 'git commit --amend -s')." >&2
    exit 1
fi
