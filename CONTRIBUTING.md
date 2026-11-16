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

jetstream uses the [Developer Certificate of Origin](https://developercertificate.org/) instead of a contributor license agreement. By adding a `Signed-off-by` line to a commit, you certify that you wrote the change or otherwise have the right to submit it under jetstream's [MIT license](LICENSE).

Add the line with `git commit -s`:

```text
Signed-off-by: Your Name <you@example.com>
```

The name and email must match the commit's author. A pull request with an unsigned-off commit can't be merged. To fix the last commit, run `git commit --amend -s`. For older commits, run `git rebase --signoff main`.

The full DCO text:

```text
Developer Certificate of Origin
Version 1.1

Copyright (C) 2004, 2006 The Linux Foundation and its contributors.

Everyone is permitted to copy and distribute verbatim copies of this
license document, but changing it is not allowed.


Developer's Certificate of Origin 1.1

By making a contribution to this project, I certify that:

(a) The contribution was created in whole or in part by me and I
    have the right to submit it under the open source license
    indicated in the file; or

(b) The contribution is based upon previous work that, to the best
    of my knowledge, is covered under an appropriate open source
    license and I have the right under that license to submit that
    work with modifications, whether created in whole or in part
    by me, under the same open source license (unless I am
    permitted to submit under a different license), as indicated
    in the file; or

(c) The contribution was provided directly to me by some other
    person who certified (a), (b) or (c) and I have not modified
    it.

(d) I understand and agree that this project and the contribution
    are public and that a record of the contribution (including all
    personal information I submit with it, including my sign-off) is
    maintained indefinitely and may be redistributed consistent with
    this project or the open source license(s) involved.
```
