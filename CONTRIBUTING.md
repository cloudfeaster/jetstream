# Contributing to jetstream

Thanks for helping. jetstream is installed by every Cloudfeaster repo, so changes are reviewed with that in mind.

## Before you start

- **Keep it generic.** jetstream is public. Don't add secrets, client names, internal hostnames or anything specific to one project.
- **Open an issue first** for anything bigger than a small fix, so the approach can be agreed before you write code.

## Development environment

You need [uv](https://docs.astral.sh/uv/). Then:

```bash
source cfg4dev.sh
pytest
```

`cfg4dev.sh` installs jetstream from your working tree into `.venv`, so you develop against your own changes.

`cfg4dev.sh` and the checks are described in [dev-environment.md](.jetstream/docs/core/dev-environment.md).

## Making a change

Follow [dev-workflow.md](.jetstream/docs/core/dev-workflow.md): branch, commit signed and signed off, open a draft pull request, and squash-merge once `jetstream lint` passes. Commit messages are [Conventional Commits](https://www.conventionalcommits.org/) (`feat: ...`, `fix: ...`, `docs: ...`); releases and `CHANGELOG.md` will be generated from them.

## Conventions

jetstream follows the conventions it ships, in [`.jetstream/docs/core/`](.jetstream/docs/core/): [GitHub Actions](.jetstream/docs/core/github-actions.md), [Markdown](.jetstream/docs/core/markdown.md), [JSON](.jetstream/docs/core/json.md), [diagrams](.jetstream/docs/core/diagrams.md) and [licensing](.jetstream/docs/core/licensing.md). `jetstream sync` writes those files from `src/jetstream/docs/`, so edit them there.

## Developer Certificate of Origin (DCO)

jetstream uses the [Developer Certificate of Origin](https://developercertificate.org/) instead of a contributor license agreement. By adding a `Signed-off-by` line to a commit (`git commit -s`), you certify that you wrote the change or otherwise have the right to submit it under jetstream's [MIT license](LICENSE). [`.jetstream/docs/core/dco.md`](.jetstream/docs/core/dco.md) explains how to sign off, how to fix a commit that isn't signed off, and has the full DCO text.
