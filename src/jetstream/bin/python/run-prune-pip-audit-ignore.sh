#!/usr/bin/env bash
#
# Report each pip-audit exception that no longer matches a finding, and fail
# if there's one, so it's removed rather than waiting for its exp: date.
# pip-audit audits uv.lock once with no exceptions, as run-pip-audit.sh does;
# an unexpired entry in .pip-audit-ignore whose ID isn't among the findings'
# IDs and aliases is redundant. In jetstream itself,
# .jetstream/pip-audit-ignore is checked too; in any other repo it's
# jetstream's, so it's left out.

set -euo pipefail

if [[ $# != 0 ]]; then
    echo "usage: $(basename "$0")" >&2
    exit 1
fi

# The tools this script runs are installed next to it, in .venv/bin.
PATH="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd):${PATH}"
toplevel="$(git rev-parse --show-toplevel)"
cd "${toplevel}"

files=(.pip-audit-ignore)
if grep -qx 'name = "cloudfeaster-jetstream"' pyproject.toml; then
    files=(.jetstream/pip-audit-ignore .pip-audit-ignore)
fi

today="$(date -u +%F)"
entries=()
for exceptions in "${files[@]}"; do
    if [[ ! -f "${exceptions}" ]]; then
        continue
    fi
    while read -r id expires _ || [[ -n "${id}" ]]; do
        if [[ -z "${id}" || "${id}" == \#* ]]; then
            continue
        fi
        if [[ "${expires}" =~ ^exp:([0-9]{4}-[0-9]{2}-[0-9]{2})$ && ! "${today}" < "${BASH_REMATCH[1]}" ]]; then
            continue  # expired, so run-pip-audit.sh already ignores it
        fi
        entries+=("${exceptions} ${id}")
    done < "${exceptions}"
done

if [[ ${#entries[@]} -eq 0 ]]; then
    echo "prune: no pip-audit exceptions to check"
    exit 0
fi

tmp="$(mktemp -d)"
trap 'rm -rf "${tmp}"' EXIT
uv export --quiet --frozen --all-groups --all-extras --no-emit-project --no-emit-package cloudfeaster-jetstream > "${tmp}/requirements.txt"
# pip-audit exits 1 when it finds something, so only a missing report is a failure.
pip-audit --requirement "${tmp}/requirements.txt" --disable-pip --progress-spinner off --format json --output "${tmp}/report.json" || true
if [[ ! -s "${tmp}/report.json" ]]; then
    echo "prune: pip-audit didn't write a report, so nothing was checked" >&2
    exit 2
fi
jq -r '.dependencies[].vulns[]? | .id, .aliases[]' "${tmp}/report.json" > "${tmp}/found"

redundant=0
for entry in "${entries[@]}"; do
    id="${entry#* }"
    if grep -qxF "${id}" "${tmp}/found"; then
        echo "prune: ${entry%% *}: ${id}: still needed"
    else
        echo "prune: ${entry%% *}: ${id}: redundant, so remove it (pip-audit no longer finds it)"
        redundant=1
    fi
done
exit "${redundant}"
