#!/usr/bin/env bash
#
# Set up jetstream's own development environment:
#
#   source cfg4dev.sh
#
# uv installs jetstream from this working tree (editable), and the build hook
# runs for that too, so jetstream develops against itself: its tools land in
# .venv/bin, and its git hooks call them. jetstream sync and cfg4dev.local.sh
# join this as they're built.

pushd "$(git rev-parse --show-toplevel)" > /dev/null || return 1

uv self update || true

if uv sync; then
    if [ -z "${VIRTUAL_ENV}" ]; then
        # shellcheck disable=SC1091
        source ./.venv/bin/activate
    fi
    # the pre-commit and commit-msg hooks (default_install_hook_types)
    pre-commit install
fi

popd > /dev/null || return 1
