# Setting up an org for jetstream

What an org does once, as an org owner, before its repos adopt jetstream. Each repo then adopts it as [adopting.md](adopting.md) says.

## 1. Mark the repos that use jetstream

Define a repo custom property, `jetstream`, in the org's **Settings → Repository → Custom properties**:

- **Name:** `jetstream`
- **Description:** `true if this repo uses jetstream`
- **Type:** **True/false**
- **Required:** off, so a repo's value is a decision, not a default
- **Allow repository actors to set this property:** off, so only org owners can set it

Each repo that uses jetstream is set to `true`, and every other repo to `false`. The org's rulesets (next section) use it to require `jetstream lint` only where jetstream runs, so a repo that doesn't use jetstream can still merge pull requests.

## 2. Protect every default branch

Two org rulesets (**Settings → Repository → Rulesets → New ruleset → New branch ruleset**), with no bypass actors, so they bind org owners too:

- **`default branch`**, on every repo's default branch (target **All repositories**, branches **Include default branch**): restrict deletions, block force pushes, require signed commits, and require a pull request before merging, with 0 approvals if the org has one member, who can't approve their own pull requests.
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

## 3. Allow jetstream's actions

If the org restricts which GitHub Actions can run (**Settings → Actions → General → Policies**), allow the ones jetstream's workflows use: `actions/checkout`, `actions/create-github-app-token` and `astral-sh/setup-uv`, at the commit SHAs its workflows pin ([github-actions.md](github-actions.md)).

## 4. Set up the Dependabot alert sync

Create the GitHub App the `jetstream-sync-dependabot-alerts.yaml` workflow runs as, and give it the org variable it needs: [dependabot-alerts.md](dependabot-alerts.md), "Setting it up for an org".
