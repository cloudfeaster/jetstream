<!-- Written by `jetstream sync` from cloudfeaster/jetstream's docs; don't edit. -->

# Setting up an org for jetstream

What an org does once, as an org owner, before its repos adopt jetstream. Each repo then adopts it as [adopting.md](adopting.md) says.

Sections 1 to 6 harden the org itself. They're the settings Cloudfeaster runs its own org with, so an org that follows them is at least as well protected as Cloudfeaster's. They're recommendations: jetstream doesn't need or check them, and each org is responsible for its own security. Sections 7 to 10 are what jetstream needs.

Some settings need a paid plan:

- **GitHub Team or above:** org rulesets (section 8) and org Actions policies (section 4). On Free, an org Actions policy isn't enforced, so set the policy on each repo instead.
- **Code Security and Secret Protection add-ons:** CodeQL and secret scanning on private repos (section 5). They're free on public repos.

The `gh api` commands need an owner's login with the `admin:org` scope. It can change org settings, not just read them, so remove it when you're done:

```bash
gh auth refresh -h github.com -s admin:org
# ... run commands ...
gh auth refresh -h github.com -r admin:org
```

## 1. Require 2FA

Every member and outside collaborator must have two-factor authentication, so a stolen password alone isn't enough to act as a member: **Settings → Authentication security → Require two-factor authentication**. Only the UI can turn this on. Turning it on blocks members without 2FA from the org's resources until they enable it, and removes outside collaborators without it, bots and service accounts included, so first check who that would be:

```bash
gh api 'orgs/<org>/members?filter=2fa_disabled' --paginate --jq '.[].login'
gh api 'orgs/<org>/outside_collaborators?filter=2fa_disabled' --paginate --jq '.[].login'
```

## 2. Limit what members can do

- **Base permission "No permission"** (**Settings → Member privileges**). Members get access to a repo only when it's granted, per repo or per team. Give non-technical members Triage or Write at most, never Maintain or Admin, so their compromised account can't change a repo's settings or secrets.
- **Only owners create repos** (same page, **Repository creation**: untick **Public** and **Private**). A member who creates a repo is its admin, which gets around the base permission, and a public repo created by mistake publishes whatever is pushed to it.

```bash
gh api -X PATCH orgs/<org> -f default_repository_permission=none \
  -F members_can_create_public_repositories=false -F members_can_create_private_repositories=false
```

## 3. Restrict GitHub Actions

In **Settings → Actions → General**:

- **Allow only selected actions:** actions written by GitHub, actions in the org's own repos, and an allowlist of third-party actions. Leave out actions by verified creators, so a third-party action only runs if someone added it on purpose. jetstream's workflows use one third-party action, `astral-sh/setup-uv`; the rest are GitHub's.
- **Require actions to be pinned to a full commit SHA**, so an action's owner, or anyone who compromises them, can't repoint a tag at different code ([github-actions.md](github-actions.md)).
- **Workflow permissions: Read repository contents and packages permissions**, and **Allow GitHub Actions to create and approve pull requests** off. A workflow that leaves out its `permissions:` block then gets a token that can't push or approve its own changes. jetstream's workflows set `permissions: {}` and grant each job what it needs, so this changes nothing for them.

```bash
gh api -X PUT orgs/<org>/actions/permissions \
  -f enabled_repositories=all -f allowed_actions=selected -F sha_pinning_required=true
gh api -X PUT orgs/<org>/actions/permissions/selected-actions --input - <<< \
  '{"github_owned_allowed": true, "verified_allowed": false, "patterns_allowed": ["astral-sh/setup-uv@*"]}'
gh api -X PUT orgs/<org>/actions/permissions/workflow \
  -f default_workflow_permissions=read -F can_approve_pull_request_reviews=false
```

Run them in that order: the allowlist is only accepted once `allowed_actions` is `selected`. `patterns_allowed` replaces the whole list, so send every entry each time. Entries end in `@*` because workflows already pin SHAs: allowlisting exact SHAs would block every Dependabot bump.

## 4. Allow only the workflow events you use

