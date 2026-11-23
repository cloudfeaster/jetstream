#!/usr/bin/env bash
#
# Check the links in the built site (dist/, from astro build) with lychee:
# links between its pages and files, #fragments, and the links in a web app
# manifest. With --external, links to other sites too; without it, lychee
# makes no network requests.
#
# Links are checked as the deployed site would resolve them. The site's
# `site` and `base`, read from its Astro config, map root-relative links
# (/<base>/...), and absolute and scheme-relative links to the site itself
# (<site>/<base>/..., //<host>/<base>/...),
# onto dist/.

set -euo pipefail

usage() {
    echo "usage: $(basename "$0") [--external]" >&2
    exit 1
}

# (an empty array is unbound under set -u before Bash 4.4, and macOS has 3.2,
# hence ${offline[@]+...} below)
offline=(--offline)
if [[ $# == 1 && $1 == --external ]]; then
    offline=()
elif [[ $# != 0 ]]; then
    usage
fi

# The tools this script runs are installed next to it, in .venv/bin.
PATH="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd):${PATH}"
toplevel="$(git rev-parse --show-toplevel)"
cd "${toplevel}"

if [[ ! -d dist ]]; then
    echo "*** $(basename "$0"): no dist/: build the site first (node_modules/.bin/astro build)" >&2
    exit 1
fi

# the site's site and base, from its Astro config
site_and_base="$(run-astro-config.sh)"
site="$(sed -n 1p <<< "${site_and_base}")"
base="$(sed -n 2p <<< "${site_and_base}")"

# lychee resolves a root-relative link under --root-dir, so dist/ goes where
# the site's base puts it.
root="$(mktemp -d)"
manifest_links="$(mktemp -d)"
trap 'rm -rf "${root}" "${manifest_links}"' EXIT
if [[ -n "${base}" ]]; then
    mkdir -p "$(dirname "${root}/${base}")"
    ln -s "${toplevel}/dist" "${root}/${base}"
else
    rmdir "${root}"
    ln -s "${toplevel}/dist" "${root}"
fi

# lychee resolves a scheme-relative link (//host/path) against the page's
# file:// URL, giving file://host/path; the deployed site would use its own
# scheme. A local file's URL has no host (file:///...), so it can't match.
# lychee applies only the first remap that matches, so the site's own links
# come first.
remap=()
if [[ -n "${site}" ]]; then
    # the site's own absolute and scheme-relative links are checked against
    # dist/, not the deployed site (site is a scheme, host and port, so . is
    # the only regex character in it)
    host="${site#*://}"
    remap+=(--remap "^${site//./\\.}/ file://${root}/")
    remap+=(--remap "^file://${host//./\\.}/ file://${root}/")
fi
scheme="${site%%://*}"
remap+=(--remap "^file://([^/]+)/ ${scheme:-https}://\$1/")

# A web app manifest is JSON, which lychee doesn't read, so its links (icons,
# start_url, ...) go on an HTML page of their own, <manifest>.html, resolved
# as a browser resolves them: against the manifest's own URL on the site.
# scope isn't one: it's a prefix of the site's URLs, not something a browser
# fetches. Node finds the manifests, and prints each page it writes.
inputs=(dist)
manifest_pages="$(node --input-type=module -e '
import { mkdirSync, readdirSync, readFileSync, writeFileSync } from "node:fs";
import { dirname, join } from "node:path";
const [site, base, root, out] = process.argv.slice(1);
const origin = site || "https://site.invalid";
const attribute = (value) => value.replaceAll("&", "&amp;").replaceAll("\"", "&quot;");
const manifests = readdirSync("dist", { recursive: true, withFileTypes: true })
    .filter((entry) => entry.isFile() && (entry.name.endsWith(".webmanifest") || entry.name === "manifest.json"))
    .map((entry) => join(entry.parentPath, entry.name));
for (const manifest of manifests) {
    const path = manifest.replace(/^dist\//, "");
    const url = new URL([base, path].filter(Boolean).join("/"), origin + "/");
    const json = JSON.parse(readFileSync(manifest, "utf8"));
    const images = (list) => (Array.isArray(list) ? list : []).map((image) => image?.src);
    const shortcuts = Array.isArray(json.shortcuts) ? json.shortcuts : [];
    const links = [json.start_url, ...images(json.icons), ...images(json.screenshots), ...shortcuts.flatMap((shortcut) => [shortcut?.url, ...images(shortcut?.icons)])]
        .filter((link) => typeof link === "string")
        .map((link) => new URL(link, url))
        .map((link) => (link.origin === origin ? "file://" + root + link.pathname + link.hash : link.href));
    const page = join(out, path + ".html");
    mkdirSync(dirname(page), { recursive: true });
    writeFileSync(page, "<html><body>" + links.map((link) => "<a href=\"" + attribute(link) + "\">" + attribute(link) + "</a>").join("") + "</body></html>");
    console.log(page);
}
' "${site}" "${base}" "${root}" "${manifest_links}")"
if [[ -n "${manifest_pages}" ]]; then
    inputs+=("${manifest_links}")
fi

lychee \
    --no-progress \
    ${offline[@]+"${offline[@]}"} \
    --include-fragments \
    --index-files index.html \
    --root-dir "${root}" \
    "${remap[@]}" \
    "${inputs[@]}"
