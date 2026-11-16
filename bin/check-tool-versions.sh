#!/usr/bin/env bash
#
# Check every tool a hooks/ script downloads is pinned to its latest release.
# Dependabot can't see these pins (it bumps the Python tools in
# pyproject.toml), so the nightly-tool-versions workflow runs this instead.
#
# A hook script declares a pin as a "# github-release: <owner>/<repo>" comment
# followed by a <NAME>_VERSION=<version> line. Prints one PASS/FAIL/WAIT line
# per pin and exits non-zero if any pin is behind a release that's older than
# the cooldown, matching Dependabot's cooldown so both wait the same time.
#
# Needs gh, logged in or with GH_TOKEN set.
#

set -o errexit
set -o nounset
set -o pipefail

COOLDOWN_DAYS=7

usage() {
    echo "usage: $(basename "$0")" >&2
}

if [ $# != 0 ]; then
    usage
    exit 1
fi

REPO_ROOT_DIR="$(git rev-parse --show-toplevel)"
NOW="$(date -u +%s)"
FAILURES=0

while IFS= read -r HOOK; do
    # Each "# github-release:" comment and the first *_VERSION= line after it.
    while IFS=$'\t' read -r UPSTREAM PINNED; do
        if [ -z "${PINNED}" ]; then
            echo "FAIL: ${HOOK#"${REPO_ROOT_DIR}/"}: no <NAME>_VERSION= line after '# github-release: ${UPSTREAM}'"
            FAILURES=$((FAILURES + 1))
            continue
        fi

        # A plain assignment, so errexit stops the script if gh fails.
        RELEASE="$(gh api "repos/${UPSTREAM}/releases/latest" --jq '[.tag_name, .published_at] | @tsv')"
        IFS=$'\t' read -r TAG PUBLISHED_AT <<< "${RELEASE}"
        LATEST="${TAG#v}"
        AGE_DAYS=$(((NOW - $(date -u -d "${PUBLISHED_AT}" +%s)) / 86400))

        if [ "${LATEST}" == "${PINNED}" ]; then
            echo "PASS: ${UPSTREAM} pinned to the latest release, ${PINNED}"
        elif [ "${AGE_DAYS}" -lt "${COOLDOWN_DAYS}" ]; then
            echo "WAIT: ${UPSTREAM} ${LATEST} is ${AGE_DAYS} day(s) old; ${PINNED} stays pinned until it's ${COOLDOWN_DAYS}"
        else
            echo "FAIL: ${UPSTREAM} pinned to ${PINNED}, latest is ${LATEST} (${AGE_DAYS} days old); update ${HOOK#"${REPO_ROOT_DIR}/"}"
            FAILURES=$((FAILURES + 1))
        fi
    done < <(
        awk '
            /^# github-release:/ { if (upstream != "") print upstream "\t"; upstream = $3; next }
            upstream != "" && /^[A-Z_]+_VERSION=/ { sub(/^[A-Z_]+_VERSION=/, ""); print upstream "\t" $0; upstream = "" }
            END { if (upstream != "") print upstream "\t" }
        ' "${HOOK}"
    )
done < <(grep -rl --include='*.sh' '^# github-release:' "${REPO_ROOT_DIR}/hooks" | sort)

if [ "${FAILURES}" != 0 ]; then
    echo "${FAILURES} tool pin(s) out of date" >&2
    exit 1
fi

exit 0