Some events run a workflow with a write token and the repo's secrets even when a stranger causes them. With `pull_request_target`, a workflow that checks out a fork's pull request and runs its code runs it with the repo's credentials. With `issue_comment`, a workflow that puts comment text into a shell script runs whatever the comment says. Both have been the way in for real supply-chain attacks. An org Actions policy that lists the events workflows may run on stops them in every repo, including a workflow that gets past the `zizmor` hook, or a repo that doesn't use jetstream.

jetstream's workflows run on `pull_request`, `push`, `schedule` and `workflow_dispatch`. Add any other event the org's own workflows need, such as `release`. A workflow on an event that isn't listed doesn't start. **Settings → Actions → Policies**, or, as JSON, for `gh api -X POST orgs/<org>/actions/policies --input <file>`:

```json
{
  "name": "allowed workflow events",
  "enforcement": "active",
  "conditions": {
    "repository_name": {"include": ["~ALL"], "exclude": []}
  },
  "rules": [
    {"type": "restrict_action_events", "parameters": {"allowed_events": ["pull_request", "push", "schedule", "workflow_dispatch"]}}
  ]
}
```

To find the events the org's workflows use now, search its code for `path:.github/workflows`. Code search only covers default branches.

## 5. Turn on code security for every repo

Two code security configurations (**Settings → Advanced Security → Configurations**), each the default for new repos of its visibility, attached to every existing one, and enforced, so a repo can't turn its settings off:

- **`<org> public`**: the dependency graph, Dependabot alerts and security updates, secret scanning and push protection, CodeQL default setup, and private vulnerability reporting. A known-vulnerable dependency is then reported and patched by a pull request, a pushed secret is blocked, code is scanned, and anyone can report a vulnerability privately.
- **`<org> private`**: what's free on private repos, the dependency graph and Dependabot alerts and security updates. Add secret scanning and CodeQL if the org buys them. Until then, jetstream's `gitleaks` hook is what catches secrets in a private repo.

As JSON, for `gh api -X POST orgs/<org>/code-security/configurations --input <file>`:

```json
{
  "name": "<org> public",
  "description": "Default for public repos",
  "advanced_security": "enabled",
  "dependency_graph": "enabled",
  "dependabot_alerts": "enabled",
  "dependabot_security_updates": "enabled",
  "secret_scanning": "enabled",
  "secret_scanning_push_protection": "enabled",
  "code_scanning_default_setup": "enabled",
  "private_vulnerability_reporting": "enabled",
  "enforcement": "enforced"
}
```

```json
{
  "name": "<org> private",
  "description": "Default for private repos",
  "advanced_security": "disabled",
  "dependency_graph": "enabled",
  "dependabot_alerts": "enabled",
  "dependabot_security_updates": "enabled",
  "secret_scanning": "disabled",
  "secret_scanning_push_protection": "disabled",
  "code_scanning_default_setup": "disabled",
  "private_vulnerability_reporting": "disabled",
  "enforcement": "enforced"
}
```

Then make each the default for new repos of its visibility, and attach it to every repo of that visibility:

```bash
ID=$(gh api orgs/<org>/code-security/configurations --jq '.[] | select(.name == "<org> public") | .id')
gh api -X PUT "orgs/<org>/code-security/configurations/$ID/defaults" -f default_for_new_repos=public
gh api -X POST "orgs/<org>/code-security/configurations/$ID/attach" -f scope=public
```

and the same for `<org> private`, with `default_for_new_repos=private_and_internal` and `scope=private_or_internal`. Attaching finishes after the command does, and attaching the second while the first is still being attached can fail with a 409, so first wait until this shows no public repo as `attaching`, then check the private ones the same way:

```bash
gh api "orgs/<org>/code-security/configurations/$ID/repositories" --paginate --jq '.[] | [.repository.name, .status] | @tsv'
```

Every repo should end up `enforced`. A `failed` one isn't managed by the configuration: find out which of its settings conflicts, fix that, and attach the configuration again. One cause is CodeQL's advanced setup, which conflicts with the default setup `<org> public` turns on. Either switch the repo to default setup, which disables its own CodeQL workflow and blocks CodeQL analysis uploads, so first check that default setup covers what that workflow does, or give the repo a configuration of its own with `code_scanning_default_setup` as `not_set`.

A repo that changes visibility keeps its configuration, so attach the other one to it.

## 6. Turn off wikis and projects

