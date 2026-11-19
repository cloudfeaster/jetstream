#!/usr/bin/env bash
#
# Make the repo's Dependabot alerts match its scanners' exceptions
# (.jetstream/trivyignore, .trivyignore, .jetstream/pip-audit-ignore and
# .pip-audit-ignore): dismiss an alert for an accepted vulnerability, with the
# exception's comment, and reopen one whose exception was removed or expired.
# An alert dismissed by anyone else is left alone, with a warning.
#
# gh needs a token that can change Dependabot alerts, in GH_TOKEN; see
# .jetstream/docs/core/dependabot-alerts.md.

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

# Files, not pipes, so set -e stops the script if gh, jq or python fails.
gh api --paginate "repos/{owner}/{repo}/dependabot/alerts?state=open,dismissed&per_page=100" > "${tmp}/pages"
jq -s 'add // []' "${tmp}/pages" > "${tmp}/alerts.json"
python -I -m jetstream.alerts plan "${tmp}/alerts.json" > "${tmp}/changes"

if [[ ! -s "${tmp}/changes" ]]; then
    echo "sync: the Dependabot alerts already match the exceptions"
    exit 0
fi

alert() {
    gh api --silent -X PATCH "repos/{owner}/{repo}/dependabot/alerts/$1" "${@:2}"
}

while IFS=$'\t' read -r number action ghsa comment; do
    case "${action}" in
        dismiss)
            echo "sync: #${number} ${ghsa}: dismissed: ${comment}"
            alert "${number}" -f state=dismissed -f dismissed_reason=tolerable_risk -f dismissed_comment="${comment}"
            ;;
        update)
            # GitHub won't dismiss a dismissed alert again, so reopen it first.
            echo "sync: #${number} ${ghsa}: comment updated: ${comment}"
            alert "${number}" -f state=open
            alert "${number}" -f state=dismissed -f dismissed_reason=tolerable_risk -f dismissed_comment="${comment}"
            ;;
        reopen)
            echo "sync: #${number} ${ghsa}: reopened, since no exception applies any more"
            alert "${number}" -f state=open
            ;;
        leave)
            echo "sync: #${number} ${ghsa}: dismissed (${comment}) by someone other than the sync, so left alone" >&2
            ;;
        *)
            echo "sync: #${number} ${ghsa}: unknown action '${action}'" >&2
            exit 2
            ;;
    esac
done < "${tmp}/changes"
