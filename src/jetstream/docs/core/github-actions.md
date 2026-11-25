# GitHub Actions

Rules for every workflow, the repo's own and jetstream's. The `zizmor` hook audits them all with zizmor's auditor persona, which reports every finding however unlikely.

## Triggers

Every workflow has a `workflow_dispatch:` trigger, next to its other triggers, so it can be run by hand from the Actions tab (or `gh workflow run`).

## Pin actions to a commit SHA

Pin every action to its full 40-character commit SHA, with the version in a comment:

```yaml
uses: actions/checkout@3d3c42e5aac5ba805825da76410c181273ba90b1  # v7.0.1
```

A tag can be moved to different code by the action's owner, or by anyone who compromises them, and every workflow using the tag then runs that code. This has happened: `aquasecurity/trivy-action` had 76 of its 77 version tags repointed at a credential-stealing payload. A SHA can't be moved.

Dependabot still updates SHA-pinned actions, changing the SHA and the comment together. It does that for the repo's own workflows only: the actions in `jetstream-*.yaml` are updated by jetstream's releases. A repo with no workflow of its own has no `github-actions` entry in `.github/dependabot.yml`, so adding its first one needs a `jetstream sync` (`jetstream check` says so). Don't pin to a major tag such as `@v7`: Dependabot never proposes a new major version for one. The org also requires SHA pinning, so a workflow using a tag fails to start.

## Which actions

The org only runs actions written by GitHub, actions in Cloudfeaster's own repos, and an allowlist of third-party actions. Using a new third-party action means adding it to the org allowlist first, or the workflow fails.

## Permissions and credentials

- Set `permissions: {}` at the top of the workflow, and give each job only the permissions it needs.
- Check out with `persist-credentials: false`, unless a later step has to push.
- Don't put `${{ ... }}` expressions in a `run:` script. Pass them in through `env:` and use the variable, so a value can't inject shell code.
- Give each job a `name:`. A required status check is a job's name, so it must stay the same across changes.
- A secret only `main` should read, such as an app's private key, goes in a GitHub environment that only `main` can deploy to, and the job names the environment (`environment:`).