- **No repo has a wiki.** Any GitHub user can edit a public repo's wiki unless editing is restricted, so it's a place an outsider could publish under the org's name. New repos get one by default, so turn it off on each.
- **Projects are off**, org and repo, if nothing uses them: less to secure.

```bash
gh api -X PATCH repos/<org>/<repo> -F has_wiki=false -F has_projects=false
gh api -X PATCH orgs/<org> -F has_organization_projects=false -F has_repository_projects=false
```

## 7. Mark the repos that use jetstream

Define a repo custom property, `jetstream`, in the org's **Settings → Repository → Custom properties**:

- **Name:** `jetstream`
- **Description:** `true if this repo uses jetstream`
- **Type:** **True/false**
- **Required:** off, so a repo's value is a decision, not a default
- **Allow repository actors to set this property:** off, so only org owners can set it

Each repo that uses jetstream is set to `true`, and every other repo to `false`. The org's rulesets (next section) use it to require `jetstream lint` only where jetstream runs, so a repo that doesn't use jetstream can still merge pull requests.

## 8. Protect every default branch

Two org rulesets (**Settings → Repository → Rulesets → New ruleset → New branch ruleset**), with no bypass actors, so they bind org owners too:

- **`default branch`**, on every repo's default branch (target **All repositories**, branches **Include default branch**): restrict deletions, block force pushes, require signed commits, and require a pull request before merging. The JSON below requires 0 approvals, for an org with one member, who can't approve their own pull requests; with more members, raise `required_approving_review_count`.
- **`default branch: jetstream lint`**, on the default branch of every repo whose `jetstream` property is `true` (target **Dynamic list by property** → `jetstream` is `true`): require the `jetstream lint` status check, with **Require branches to be up to date before merging** on, and **Do not require status checks on creation** on, so a new repo's first push can create its default branch.

They're two rulesets so that a repo that doesn't use jetstream keeps every protection but the check. [dev-workflow.md](dev-workflow.md) says what the rules mean for day-to-day work. As JSON, for `gh api -X POST orgs/<org>/rulesets --input <file>`:

```json
{
  "name": "default branch",
  "target": "branch",
  "enforcement": "active",
  "bypass_actors": [],
  "conditions": {
    "repository_name": {"include": ["~ALL"], "exclude": []},
    "ref_name": {"include": ["~DEFAULT_BRANCH"], "exclude": []}
  },
  "rules": [
    {"type": "deletion"},
    {"type": "non_fast_forward"},
    {"type": "required_signatures"},
    {"type": "pull_request", "parameters": {"required_approving_review_count": 0, "dismiss_stale_reviews_on_push": false, "require_code_owner_review": false, "require_last_push_approval": false, "required_review_thread_resolution": false}}
  ]
}
```

```json
{
  "name": "default branch: jetstream lint",
  "target": "branch",
  "enforcement": "active",
  "bypass_actors": [],
  "conditions": {
    "repository_property": {"include": [{"name": "jetstream", "property_values": ["true"]}], "exclude": []},
    "ref_name": {"include": ["~DEFAULT_BRANCH"], "exclude": []}
  },
  "rules": [
    {"type": "required_status_checks", "parameters": {"strict_required_status_checks_policy": true, "do_not_enforce_on_create": true, "required_status_checks": [{"context": "jetstream lint"}]}}
  ]
}
```

Don't also use classic branch protection: the rulesets replace it, and two systems of rules are harder to reason about. Deleting it drops anything it requires that the rulesets don't, such as approvals or other status checks, so first see what that is, and add what the repo needs to a ruleset:

```bash
gh api repos/<org>/<repo>/branches/<branch>/protection  # a 404 means there's none
gh api -X DELETE repos/<org>/<repo>/branches/<branch>/protection
```

## 9. Set up the Dependabot alert sync

Create the GitHub App the `jetstream-sync-dependabot-alerts.yaml` workflow runs as, and give it the org variable it needs: [dependabot-alerts.md](dependabot-alerts.md), "Setting it up for an org".

## 10. Set up jetstream updates

Create the GitHub App the `jetstream-update.yaml` workflow runs as, which opens the pull request that takes each jetstream release, and give it the org variable it needs: [jetstream-update.md](jetstream-update.md), "Setting it up for an org".
