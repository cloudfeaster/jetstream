#!/usr/bin/env bash
#
# Fail unless each commit has a Developer Certificate of Origin sign-off by
# its author, as `git commit -s` adds.
#
#   run-dco.sh <commit message file>     the commit-msg hook: the commit being made
#   run-dco.sh --commits <revision range>  CI: every commit in a PR, e.g. base..head

set -euo pipefail

usage() {
    echo "usage: $(basename "$0") <commit message file> | --commits <revision range>" >&2
}

# Strip the timestamp and timezone from `git var GIT_AUTHOR_IDENT`'s "Name <email> <timestamp> <timezone>".
author_of_next_commit() {
    git var GIT_AUTHOR_IDENT | sed -E 's/ [0-9]+ [-+][0-9]{4}$//'
}

if [[ $# = 1 ]] && [[ "$1" != --commits ]]; then
    author="$(author_of_next_commit)"
    if ! grep -qxF "Signed-off-by: ${author}" "$1"; then
        echo "*** The commit message needs a DCO sign-off: 'Signed-off-by: ${author}'." >&2
        echo "*** Commit with 'git commit -s' (or amend with 'git commit --amend -s')." >&2
        exit 1
    fi
    exit 0
fi

if [[ $# != 2 ]] || [[ "$1" != --commits ]]; then
    usage
    exit 1
fi

commit_list="$(mktemp)"
trap 'rm -f "${commit_list}"' EXIT
git rev-list --no-merges "$2" > "${commit_list}"

unsigned=0
while IFS= read -r commit; do
    author="$(git log -1 --format='%an <%ae>' "${commit}")"
    if ! git log -1 --format=%B "${commit}" | grep -qxF "Signed-off-by: ${author}"; then
        subject="$(git log -1 --format=%s "${commit}")"
        echo "*** ${commit:0:12} ${subject}: no 'Signed-off-by: ${author}'" >&2
        unsigned=$((unsigned + 1))
    fi
done < "${commit_list}"

if [[ "${unsigned}" -gt 0 ]]; then
    echo "*** ${unsigned} commit(s) without a DCO sign-off by their author." >&2
    echo "*** Add them with 'git rebase --signoff <base>' and force-push the branch." >&2
    exit 1
fi
