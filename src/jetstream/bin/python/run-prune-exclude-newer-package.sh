#!/usr/bin/env bash
#
# Report each [tool.uv] exclude-newer-package override that no longer changes
# what uv locks, and fail if there's one, so it's removed. An override lets a
# package past the exclude-newer cooldown, and it's redundant once the version
# it let in has cleared the cooldown: a copy of the project without it locks
# the same version. The repo's own pyproject.toml and uv.lock are never
# changed.

set -euo pipefail

if [[ $# != 0 ]]; then
    echo "usage: $(basename "$0")" >&2
    exit 1
fi

# The tools this script runs are installed next to it, in .venv/bin.
PATH="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd):${PATH}"
toplevel="$(git rev-parse --show-toplevel)"
cd "${toplevel}"

tmp="$(mktemp -d)"
trap 'rm -rf "${tmp}"' EXIT

# A file, not a pipe, so set -e stops the script if python fails.
python -I -m jetstream.prune exclude-newer-packages pyproject.toml > "${tmp}/entries"
packages=()
while IFS= read -r package; do
    packages+=("${package}")
done < "${tmp}/entries"

if [[ ${#packages[@]} -eq 0 ]]; then
    echo "prune: no [tool.uv] exclude-newer-package overrides to check"
    exit 0
fi

copy="${tmp}/project"
fresh_copy() {
    rm -rf "${copy}"
    mkdir "${copy}"
    cp pyproject.toml uv.lock "${copy}/"
}

# The copy must lock as it is, or every trial would fail for another reason.
fresh_copy
if ! uv lock --quiet --locked --directory "${copy}" 2> "${tmp}/log"; then
    cat "${tmp}/log" >&2
    echo "prune: a copy of pyproject.toml and uv.lock doesn't lock as it is, so nothing was checked" >&2
    exit 2
fi

redundant=0
for package in "${packages[@]}"; do
    fresh_copy
    locked="$(python -I -m jetstream.prune locked-version uv.lock "${package}")"
    python -I -m jetstream.prune remove-exclude-newer-package "${copy}/pyproject.toml" "${package}"
    if uv lock --quiet --directory "${copy}" 2> "${tmp}/log"; then
        without="$(python -I -m jetstream.prune locked-version "${copy}/uv.lock" "${package}")"
        if [[ "${without}" == "${locked}" ]]; then
            echo "prune: ${package}: redundant, so remove it (${locked:-it} locks without it)"
            redundant=1
        else
            echo "prune: ${package}: still needed (without it, ${without:-none} locks instead of ${locked})"
        fi
    elif grep -q "No solution found" "${tmp}/log"; then
        echo "prune: ${package}: still needed (without it, nothing locks)"
    else
        cat "${tmp}/log" >&2
        echo "prune: ${package}: couldn't check it" >&2
        exit 2
    fi
done
exit "${redundant}"
