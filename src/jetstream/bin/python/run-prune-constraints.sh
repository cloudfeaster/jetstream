#!/usr/bin/env bash
#
# Report each [tool.uv] constraint-dependencies entry that no longer changes
# what uv locks, and fail if there's one, so it's removed. A constraint is a
# floor, "foo>=1.2.3", and it's redundant once nothing the dependencies allow
# is older: a copy of the project with "foo<1.2.3" in its place can't lock.
# The repo's own pyproject.toml and uv.lock are never changed.

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
python -I -m jetstream.prune constraints pyproject.toml > "${tmp}/entries"
constraints=()
while IFS= read -r constraint; do
    constraints+=("${constraint}")
done < "${tmp}/entries"

if [[ ${#constraints[@]} -eq 0 ]]; then
    echo "prune: no [tool.uv] constraint-dependencies to check"
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
for i in "${!constraints[@]}"; do
    fresh_copy
    inverse="$(python -I -m jetstream.prune invert-constraint "${copy}/pyproject.toml" "${i}")"
    if uv lock --quiet --directory "${copy}" 2> "${tmp}/log"; then
        echo "prune: ${constraints[i]}: still needed (${inverse} locks)"
    elif grep -q "No solution found" "${tmp}/log"; then
        echo "prune: ${constraints[i]}: redundant, so remove it (nothing the dependencies allow is older)"
        redundant=1
    else
        cat "${tmp}/log" >&2
        echo "prune: ${constraints[i]}: couldn't check it" >&2
        exit 2
    fi
done
exit "${redundant}"
