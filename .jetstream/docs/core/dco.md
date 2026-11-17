<!-- Written by `jetstream sync` from cloudfeaster/jetstream's docs; don't edit. -->

# Developer Certificate of Origin (DCO)

Cloudfeaster repos use the [Developer Certificate of Origin](https://developercertificate.org/) instead of a contributor license agreement. By adding a `Signed-off-by` line to a commit, you certify that you wrote the change or otherwise have the right to submit it under the repo's license.

## Signing off

Add the line with `git commit -s`:

```text
Signed-off-by: Your Name <you@example.com>
```

The name and email must match the commit's author. Two checks enforce this:

- the `dco` pre-commit hook, at `commit-msg`, checks the commit you're making;
- the `jetstream lint` workflow checks every commit in a pull request, so a pull request with a commit that isn't signed off can't be merged.

To fix the last commit, run `git commit --amend -s`. For older commits, run `git rebase --signoff main` and force-push the branch.

## The DCO

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
