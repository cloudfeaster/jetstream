#!/usr/bin/env bash
#
# Written by `jetstream sync` (core pack); don't edit. VS Code's terminal
# profiles (settings.json) start bash with this as its rcfile, so every new
# terminal is set up by cfg4dev.sh.

# shellcheck source=/dev/null
[[ -f ~/.bashrc ]] && source ~/.bashrc
# shellcheck source=/dev/null
source "$(dirname "${BASH_SOURCE[0]}")/../cfg4dev.sh"
echo "dev terminal has been initialized by $(basename "${BASH_SOURCE[0]}")!"

# On macOS, hand off to zsh (Apple's default shell) so ~/.zshrc's aliases,
# prompt and plugins are available. cfg4dev.sh's exports (PATH, VIRTUAL_ENV)
# survive the exec because they're already in the environment.
if [[ "${OSTYPE}" == darwin* ]] && command -v zsh > /dev/null 2>&1; then
    exec zsh
fi
