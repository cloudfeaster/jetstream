#!/usr/bin/env bash
#
# Run the repo's tests with pytest, leaving out those marked integration.
# A repo's own checks are tests, so this is how a repo adds checks. It passes
# when the repo has no tests.

set -euo pipefail

if [[ $# != 0 ]]; then
    echo "usage: $(basename "$0")" >&2
    exit 1
fi

# The tools this script runs are installed next to it, in .venv/bin.
PATH="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd):${PATH}"
toplevel="$(git rev-parse --show-toplevel)"
cd "${toplevel}"

# pytest's exit status when it collects no tests
NO_TESTS_COLLECTED=5

status=0
pytest -m "not integration" || status=$?
if [[ "${status}" -eq "${NO_TESTS_COLLECTED}" ]]; then
    exit 0
fi
exit "${status}"
