#!/usr/bin/env bash
#
# Take jetstream's latest release (decision 23): if it's newer than the repo's
# pin, set the pin to it, run uv lock, uv sync and jetstream sync, and commit
# what changed, on top of the commit checked out, to the jetstream/update
# branch, then open a pull request for it, or update the open one. With no
# newer release, close any open one. A repo whose jetstream isn't pinned to a
# release tag (jetstream itself) has nothing to update.
#
# The commit is made through GitHub's API, so GitHub signs it. gh needs a
# token that can write contents, workflows and pull requests, in GH_TOKEN;
# see .jetstream/docs/core/jetstream-update.md.

set -euo pipefail

BRANCH="jetstream/update"
BASE="main"

# All in a function, which bash reads in full before running: uv sync
# replaces this script in .venv/bin while it runs.
main() {
    if [[ $# != 0 ]]; then
        echo "usage: $(basename "$0")" >&2
        exit 1
    fi

    # The tools this script runs are installed next to it, in .venv/bin.
    PATH="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd):${PATH}"
    local toplevel
    toplevel="$(git rev-parse --show-toplevel)"
    cd "${toplevel}"

    tmp="$(mktemp -d)"
    trap 'rm -rf "${tmp}"' EXIT

    # Files, not pipes, so set -e stops the script if a command fails.
    python -I -m jetstream.update pin > "${tmp}/pin"
    if [[ ! -s "${tmp}/pin" ]]; then
        echo "update: jetstream isn't pinned to a release tag in [tool.uv.sources], so there's nothing to update"
        exit 0
    fi
    local source pin
    IFS=$'\t' read -r source pin < "${tmp}/pin"

    git ls-remote --tags --refs "${source}" > "${tmp}/tags"
    python -I -m jetstream.update newer "${pin}" < "${tmp}/tags" > "${tmp}/latest"
    gh api "repos/{owner}/{repo}/pulls?state=open&head={owner}:${BRANCH}" --jq '.[] | "\(.number)\t\(.title)"' > "${tmp}/pr"
    local number="" title=""
    if [[ -s "${tmp}/pr" ]]; then
        IFS=$'\t' read -r number title < "${tmp}/pr"
    fi

    if [[ ! -s "${tmp}/latest" ]]; then
        echo "update: jetstream ${pin} is its latest release"
        if [[ -n "${number}" ]]; then
            echo "update: closing #${number}, since the pin is already up to date"
            gh api --silent -X POST "repos/{owner}/{repo}/issues/${number}/comments" -f body="Closed by jetstream update: the jetstream pin is already ${pin}, its latest release."
            gh api --silent -X PATCH "repos/{owner}/{repo}/pulls/${number}" -f state=closed
        fi
        exit 0
    fi
    local latest want
    latest="$(cat "${tmp}/latest")"
    want="build(deps): update jetstream from ${pin} to ${latest}"

    local base base_tree
    base="$(git rev-parse HEAD)"
    base_tree="$(git rev-parse 'HEAD^{tree}')"
    # The open pull request is already for this release, on this commit.
    if [[ "${title}" == "${want}" ]]; then
        local parent
        parent="$(gh api "repos/{owner}/{repo}/commits/${BRANCH}" --jq '.parents[0].sha')"
        if [[ "${parent}" == "${base}" ]]; then
            echo "update: #${number} already updates jetstream to ${latest}"
            exit 0
        fi
    fi

    echo "update: updating jetstream from ${pin} to ${latest}"
    python -I -m jetstream.update set-pin "${latest}"
    uv lock
    uv sync
    jetstream sync
    uv lock  # in case jetstream sync changed pyproject.toml

    git status --porcelain=v1 -z --untracked-files=all > "${tmp}/status"
    python -I -m jetstream.update tree "${tmp}/status" "${base_tree}" > "${tmp}/tree.json"

    local body
    body="$(cat <<EOF
Updates jetstream from ${pin} to ${latest}: the pin in \`pyproject.toml\`, \`uv.lock\`, and what \`jetstream sync\` changes, which is what the release changes in this repo. Release notes: ${source%.git}/releases/tag/${latest}

Opened by the \`jetstream-update.yaml\` workflow, which resets \`${BRANCH}\` each time there's a newer release or \`${BASE}\` moves on, so don't push to it.
EOF
)"

    local tree commit
    tree="$(gh api -X POST "repos/{owner}/{repo}/git/trees" --input "${tmp}/tree.json" --jq .sha)"
    commit="$(gh api -X POST "repos/{owner}/{repo}/git/commits" -f message="${want}" -f tree="${tree}" -f "parents[]=${base}" --jq .sha)"
    if gh api --silent "repos/{owner}/{repo}/git/ref/heads/${BRANCH}" 2> /dev/null; then
        gh api --silent -X PATCH "repos/{owner}/{repo}/git/refs/heads/${BRANCH}" -f sha="${commit}" -F force=true
    else
        gh api --silent -X POST "repos/{owner}/{repo}/git/refs" -f ref="refs/heads/${BRANCH}" -f sha="${commit}"
    fi

    if [[ -n "${number}" ]]; then
        gh api --silent -X PATCH "repos/{owner}/{repo}/pulls/${number}" -f title="${want}" -f body="${body}"
        echo "update: updated #${number}"
    else
        gh api -X POST "repos/{owner}/{repo}/pulls" -f title="${want}" -f head="${BRANCH}" -f base="${BASE}" -f body="${body}" --jq '"update: opened #\(.number)"'
    fi
}

main "$@"
