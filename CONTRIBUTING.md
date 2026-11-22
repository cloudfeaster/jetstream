# Contributing to jetstream

Thanks for helping. jetstream is installed by every Cloudfeaster repo, so changes are reviewed with that in mind.

## Before you start

- **Keep it generic.** jetstream is public. Don't add secrets, client names, internal hostnames or anything specific to one project.
- **Open an issue first** for anything bigger than a small fix, so the approach can be agreed before you write code.

## Development environment

You need [uv](https://docs.astral.sh/uv/), and [Node](https://nodejs.org/) for the website pack's tests, at the major version in `.nvmrc`. That's the website pack's `.nvmrc` (a symlink to `src/jetstream/files/website/.nvmrc`), so jetstream's tests and CI use the Node the sites do. Then:

```bash
source cfg4dev.sh
pytest
```

`cfg4dev.sh` installs jetstream from your working tree into `.venv`, so you develop against your own changes.

`cfg4dev.sh` and the checks are described in [dev-environment.md](.jetstream/docs/core/dev-environment.md).

## Making a change

Follow [dev-workflow.md](.jetstream/docs/core/dev-workflow.md): branch, commit signed, open a draft pull request, and squash-merge once `jetstream lint` passes. Commit messages are [Conventional Commits](https://www.conventionalcommits.org/) (`feat: ...`, `fix: ...`, `docs: ...`); releases and `CHANGELOG.md` are generated from them (see [Releasing](#releasing)).

## Keeping the binary tools current

Dependabot keeps jetstream's Python dependencies and actions current, but it can't see the binary tools pinned in `binaries.toml`. The `binary pins` workflow checks them every night with `bin/update-binary.py --check --verbose`, which reports every pin (its version, the latest release and whether that is still in the cooldown) and fails when a pin is behind a release that's at least 7 days old. To bump one:

```bash
bin/update-binary.py <tool>             # its latest release past the cooldown
bin/update-binary.py <tool> <version>   # a named version, even inside the cooldown
```

It updates the version and every platform's SHA-256 in `binaries.toml`, after checking GitHub's digests against the checksums file the project publishes. Commit it as a `fix:`, so the bump is released.

## Keeping the uv floor current

Every repo gets its uv floor from core's `[tool.uv] required-version` (`src/jetstream/parts/core/pyproject.toml`). It's a floor (`>=`), not a pin: uv refuses to run below it, locally and in CI (`astral-sh/setup-uv` reads it), and `cfg4dev.sh`'s `uv self update` keeps everyone above it without anyone bumping a pin.

It has a ceiling too. Dependabot runs `uv lock` with the uv in [dependabot-core's uv Dockerfile](https://github.com/dependabot/dependabot-core/blob/main/uv/Dockerfile), so a floor above that uv makes every Dependabot uv update fail. The `uv floor` workflow checks every night with `bin/check-uv-floor.py --verbose`, and fails when the floor:

- is above Dependabot's uv: lower it to Dependabot's uv;
- is a minor version or more behind Dependabot's uv (0.13.x when Dependabot is on 0.14.y): raise it to Dependabot's uv. Within a minor version it can lag, so a floor bump, which every repo takes in a release, comes a few times a year rather than with every uv release.

To change it, edit `required-version` in core's part, run `jetstream sync` (jetstream's own `pyproject.toml` has the same key) and `uv lock`, and commit it as a `fix:`, so it's released.

## Licenses of the tools jetstream installs

Every tool jetstream installs is a development tool, so it may have any open-source license except that an AGPL one needs a review first ([licensing.md](src/jetstream/docs/core/licensing.md#development-tools)). `tests/test_dev_tool_licenses.py` checks:

- **every Python package** that a pack's extra installs, with its dependencies, using the license licensecheck reads from its installed metadata;
- **every binary** in `binaries.toml`, by its `license`. The `binary pins` workflow's `bin/update-binary.py --check` fails if GitHub reports a different license for the tool's repo;
- **what's bundled inside a package**, under a license of its own, which no metadata shows. It's recorded by hand in `dev-tool-licenses.toml`'s `[bundled]`, such as the GPL ShellCheck binary in `shellcheck-py`'s wheels.

When you add a tool, check what its wheels contain and record anything bundled. A license the test can't recognise, a missing one, or an AGPL one fails until someone reviews it and records it in `[reviewed]`, with a comment saying why it's allowed.

## Releasing

Releases are cut by [release-please](https://github.com/googleapis/release-please), from the Conventional Commits on `main`:

1. Every push to `main` runs the `release-please` workflow. It opens, or updates, a release PR from the `release-please--branches--main--components--cloudfeaster-jetstream` branch. The PR sets the next version in `pyproject.toml` and `uv.lock`, and adds the commits since the last release to `CHANGELOG.md`.
1. Merge the release PR like any other, once `jetstream lint` passes. The workflow then tags the merge commit `vX.Y.Z` and creates the GitHub Release.

The commits decide the version. Before 1.0.0, a breaking change (`feat!:`) or a `feat:` bumps the minor version, and a `fix:` bumps the patch version. From 1.0.0 on, a breaking change bumps the major version. A change is breaking if a repo must change something it owns to take the release.

Two org rulesets protect the tags: only the `cloudfeaster-release` App can create a tag, and no one, the App and org owners included, can move or delete one. So a release's only source is release-please, and a tag can't be created by hand, even by an owner. If a release fails between merging the release PR and tagging, rerun the `release-please` workflow. The rulesets are set and checked nightly by `cloudfeaster/.github-private` (`docs/org-hardening.md`, section 8). They replace a `vX.Y.Z` tag name pattern, which GitHub Team doesn't enforce (decision 9 in #1).

A release is only its tag and its GitHub Release notes. Never attach a built wheel or any other file to a release, publish jetstream to a package index, or publish an image with jetstream installed, without a licensing review first. jetstream not distributing the tools it installs is what lets it include them whatever their license ([How jetstream is distributed](README.md#how-jetstream-is-distributed)). The `release-assets` workflow fails if a release ever has a file attached.

### Setting up the release App

release-please acts as a GitHub App, `cloudfeaster-release`, rather than with the workflow's `GITHUB_TOKEN`, because GitHub starts no workflows from anything `GITHUB_TOKEN` does. The release PR would then never get the `jetstream lint` check that the org ruleset requires, and could never merge. One App serves every repo that releases.

Do these as an org owner, in the browser:

1. **Create the App** at <https://github.com/organizations/cloudfeaster/settings/apps/new>:
    - GitHub App name: `cloudfeaster-release`
    - Homepage URL: `https://github.com/cloudfeaster/jetstream`. It's required but unused.
    - Webhook: untick **Active**.
    - Repository permissions (leave everything else at **No access**):
        - Contents: **Read and write**, for the release branch and its commit, tags and GitHub Releases
        - Pull requests: **Read and write**, to open and update the release PR
        - Issues: **Read and write**, for the `autorelease: pending` and `autorelease: tagged` labels release-please puts on the PR
        - Metadata: **Read-only** (required)
    - Where can this GitHub App be installed? **Only on this account**.
    - Click **Create GitHub App**.
1. **Copy the client ID and create a private key.** Note the **Client ID** (`Iv23li...`), then click **Private keys → Generate a private key**. That `.pem` file is the App's password.
1. **Install the App:** **Install App → Install** next to `cloudfeaster`, then **Only select repositories → jetstream**. Add more repos here later, as they start releasing.
1. **Create the `release` environment** in the repo: **Settings → Environments → New environment**, named `release`. Under **Deployment branches and tags**, choose **Selected branches and tags** and add `main`. Only runs from `main` can then read the key.
1. **Give the environment the client ID and key:**

    ```bash
    gh variable set RELEASE_APP_CLIENT_ID -R cloudfeaster/jetstream --env release --body 'Iv23li...'
    gh secret set RELEASE_APP_PRIVATE_KEY -R cloudfeaster/jetstream --env release < ~/Downloads/cloudfeaster-release.*.private-key.pem
    ```

    For another repo, repeat steps 4 and 5 with its name. Keep the `.pem` somewhere safe until every repo that needs it has a copy, then delete it. A new key can always be generated on the App's page.

The workflow asks for a token with only the Contents, Issues and Pull requests permissions, so it stays that narrow even if the App is given more.

## Conventions

jetstream follows the conventions it ships, in [`.jetstream/docs/core/`](.jetstream/docs/core/): [GitHub Actions](.jetstream/docs/core/github-actions.md), [Markdown](.jetstream/docs/core/markdown.md), [JSON](.jetstream/docs/core/json.md), [diagrams](.jetstream/docs/core/diagrams.md) and [licensing](.jetstream/docs/core/licensing.md). `jetstream sync` writes those files from `src/jetstream/docs/`, so edit them there.
