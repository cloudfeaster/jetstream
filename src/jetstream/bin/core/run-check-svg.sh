#!/usr/bin/env bash
#
# Fail if a committed SVG diagram isn't what its D2 source compiles to. Every
# <dir>/images/<name>.svg needs a source at <dir>/images/d2/<name>.d2;
# regenerate them with run-d2-compile.sh. SVGs elsewhere aren't checked.

set -euo pipefail

if [[ $# != 0 ]]; then
    echo "usage: $(basename "$0")" >&2
    exit 1
fi

# The tools this script runs are installed next to it, in .venv/bin.
PATH="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd):${PATH}"
toplevel="$(git rev-parse --show-toplevel)"
cd "${toplevel}"

# Compare SVGs as canonical XML (C14N 2.0), so formatting differences don't count.
canonical() {
    python3 -c 'import sys, xml.etree.ElementTree as ET; sys.stdout.write(ET.canonicalize(from_file=sys.argv[1]))' "$1"
}

work_dir="$(mktemp -d)"
trap 'rm -rf "${work_dir}"' EXIT

git ls-files -z -- '*.svg' > "${work_dir}/svg-files"

missing=0
stale=0
while IFS= read -r -d '' svg_file; do
    images_dir="$(dirname "${svg_file}")"
    if [[ "$(basename "${images_dir}")" != images ]]; then
        continue
    fi
    d2_file="${images_dir}/d2/$(basename "${svg_file%.svg}").d2"
    if [[ ! -f "${d2_file}" ]]; then
        echo "Missing source: ${svg_file} has no D2 source at ${d2_file}" >&2
        missing=$((missing + 1))
        continue
    fi
    if ! output="$(d2 --sketch "${d2_file}" "${work_dir}/generated.svg" 2>&1)"; then
        echo "${output}" >&2
        exit 1
    fi
    committed="$(canonical "${svg_file}")"
    generated="$(canonical "${work_dir}/generated.svg")"
    if [[ "${committed}" != "${generated}" ]]; then
        echo "Stale SVG: ${svg_file} doesn't match what ${d2_file} compiles to; run run-d2-compile.sh" >&2
        stale=$((stale + 1))
    fi
done < "${work_dir}/svg-files"

if [[ "${missing}" -gt 0 ]] || [[ "${stale}" -gt 0 ]]; then
    echo "SVG check failed: ${missing} missing source(s), ${stale} stale SVG(s)" >&2
    exit 1
fi
