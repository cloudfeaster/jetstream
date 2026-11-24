# CodeRabbit

The public pack is for a repo that's public. It writes `.coderabbit.yaml`, so [CodeRabbit](https://www.coderabbit.ai/) reviews every pull request the same way in every public repo: in Canadian English (`en-CA`), with the `chill` review profile and a high-level summary added to the pull request's description. CodeRabbit's full reviews are free for public repos; a private repo leaves the pack out.

CodeRabbit reads the file from the repo; the CodeRabbit GitHub App must be installed on the repo for it to review anything. It reviews pull requests into the default branch on its own, but not drafts, so its first review comes when the pull request is marked ready ([dev-workflow.md](../core/dev-workflow.md)). A pull request into any other branch isn't reviewed automatically unless `reviews.auto_review.base_branches` lists that branch, which the file doesn't; comment `@coderabbitai review` on it to ask for a review. Nor does it automatically review release-please's pull requests, which the cloudfeaster-release App opens (`cloudfeaster-release[bot]`): they only bump the version and add to `CHANGELOG.md`. Or Dependabot's (`dependabot[bot]`): they're mostly lockfile changes, which CodeRabbit leaves out of a review anyway, and CI is what tells whether an update works. `@coderabbitai review` still asks for a review of either.

## Working through its review

A pull request's CodeRabbit findings are dealt with before it merges, and each one gets an answer in the pull request, so the decision is recorded where the finding is:

1. Mark the pull request ready, and wait for CodeRabbit's review. Its check passes whatever it found, so read its comments.
1. Decide each finding. A Trivial finding or a nitpick is the author's call; anything above that (Minor, Major or Critical) is shown to whoever owns the change, with a recommendation, before anything is done about it.
1. Fix it, decline it, or defer it to an issue, and answer in its thread, naming the commit or the issue. Reply only once the fix is pushed.
1. If anything was fixed, push the fixes together and go back to step 1: CodeRabbit reviews each push, unless it doesn't review the pull request automatically (see above) or it has paused, as it does after 5 reviewed commits. Comment `@coderabbitai review` to ask for the review then. After about 3 rounds, decide whether to keep going.
1. Once a review leaves nothing open, the pull request can be squash-merged ([dev-workflow.md](../core/dev-workflow.md)).

In Claude Code, `/jetstream-ship` does this, from the public pack's `.claude/skills/jetstream-ship/coderabbit.md`.

## Adding the pack

`jetstream new-repo` doesn't take the pack, so a public repo adds it once it's started, as does a private repo that's made public:

1. Add `"public"` to `[tool.jetstream] packs`, and `public` to the extras on `cloudfeaster-jetstream` in `[dependency-groups] dev` (`[core,public]`, ...).
1. Run `uv lock`, then `jetstream sync`, and commit `.coderabbit.yaml` and the rest.

A repo that's made private takes the pack out the same way and deletes `.coderabbit.yaml` itself: `jetstream sync` only deletes files in its own folders.
