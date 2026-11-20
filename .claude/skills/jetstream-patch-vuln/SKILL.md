---
name: jetstream-patch-vuln
description: Review and resolve one vulnerability from a dependency scan - trivy, or a pack's scanner such as pip-audit - that is newly failing, or whose temporary exception has expired or is about to. Works out who owns the vulnerable package (jetstream's tools or the repo's own dependencies), then fixes it, adds a dated exception, or says the fix belongs in jetstream; then verifies, commits and opens a pull request. Use when the user says things like "review CVE-...", "patch CVE-...", "trivy failed", "nightly SCA failed", when the trivy or another scan hook blocks a commit, or when .trivyignore, .jetstream/trivyignore or a pack's ignore file such as .pip-audit-ignore needs attention.
---

# Patch a vulnerability

One vulnerability ID at a time (`CVE-2026-12345`, `GHSA-xxxx-xxxx-xxxx`), flagged by `jetstream-nightly-sca.yaml` or a scan hook. If the user didn't give one, take it from the failing run (`gh run list --workflow jetstream-nightly-sca.yaml`), or from the exception that expires soonest.

`.jetstream/docs/core/dev-environment.md` "Vulnerabilities" has the rules this follows. In short: whoever owns the vulnerable package fixes it, and an exception expires 7 days out so it's reviewed again.

**Packs add to this skill.** For each `*.md` file next to this one (such as `python.md`), read it before going on: it covers its pack's scanner and how to fix that ecosystem's dependencies, whichever scanner found the vulnerability.

## When a hook raised it

The scan hooks check every lockfile, so they also block commits that have nothing to do with dependencies, often on a feature branch, the day an exception expires.

- **Don't skip the hook yourself.** `SKIP=trivy git commit ...` is the user's call, one commit at a time, and the next commit is blocked too.
- **Fix it on its own branch from `main`.** `main` has the same lockfile and is failing its nightly scan too. Stash the feature branch's work (or use a git worktree), and start at step 1.
- Once the fix merges, update the feature branch from `main` and commit with every hook on.

## 1. Branch and reproduce

```bash
git switch main && git pull
git switch -c fix/review-<ID>
run-trivy.sh
```

Run every pack's scanner too, even if only one failed: the IDs each one reports can differ.

If the ID is already in `.trivyignore` or `.jetstream/trivyignore`, this is a re-review: the entry's comment says what the last review found (the fixed version and when it was published, why it was excepted, when to look again). Start from that, and tell the user it's a re-review, not a new finding.

## 2. Work out who owns the package

Find why the vulnerable package is in the lockfile trivy names. For `uv.lock`:

```bash
uv tree --invert --package <name> --frozen
```

- **Every path leads to `cloudfeaster-jetstream`**: it's one of jetstream's tools, or something one needs. jetstream fixes it (step 3a).
- **A path leads to the repo's own dependencies**: the repo fixes it (step 3b). If jetstream's tools need it too, the finding only clears once both are fixed.

To tell whether you're in jetstream itself, check `pyproject.toml`'s `[project] name`: `cloudfeaster-jetstream`.

## 3a. A vulnerability in jetstream's tools

**In a repo that uses jetstream:** stop. Tell the user the fix belongs in jetstream, to make with `/jetstream-patch-vuln` in a clone of jetstream. The repo's scans keep failing until it takes a jetstream release that fixes the vulnerability or adds an exception for it. That's deliberate: never add a `.trivyignore` entry for it, and never pin or upgrade one of jetstream's dependencies in the repo. Check whether that release is already out: `gh pr list --search cloudfeaster-jetstream` shows Dependabot's bump. Close any Dependabot pull request that bumps one of jetstream's dependencies rather than jetstream itself.

**In jetstream:** every repo resolves jetstream's dependencies in its own lockfile, so a fix has to be a requirement in jetstream's `pyproject.toml`, which every repo's resolution must meet. Upgrading jetstream's own `uv.lock` alone doesn't reach any other repo.

1. **First, is the fixed version less than 7 days old?** Find when it was published (for PyPI: `curl -s https://pypi.org/pypi/<package>/<version>/json`, `urls[].upload_time_iso_8601`). If it is, `[tool.uv] exclude-newer = "7 days"` keeps it out, so add an exception (item 4). Don't add an `exclude-newer-package` override: the cooldown keeps an unproven release out, and a "security fix" is what an attacker would publish. Only if the vulnerable code is reachable with untrusted input and the impact is severe, put an override to the user as a choice, explaining the exposure.
2. **A tool pinned in a pack's extra** (`[project.optional-dependencies]`): bump its exact pin to a fixed version.
3. **Something a tool needs**: add a floor to the same extra, with the ID in a comment, for example `"foo>=1.2.3",  # CVE-2026-12345`, then `uv lock`. Remove the floor once the tool itself requires a fixed version.
4. **No usable fix yet**: add an exception to `src/jetstream/files/core/.jetstream/trivyignore`, then run `jetstream sync`, which writes it to `.jetstream/trivyignore`:

    ```text
    CVE-2026-12345 exp:<today + 7 days>  # fixed in foo 1.2.3 (published 2026-11-26), inside the 7-day cooldown until 2026-12-03
    ```

    Renewing an entry that hasn't cleared: set `exp:` 7 days out again and update the comment. When it has cleared, upgrade (items 2 or 3) and delete the entry in the same commit.

A package only jetstream's own `[dependency-groups] dev` needs (`uv tree` shows `(group: dev)` and no extra) doesn't reach other repos: fix it in jetstream's `uv.lock`, or except it in jetstream's own `.trivyignore`, as in 3b.

## 3b. A vulnerability in the repo's own dependencies

In order of preference:

1. **Upgrade** the dependency, or the direct dependency that pulls it in, to a version with the fix. The pack file for its ecosystem says how.
2. **Add an exception** to `.trivyignore` when no fixed version can be used yet: it's still inside the 7-day cooldown (see 3a item 1), the fix isn't released, or another dependency's constraints rule it out. Use the same format as above, `exp:` 7 days out. Renew an entry by moving `exp:` on and updating the comment; when the fix can be used, upgrade and delete the entry in the same commit.

Say which option you're taking and why before you make the change, and ask when it's a close call.

## 4. Verify

```bash
run-trivy.sh
pre-commit run --all-files
```

Both must pass. If a dependency's version changed, run every pack's scanner again too, since an upgrade can bring in a new finding.

## 5. Commit, pull request and merge

Commit with a message such as `fix: review CVE-2026-12345` or `fix: upgrade foo for CVE-2026-12345`. Show the user the diff, and ask before pushing and opening the pull request. Then follow `/jetstream-ship`: wait for `jetstream lint`, and merge only after the user's go-ahead.

**In jetstream**, a `fix:` commit makes the next release a patch release. Every repo's scan clears once it takes that release. A new pin or floor, or a changed `.jetstream/trivyignore`, reaches a repo through the pull request `jetstream-update.yaml` opens, which re-locks `uv.lock` and runs `jetstream sync` (dev-workflow.md "Taking a jetstream release").
