#!/usr/bin/env bash
#
# pre-commit hook: run mado (https://github.com/akiomik/mado) on the Markdown
# files pre-commit passes in, installing the pinned release on first use.
#
# mado reads its config from mado.toml in the current directory, which
# pre-commit sets to the root of the repo being checked. The
# mado-config-up-to-date hook generates mado.toml from .markdownlint.json.
#

set -o errexit
set -o nounset
set -o pipefail

MADO="$("$(dirname "${BASH_SOURCE[0]}")/install-mado.sh")"

# mado lints stdin instead of the given files if stdin has data, and hangs if
# stdin is an open pipe that never closes, so give it an empty stdin.
exec "${MADO}" check "$@" < /dev/null
