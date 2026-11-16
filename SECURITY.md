# Security Policy

jetstream installs and configures the security tooling of every Cloudfeaster repo, so a vulnerability in jetstream can reach all of them. Reports are very welcome.

## Reporting a Vulnerability

**Please don't report security vulnerabilities in public issues, pull requests or discussions.**

Report it privately instead:

1. Go to this repository's **Security** tab.
1. Click **Report a vulnerability**.
1. Describe the problem: what's affected (file, release tag or commit), how to reproduce it, and what an attacker could do with it.

If **Report a vulnerability** isn't shown, email [security@cloudfeaster.com](mailto:security@cloudfeaster.com) instead of opening an issue.

## What's in scope

- The `jetstream` command and the build hook that downloads and verifies bundled tools.
- The files, tool configuration and CI workflows jetstream writes into other repos.
- jetstream's own release process: tags, pins and checksums.

A vulnerability in a bundled third-party tool belongs with that tool's maintainers. Please tell us too if a jetstream release should move to a fixed version.

## Supported versions

Only the latest release gets fixes. Repos pick up a fix by bumping their jetstream pin.
