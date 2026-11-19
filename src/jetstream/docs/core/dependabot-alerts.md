# Dependabot alerts

A repo records the vulnerabilities it accepts, each for 7 days at a time, as exceptions in its scanners' ignore files (see [dev-environment.md](dev-environment.md#vulnerabilities)): `.trivyignore`, `.pip-audit-ignore`, and jetstream's `.jetstream/trivyignore` and `.jetstream/pip-audit-ignore`. Dependabot doesn't read them, so without a sync every accepted vulnerability still shows as an open alert, and a new one is lost among them.

The `jetstream-sync-dependabot-alerts.yaml` workflow makes the repo's alerts match the files, every night and whenever one of them changes on `main`:

| Alert | Exception | What the sync does |
|---|---|---|
| open | applies (its `exp:` date hasn't passed) | dismisses it as `tolerable_risk`, with a comment from the exception |
| dismissed by the sync | applies | updates the comment, if the exception changed |
| dismissed by the sync | removed, or expired | reopens it |
| dismissed by anyone else | any | leaves it alone, with a warning in the run's log |

The sync's comments start with `[jetstream exceptions]`, which is how it knows its own dismissals. The ignore files are the only record of what's accepted, so don't dismiss an alert by hand: add an exception instead (`/jetstream-patch-vuln`).

## What the sync needs

`GITHUB_TOKEN` can read Dependabot alerts but can't dismiss or reopen them, so the workflow runs as a GitHub App that the org owns. An App, unlike a personal access token, isn't tied to anyone's account and doesn't expire, and it can do only what it's given: here, change Dependabot alerts. On each run the workflow swaps the App's private key for a token that lasts an hour and only covers that repo.

The workflow needs, in every repo that uses jetstream:

- the App installed on the repo;
- the App's client ID, as the variable `DEPENDABOT_ALERTS_APP_CLIENT_ID`;
- an environment called `dependabot-alerts` that only `main` can deploy to, holding the App's private key as the secret `DEPENDABOT_ALERTS_APP_PRIVATE_KEY`. Only `main` can read the key, so a workflow changed on any other branch can't use it.

Until a repo has all three, its sync fails on every run.

## Setting it up for an org

Do these once, as an org owner. Replace `<org>` with the org's name. The App can only be created in the browser:

1. **Create the App** at `https://github.com/organizations/<org>/settings/apps/new`:
    - **GitHub App name:** `<org>-dependabot-alerts`, say. App names are unique across all of GitHub.
    - **Homepage URL:** any URL, such as the org's; it's required but unused.
    - **Webhook:** untick **Active**. The App doesn't receive events.
    - **Permissions:** Repository permissions → **Dependabot alerts**: **Read and write**. GitHub adds **Metadata**: **Read-only** itself. Leave everything else at **No access**.
    - **Where can this GitHub App be installed?** **Only on this account**.
    - Click **Create GitHub App**.
1. **Note the client ID.** It's on the App's page (`Iv23li...`).
1. **Install the App.** In the App's sidebar, click **Install App → Install** next to the org. Choose **Only select repositories** and pick the repos that use jetstream, so it can't touch any other repo's alerts. (**All repositories** also works, and covers a new repo without the next section's first step.)
1. **Give every repo the client ID**, as an org variable. It isn't secret:

    ```bash
    gh variable set DEPENDABOT_ALERTS_APP_CLIENT_ID --org <org> --visibility all --body 'Iv23li...'
    ```

1. **Set up each repo** that uses jetstream, as in the next section.

## Adding a repo

For each repo that uses jetstream, including one created later:

1. **Add the repo to the App's installation**, unless it's installed on all repositories: the org's **Settings → GitHub Apps →** the App's **Configure → Repository access**.
1. **Generate a private key** on the App's page (**Private keys → Generate a private key**). The browser downloads a `.pem` file. An App can have several keys, so this doesn't affect the other repos.
1. **Create the environment and store the key**, then delete the download, since the repo has the copy it needs:

    ```bash
    repo=<org>/<repo>
    gh api --silent -X PUT "repos/${repo}/environments/dependabot-alerts" \
        --input - <<< '{"deployment_branch_policy": {"protected_branches": false, "custom_branch_policies": true}}'
    gh api --silent -X POST "repos/${repo}/environments/dependabot-alerts/deployment-branch-policies" \
        -f name=main -f type=branch
    gh secret set DEPENDABOT_ALERTS_APP_PRIVATE_KEY -R "${repo}" --env dependabot-alerts < ~/Downloads/<app>.*.private-key.pem
    rm ~/Downloads/<app>.*.private-key.pem
    ```

    The first two commands create the environment and allow only `main` to deploy to it (**Settings → Environments → dependabot-alerts** shows it). To set up several repos at once, run them in a loop with one key.

1. **Test it** once the repo has taken a jetstream release with this workflow: run it by hand on `main` (Actions → jetstream sync dependabot alerts → Run workflow). Its log lists each alert it dismissed, updated or reopened. A run on any other branch fails at the start, because the environment only allows `main`.

If a key is ever lost or might be exposed, delete it on the App's page, and set up each repo that used it again with a new one.

## Checking the setup

To check a repo's setup by hand:

```bash
repo=<org>/<repo>
gh api "repos/${repo}/environments/dependabot-alerts" --jq '.deployment_branch_policy'
gh api "repos/${repo}/environments/dependabot-alerts/deployment-branch-policies" --jq '[.branch_policies[].name]'
gh api "repos/${repo}/environments/dependabot-alerts/secrets" --jq '[.secrets[].name]'
```

Expected: `{"custom_branch_policies":true,"protected_branches":false}`, `["main"]` and `["DEPENDABOT_ALERTS_APP_PRIVATE_KEY"]`.
