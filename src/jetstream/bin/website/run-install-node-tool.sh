#!/usr/bin/env bash
#
# Install one of jetstream's Node tools, if it isn't already, and print the
# folder it's in: .venv/jetstream-<tool>. Its package.json and
# package-lock.json ship in jetstream (node/<tool>/), and the first run, or
# the first after a jetstream release changes them, installs it with npm ci.
# run-astro-check.sh and run-lighthouse.sh use it.

set -euo pipefail

if [[ $# != 2 ]]; then
    echo "usage: $(basename "$0") <tool> <command>" >&2
    exit 1
fi
tool="$1"
command="$2"  # the tool's command, in its node_modules/.bin

if ! command -v node > /dev/null; then
    echo "*** $(basename "$0"): node isn't installed: install Node, at the major version in .nvmrc" >&2
    exit 1
fi

# This script is installed in .venv/bin, next to jetstream's Python.
bin_dir="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
package="$("${bin_dir}/python" -c 'import importlib.resources, sys; print(importlib.resources.files("jetstream") / "node" / sys.argv[1])' "${tool}")"
tools="$(dirname "${bin_dir}")/jetstream-${tool}"

# The lockfile is copied to installed.json only once npm ci has finished, so an
# install that fails part way, or one whose command has gone, is redone on the
# next run.
if ! cmp -s "${package}/package-lock.json" "${tools}/installed.json" || [[ ! -x "${tools}/node_modules/.bin/${command}" ]]; then
    if ! command -v npm > /dev/null; then
        echo "*** $(basename "$0"): npm, which comes with Node, isn't installed: install Node, at the major version in .nvmrc" >&2
        exit 1
    fi
    rm -rf "${tools}"
    cp -R "${package}" "${tools}"
    # No package in the lockfiles has an install script, so none is run.
    npm ci --prefix "${tools}" --ignore-scripts --no-audit --no-fund --loglevel=error >&2
    cp "${package}/package-lock.json" "${tools}/installed.json"
fi

echo "${tools}"
