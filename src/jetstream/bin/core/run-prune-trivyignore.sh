#!/usr/bin/env bash
#
# Report each trivy exception that no longer matches a finding, and fail if
# there's one, so it's removed rather than waiting for its exp: date. trivy
# scans once with no exceptions; an unexpired entry in .trivyignore whose ID
# isn't among the findings' IDs (VulnerabilityID or VendorIDs) is redundant.
# In jetstream itself, .jetstream/trivyignore is checked too; in any other
# repo it's jetstream's, so it's left out.

set -euo pipefail

if [[ $# != 0 ]]; then
    echo "usage: $(basename "$0")" >&2
    exit 1
fi

# The tools this script runs are installed next to it, in .venv/bin.
PATH="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd):${PATH}"
toplevel="$(git rev-parse --show-toplevel)"
cd "${toplevel}"

files=(.trivyignore)
if [[ -f pyproject.toml ]] && grep -qx 'name = "cloudfeaster-jetstream"' pyproject.toml; then
    files=(.jetstream/trivyignore .trivyignore)
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
            continue  # expired, so trivy already ignores it
        fi
        entries+=("${exceptions} ${id}")
    done < "${exceptions}"
done

if [[ ${#entries[@]} -eq 0 ]]; then
    echo "prune: no trivy exceptions to check"
    exit 0
fi

tmp="$(mktemp -d)"
trap 'rm -rf "${tmp}"' EXIT
# --exit-code 0, so a finding isn't a failure, and an empty ignore file, so
# every finding is reported.
trivy fs --quiet --config .trivy.yaml --ignorefile /dev/null --exit-code 0 --format json --output "${tmp}/report.json" .
jq -r '.Results[]?.Vulnerabilities[]? | .VulnerabilityID, (.VendorIDs // [])[]' "${tmp}/report.json" > "${tmp}/found"

redundant=0
for entry in "${entries[@]}"; do
    id="${entry#* }"
    if grep -qxF "${id}" "${tmp}/found"; then
        echo "prune: ${entry%% *}: ${id}: still needed"
    else
        echo "prune: ${entry%% *}: ${id}: redundant, so remove it (trivy no longer finds it)"
        redundant=1
    fi
done
exit "${redundant}"
