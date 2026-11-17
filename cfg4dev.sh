#!/usr/bin/env bash
#
# Set up jetstream's own development environment:
#
#   source cfg4dev.sh
#
# uv installs jetstream from this working tree (editable), and the build hook
# runs for that too, so jetstream develops against itself. jetstream sync,
# pre-commit install and cfg4dev.local.sh join this as they're built.

pushd "$(git rev-parse --show-toplevel)" > /dev/null || return 1

uv self update || true

if uv sync; then
    if [ -z "${VIRTUAL_ENV}" ]; then
        # shellcheck disable=SC1091
        source ./.venv/bin/activate
    fi
fi

popd > /dev/null || return 1
