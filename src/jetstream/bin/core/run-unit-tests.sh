#!/usr/bin/env bash
#
# Run the repo's tests with pytest, leaving out those marked integration.
# A repo's own checks are tests, so this is how a repo adds checks. It passes
# when the repo has no tests.
#
# When coverage is installed (the python pack installs it), the tests run
# under coverage, and coverage report then fails below the repo's
# [tool.coverage.report] fail_under.

set -euo pipefail

if [[ $# != 0 ]]; then
    echo "usage: $(basename "$0")" >&2
    exit 1
fi

# The tools this script runs are installed next to it, in .venv/bin.
here="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PATH="${here}:${PATH}"
toplevel="$(git rev-parse --show-toplevel)"
cd "${toplevel}"

# pytest's exit status when it collects no tests
NO_TESTS_COLLECTED=5

pytest=(pytest)
if [[ -x "${here}/coverage" ]]; then
    pytest=(coverage run -m pytest)
fi

status=0
"${pytest[@]}" -m "not integration" || status=$?
if [[ "${status}" -eq "${NO_TESTS_COLLECTED}" ]]; then
    exit 0
fi
if [[ "${status}" -ne 0 || "${pytest[0]}" != coverage ]]; then
    exit "${status}"
fi
coverage report
