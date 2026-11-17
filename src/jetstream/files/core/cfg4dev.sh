#!/usr/bin/env bash
#
# Set up this repo's development environment:
#
#   source cfg4dev.sh
#
# Written by `jetstream sync` (core pack). Put the repo's own setup in
# cfg4dev.local.sh, which this sources last.
#
# uv sync installs jetstream and every tool it pins into .venv, jetstream sync
# writes jetstream's files into the repo, and pre-commit install sets up the
# git hooks, which call the tools in .venv/bin.

_jetstream_toplevel="$(git rev-parse --show-toplevel)" || return 1
pushd "${_jetstream_toplevel}" > /dev/null || return 1
unset _jetstream_toplevel

uv self update || true

if uv sync; then
    if [[ -z "${VIRTUAL_ENV:-}" ]]; then
        # shellcheck disable=SC1091
        source ./.venv/bin/activate
    fi

    # jetstream sync can change pyproject.toml (jetstream's keys), and then
    # .venv has to catch up.
    _jetstream_pyproject="$(cksum < pyproject.toml)"
    jetstream sync
    _jetstream_pyproject_synced="$(cksum < pyproject.toml)"
    if [[ "${_jetstream_pyproject_synced}" != "${_jetstream_pyproject}" ]]; then
        uv sync
    fi
    unset _jetstream_pyproject _jetstream_pyproject_synced

    # the pre-commit and commit-msg hooks (default_install_hook_types)
    pre-commit install

    if [[ -f cfg4dev.local.sh ]]; then
        # shellcheck disable=SC1091
        source ./cfg4dev.local.sh
    fi
fi

popd > /dev/null || return 1
