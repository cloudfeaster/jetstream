# Licensing

Cloudfeaster code may be open-sourced or sold, so nothing Cloudfeaster distributes may carry a license that stops either. What decides it is whether third-party software ends up in something Cloudfeaster distributes, not whether Cloudfeaster uses it.

## Product dependencies

Third-party software that's part of a product (linked with it, embedded in it, or distributed with it), whether a direct or a transitive dependency:

- **Allowed**: MIT, Apache-2.0 and the BSD licenses.
- **Allowed for a transitive dependency only**: MPL-2.0. It's weak copyleft that only covers changes to that package's own files, not the code that uses it.
- **Not allowed**: GPL, LGPL and AGPL, in any version, and any license not listed here.

A component bundled inside a package counts under its own license, not the package's. For example, `shellcheck-py` is MIT, but the ShellCheck binary in its wheels is GPL-3.0. So check what a package contains, not just the license in its metadata.

## Development tools

A tool used only to develop, test, lint, scan or build, locally or in CI, may have any open-source license, GPL, LGPL and AGPL included, when:

- it runs as a separate program, and isn't linked with or copied into the product;
- nothing Cloudfeaster distributes includes it;
- Cloudfeaster doesn't redistribute it: it comes from its own publisher, such as a package index or the project's own releases.

Running such a tool on a repo's code doesn't change that code's license. An AGPL tool that serves anything over a network needs a review before it's used.

jetstream's tools are development tools in this sense, because jetstream installs them without distributing them: see [How jetstream is distributed](https://github.com/cloudfeaster/jetstream#how-jetstream-is-distributed).

## Publishing

Publishing anything that contains a third-party tool, such as a built wheel, a release archive or a container image, makes Cloudfeaster that tool's distributor. So it needs a licensing review first, whatever the tool's license.

## Exceptions

A dependency that needs an exception is a decision for jetstream, not for one repo, because the allowed licenses are set in the configuration jetstream owns.

## Third-party data

A data file from a published dataset is never committed, whatever its license. A script builds it, it's gitignored, and code that needs it fails with a message saying how to build it. Tests use a small stand-in instead. The dataset's credit goes in the README next to the code that uses it.

## Copyright

Copyright is stated once, in the repo's `LICENSE`. Files don't have copyright headers.
