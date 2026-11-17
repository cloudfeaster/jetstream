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

## Making a change

1. Branch from `main`. Changes reach `main` only through a pull request.
1. Write commit messages as [Conventional Commits](https://www.conventionalcommits.org/) (`feat: ...`, `fix: ...`, `docs: ...`). Releases and `CHANGELOG.md` are generated from them.
1. Sign your commits (GPG, SSH or S/MIME). `main` only accepts signed commits.
1. Sign off every commit under the DCO (next section).
1. Open a pull request and make sure CI passes.

## Developer Certificate of Origin (DCO)

jetstream uses the [Developer Certificate of Origin](https://developercertificate.org/) instead of a contributor license agreement. By adding a `Signed-off-by` line to a commit (`git commit -s`), you certify that you wrote the change or otherwise have the right to submit it under jetstream's [MIT license](LICENSE). [`.jetstream/docs/core/dco.md`](.jetstream/docs/core/dco.md) explains how to sign off, how to fix a commit that isn't signed off, and has the full DCO text.
