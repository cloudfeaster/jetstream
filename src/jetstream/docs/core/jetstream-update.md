# jetstream updates

A repo takes a jetstream release through a pull request that the `jetstream-update.yaml` workflow opens. Dependabot doesn't update jetstream (core's `dependabot.yml` ignores `cloudfeaster-jetstream*`), because it can only change the pin and `uv.lock`, and a release that changes files jetstream owns also needs `jetstream sync`'s changes.

Every night, and whenever it's run by hand, the workflow runs `run-update-jetstream.sh` on `main`. If jetstream's latest release tag is newer than the pin in `[tool.uv.sources]`, it:

1. sets the pin to the new tag;
1. runs `uv lock`, `uv sync` (installing the new release) and `jetstream sync`, then `uv lock` again in case `sync` changed `pyproject.toml`;
1. commits everything that changed, as one commit on top of `main`, to the `jetstream/update` branch;
1. opens a pull request for the branch, `build(deps): update jetstream from vA to vB`, or updates the one already open.

It runs again each night: when a newer release comes out, or `main` moves on, it makes the commit again on the new `main` and resets the branch to it, so don't push to `jetstream/update`. Once the pin is the latest release, it closes any update pull request still open. A repo whose jetstream isn't pinned to a release tag, such as jetstream itself, has nothing to update, so the run does nothing.

Taking the release is then [dev-workflow.md](dev-workflow.md), "Taking a jetstream release".

## What the workflow needs

A push with `GITHUB_TOKEN` starts no workflows, so `jetstream lint` would never run on the pull request and it could never merge. So the workflow runs as a GitHub App that the org owns, as the [Dependabot alert sync](dependabot-alerts.md) does, but a separate one: this App can change a repo's code and workflows, and the alerts App can't. The workflow makes the commit through GitHub's API rather than with `git push`, so GitHub signs it.

The workflow needs, in every repo that uses jetstream:

- the App installed on the repo;
- the App's client ID, as the variable `JETSTREAM_UPDATE_APP_CLIENT_ID`;
- an environment called `jetstream-update` that only `main` can deploy to, holding the App's private key as the secret `JETSTREAM_UPDATE_APP_PRIVATE_KEY`. Only `main` can read the key, so a workflow changed on any other branch can't use it.

Until a repo has all three, its update fails on every run, jetstream's own repo included.

## Setting it up for an org

Do these once, as an org owner. Replace `<org>` with the org's name. The App can only be created in the browser:

1. **Create the App** at `https://github.com/organizations/<org>/settings/apps/new`:
    - **GitHub App name:** `<org>-jetstream-update`, say. App names are unique across all of GitHub.
    - **Homepage URL:** any URL, such as the org's; it's required but unused.
    - **Webhook:** untick **Active**. The App doesn't receive events.
    - **Permissions:** Repository permissions → **Contents**, **Pull requests** and **Workflows**: **Read and write**. **Workflows** is needed because `jetstream sync` writes `.github/workflows/jetstream-*.yaml`. GitHub adds **Metadata**: **Read-only** itself. Leave everything else at **No access**.
    - **Where can this GitHub App be installed?** **Only on this account**.
    - Click **Create GitHub App**.
1. **Note the client ID.** It's on the App's page (`Iv23li...`).
1. **Install the App.** In the App's sidebar, click **Install App → Install** next to the org. Choose **Only select repositories** and pick the repos that use jetstream, so it can't change any other repo.
1. **Give every repo the client ID**, as an org variable. It isn't secret:

    ```bash
    gh variable set JETSTREAM_UPDATE_APP_CLIENT_ID --org <org> --visibility all --body 'Iv23li...'
    ```

1. **Set up each repo** that uses jetstream, as in the next section.

## Adding a repo

For each repo that uses jetstream, including one created later:

1. **Add the repo to the App's installation**: the org's **Settings → GitHub Apps →** the App's **Configure → Repository access**.
1. **Generate a private key** on the App's page (**Private keys → Generate a private key**). The browser downloads a `.pem` file. An App can have several keys, so this doesn't affect the other repos.
1. **Create the environment and store the key**, then delete the download, since the repo has the copy it needs:

    ```bash
    repo=<org>/<repo>
    gh api --silent -X PUT "repos/${repo}/environments/jetstream-update" \
        --input - <<< '{"deployment_branch_policy": {"protected_branches": false, "custom_branch_policies": true}}'
    gh api --silent -X POST "repos/${repo}/environments/jetstream-update/deployment-branch-policies" \
        -f name=main -f type=branch
    gh secret set JETSTREAM_UPDATE_APP_PRIVATE_KEY -R "${repo}" --env jetstream-update < ~/Downloads/<app>.*.private-key.pem
    rm ~/Downloads/<app>.*.private-key.pem
    ```

    The first two commands create the environment and allow only `main` to deploy to it. To set up several repos at once, run them in a loop with one key.

1. **Test it** once the repo has taken a jetstream release with this workflow: run it by hand on `main` (Actions → jetstream update → Run workflow). Its log says whether the pin is the latest release, or which pull request it opened or updated. A run on any other branch fails at the start, because the environment only allows `main`.

If a key is ever lost or might be exposed, delete it on the App's page, and set up each repo that used it again with a new one.

## Checking the setup

To check a repo's setup by hand:

```bash
repo=<org>/<repo>
gh api "repos/${repo}/environments/jetstream-update" --jq '.deployment_branch_policy'
gh api "repos/${repo}/environments/jetstream-update/deployment-branch-policies" --jq '[.branch_policies[].name]'
gh api "repos/${repo}/environments/jetstream-update/secrets" --jq '[.secrets[].name]'
```

Expected: `{"custom_branch_policies":true,"protected_branches":false}`, `["main"]` and `["JETSTREAM_UPDATE_APP_PRIVATE_KEY"]`.
