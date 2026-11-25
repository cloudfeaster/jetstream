#!/usr/bin/env bash
#
# Lint the repo's Markdown with mado, using the repo's mado.toml. A page whose
# title is in its front matter, as a site's pages are, has no top level heading
# of its own, so it's linted without the rules that want one (MD002, MD041).

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
grep -v -e '"MD002"' -e '"MD041"' mado.toml > "${tmp}/mado.toml"

# the files mado finds in ".": those git doesn't ignore, outside hidden folders
git ls-files -z --cached --others --exclude-standard -- '*.md' > "${tmp}/files"
files=()
pages=()
while IFS= read -r -d '' file; do
    if [[ ! -f "${file}" || "/${file}" == */.* ]]; then
        continue
    fi
    # a page starts with front matter, between --- lines, that has a title
    title=false
    page=false
    {
        if IFS= read -r line && [[ "${line}" == --- ]]; then
            while IFS= read -r line; do
                if [[ "${line}" == --- ]]; then
                    page="${title}"
                    break
                elif [[ "${line}" == title:*[![:space:]]* ]]; then
                    title=true
                fi
            done
        fi
    } < "${file}"
    if [[ "${page}" == true ]]; then
        pages+=("${file}")
    else
        files+=("${file}")
    fi
done < "${tmp}/files"

# mado lints stdin instead of the files when stdin has data, and waits forever
# on an open pipe that never sends any, so give it nothing to read.
status=0
if [[ ${#files[@]} -gt 0 ]]; then
    mado check -- "${files[@]}" < /dev/null || status=$?
fi
if [[ ${#pages[@]} -gt 0 ]]; then
    mado --config "${tmp}/mado.toml" check -- "${pages[@]}" < /dev/null || status=$?
fi
exit "${status}"
