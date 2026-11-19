#!/usr/bin/env bash
#
# Audit every package in uv.lock (every group and extra, so jetstream's tools
# too) for known vulnerabilities with pip-audit. Exceptions come from
# jetstream's .jetstream/pip-audit-ignore and the repo's .pip-audit-ignore:
# one ID per line, with an optional exp:YYYY-MM-DD after which it no longer
# applies, as in .trivyignore.

set -euo pipefail

if [[ $# != 0 ]]; then
    echo "usage: $(basename "$0")" >&2
    exit 1
fi

# The tools this script runs are installed next to it, in .venv/bin.
PATH="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd):${PATH}"
toplevel="$(git rev-parse --show-toplevel)"
cd "${toplevel}"

today="$(date -u +%F)"
ignores=()
for exceptions in .jetstream/pip-audit-ignore .pip-audit-ignore; do
    if [[ ! -f "${exceptions}" ]]; then
        continue
    fi
    while read -r id expires _ || [[ -n "${id}" ]]; do
        if [[ -z "${id}" || "${id}" == \#* ]]; then
            continue
        fi
        if [[ "${expires}" =~ ^exp:([0-9]{4}-[0-9]{2}-[0-9]{2})$ ]]; then
            if [[ ! "${today}" < "${BASH_REMATCH[1]}" ]]; then
                continue  # expired
            fi
        elif [[ -n "${expires}" && "${expires}" != \#* ]]; then
            echo "${exceptions}: '${id} ${expires}': expected exp:YYYY-MM-DD after the ID" >&2
            exit 1
        fi
        ignores+=(--ignore-vuln "${id}")
    done < "${exceptions}"
done

# jetstream isn't on PyPI, so it has no advisories to look up.
tmp="$(mktemp -d)"
trap 'rm -rf "${tmp}"' EXIT
requirements="${tmp}/requirements.txt"
uv export --quiet --frozen --all-groups --all-extras --no-emit-project --no-emit-package cloudfeaster-jetstream > "${requirements}"

pip-audit --requirement "${requirements}" --disable-pip --progress-spinner off ${ignores[@]+"${ignores[@]}"}
