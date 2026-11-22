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
    # activate this repo's .venv, even when another repo's is active, or
    # jetstream sync and the git hook would use that repo's tools (activate
    # deactivates the other one first)
    if [[ "${VIRTUAL_ENV:-}" != "${PWD}/.venv" ]]; then
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

    # the website pack: Node is installed by hand, so say when it isn't the
    # major version .nvmrc names, which is the one CI uses
    if [[ -f .nvmrc ]]; then
        _jetstream_node="$(node --version 2> /dev/null || true)"
        _jetstream_node="${_jetstream_node#v}"
        if [[ "${_jetstream_node%%.*}" != "$(< .nvmrc)" ]]; then
            echo "*** cfg4dev.sh: .nvmrc says Node $(< .nvmrc), but node is ${_jetstream_node:-not installed}: install Node $(< .nvmrc) (with nvm, nvm install)" >&2
        fi
        unset _jetstream_node
    fi

    # the site's npm packages, when package-lock.json is newer than what's
    # installed (npm ci writes node_modules/.package-lock.json)
    if [[ -f .nvmrc && -f package-lock.json ]]; then
        if [[ ! package-lock.json -ot node_modules/.package-lock.json ]]; then
            npm ci
        fi
    fi

    # the pre-commit hook
    pre-commit install

    if [[ -f cfg4dev.local.sh ]]; then
        # shellcheck disable=SC1091
        source ./cfg4dev.local.sh
    fi
fi

popd > /dev/null || return 1
