# CodeRabbit

The public pack is for a repo that's public. It writes `.coderabbit.yaml`, so [CodeRabbit](https://www.coderabbit.ai/) reviews every pull request the same way in every public repo: in Canadian English (`en-CA`), with the `chill` review profile and a high-level summary added to the pull request's description. CodeRabbit's full reviews are free for public repos; a private repo leaves the pack out.

CodeRabbit reads the file from the repo; the CodeRabbit GitHub App must be installed on the repo for it to review anything. It reviews pull requests into the default branch on its own, but not drafts, so its first review comes when the pull request is marked ready ([dev-workflow.md](../core/dev-workflow.md)). A pull request into any other branch isn't reviewed automatically unless `reviews.auto_review.base_branches` lists that branch, which the file doesn't; comment `@coderabbitai review` on it to ask for a review.

## Adding the pack

`jetstream new-repo` doesn't take the pack, so a public repo adds it once it's started, as does a private repo that's made public:

1. Add `"public"` to `[tool.jetstream] packs`, and `public` to the extras on `cloudfeaster-jetstream` in `[dependency-groups] dev` (`[core,public]`, ...).
1. Run `uv lock`, then `jetstream sync`, and commit `.coderabbit.yaml` and the rest.

A repo that's made private takes the pack out the same way and deletes `.coderabbit.yaml` itself: `jetstream sync` only deletes files in its own folders.
