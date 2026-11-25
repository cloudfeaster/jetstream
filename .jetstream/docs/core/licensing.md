<!-- Written by `jetstream sync` from cloudfeaster/jetstream's docs; don't edit. -->

# Licensing

Cloudfeaster code may be open-sourced or sold, so nothing Cloudfeaster distributes may carry a license that stops either. What decides it is whether third-party software ends up in something Cloudfeaster distributes, not whether Cloudfeaster uses it.

## Product dependencies

Third-party software that's part of a product (linked with it, embedded in it, or distributed with it), whether a direct or a transitive dependency:

- **Allowed**: MIT, Apache-2.0, BSD-2-Clause, BSD-3-Clause, ISC and 0BSD.
- **Allowed for a transitive dependency only**: MPL-2.0. It's weak copyleft that only covers changes to that package's own files, not the code that uses it.
- **Not allowed**: GPL, LGPL and AGPL, in any version, and any license not listed here.

Two permissive licenses are left out on purpose. CC0-1.0, a public-domain dedication, grants no patent rights, so it isn't allowed for code that ships. BlueOak-1.0.0 isn't allowed until a package that needs it has been reviewed. A package offered under either or an allowed license, such as `(MIT OR CC0-1.0)`, is fine.

A component bundled inside a package counts under its own license, not the package's. For example, `shellcheck-py` is MIT, but the ShellCheck binary in its wheels is GPL-3.0. So check what a package contains, not just the license in its metadata.

## Development tools

A tool used only to develop, test, lint, scan or build, locally or in CI, may have any open-source license, GPL, LGPL and AGPL included, when:

- it runs as a separate program, and isn't linked with or copied into the product;
- nothing Cloudfeaster distributes includes it;
- Cloudfeaster doesn't redistribute it: it comes from its own publisher, such as a package index or the project's own releases.

Running such a tool on a repo's code doesn't change that code's license. An AGPL tool that serves anything over a network needs a review before it's used.

jetstream's tools are development tools in this sense, because jetstream installs them without distributing them: see [How jetstream is distributed](https://github.com/cloudfeaster/jetstream#how-jetstream-is-distributed). jetstream's own tests check that every tool it installs, and anything bundled inside one, has a license this section allows, so a repo doesn't check them.

## Publishing

Publishing anything that contains a third-party tool, such as a built wheel, a release archive or a container image, makes Cloudfeaster that tool's distributor. So it needs a licensing review first, whatever the tool's license.

## Exceptions

A dependency that needs an exception is a decision for jetstream, not for one repo, because the allowed licenses are set in the configuration jetstream owns.

## Third-party data

A data file from a published dataset is never committed, whatever its license. A script builds it, it's gitignored, and code that needs it fails with a message saying how to build it. Tests use a small stand-in instead. The dataset's credit goes in the README next to the code that uses it.

## The repo's own licenses

Most repos have one license, for their code, in `LICENSE`. A repo whose own written content or brand assets need other terms, such as a website, can have up to three, each in a file of its own:

| File | Covers | Example |
|---|---|---|
| `LICENSE` | the code: every file that neither of the others covers | MIT, or a proprietary license for a repo that's sold |
| `LICENSE-docs` | written content: the Markdown and MDX in the repo's content folders, such as a site's `src/content/` | CC BY 4.0 |
| `TRADEMARKS.md` | brand assets: the name, logo and icons, by path, which neither license covers | all rights reserved, with how the name may be used |

The repo chooses the licenses; the file names are fixed, so anyone can find them in any repo. Which file covers a file depends only on its path, never on what's in it, so a `.astro` page, or any other file of code, is code, its text included. Prose that should be under the content license goes in a Markdown or MDX file in a content folder; any other file there, such as a `.json` one, is code, unless `TRADEMARKS.md` lists it.

A repo with more than one has a "License" section in its `README.md`, listing each file and what it covers.

## Copyright

Copyright is stated in each of the repo's license files (`LICENSE`, and `LICENSE-docs` and `TRADEMARKS.md` if it has them), and in its README's "License" section if it has one. Files don't have copyright headers.
