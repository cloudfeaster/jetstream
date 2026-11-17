# CLAUDE.md

Guidance for Claude Code in the jetstream repo. jetstream follows the conventions it ships; they're imported below from `.jetstream/docs/`, which `jetstream sync` writes from `src/jetstream/docs/` (edit them there).

@.jetstream/docs/core/behavioral-guidelines.md
@.jetstream/docs/core/dev-workflow.md
@.jetstream/docs/core/dev-environment.md
@.jetstream/docs/core/github-actions.md
@.jetstream/docs/core/markdown.md
@.jetstream/docs/core/json.md
@.jetstream/docs/core/diagrams.md
@.jetstream/docs/core/licensing.md

## jetstream itself

- `README.md` explains what jetstream is; `CONTRIBUTING.md` how to work on it.
- Issue #1 holds the phase 1 plan and its numbered decisions.
- The package is `src/jetstream/`: `files/<pack>/` (owned files, copied as-is), `parts/<pack>/` (combined across packs), `docs/<pack>/`, and `bin/<pack>/` (the `run-*.sh` scripts, installed into `.venv/bin`). `hatch_build.py` downloads and verifies the binaries pinned in `binaries.toml`; `bin/update-binary.py` bumps a pin.
- Type-annotate every variable assigned with `=`, including in tests; module constants are `Final`.
