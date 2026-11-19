# Python: pip-audit, and fixing a Python dependency

The python pack's part of `/jetstream-patch-vuln`. Read `SKILL.md` first: this adds to its steps, it doesn't replace them.

## pip-audit

`run-pip-audit.sh` audits every package in `uv.lock`, every group and extra, so jetstream's tools too. It's the same set trivy scans, but from PyPI's advisories, so a vulnerability can show up in one scanner, both, or move between them. Run both in step 1, whichever one failed:

```bash
run-trivy.sh
run-pip-audit.sh
```

pip-audit's exceptions work as trivy's do, in the same format and with the same owners:

| A vulnerability in | trivy's exception | pip-audit's exception |
|---|---|---|
| jetstream's tools | `.jetstream/trivyignore` | `.jetstream/pip-audit-ignore` |
| the repo's own dependencies | `.trivyignore` | `.pip-audit-ignore` |

In jetstream itself, `.jetstream/pip-audit-ignore` is written by `jetstream sync` from `src/jetstream/files/python/.jetstream/pip-audit-ignore`: edit that, then sync.

- **Look for a re-review in all four files**, not only trivy's.
- **Record an exception under the CVE ID**, or the GHSA ID if there's no CVE, not pip-audit's `PYSEC-...` ID. pip-audit matches an exception against a finding's aliases, so one ID works for both scanners. [osv.dev](https://osv.dev/) lists a `PYSEC-...` ID's aliases.
- **When both scanners report it, both files need the entry.** Give both the same `exp:` date and comment.

## Fixing a Python dependency in the repo (step 3b)

Find why the package is there with `uv tree --invert --package <name> --frozen`, then, in order of preference:

1. **A fix the constraints already allow**: when no dependency rules out the fixed version, often because it has just cleared the 7-day cooldown, re-lock just that package. Nothing in `pyproject.toml` changes:

    ```bash
    uv lock --upgrade-package <name>
    ```

1. **A direct dependency**: raise its requirement in `[project] dependencies` (or its `[dependency-groups]` group) to a fixed version, then `uv lock`.

1. **A transitive dependency its parents hold back**: first look for a release of the direct dependency that allows the fixed version, and upgrade that (item 2). Otherwise, add a constraint in `pyproject.toml`, with the ID in a comment, then `uv lock`:

    ```toml
    [tool.uv]
    constraint-dependencies = [
        "foo>=1.2.3",  # CVE-2026-12345
    ]
    ```

    A constraint restricts the version uv picks without making the package a dependency, so deptry doesn't flag it as unused and it isn't in the published package's metadata. Remove it once the parents require a fixed version themselves: the nightly `jetstream-prune-constraints.yaml` fails, naming it, when they do. Only a floor (`>=`) can be checked that way.

1. **No usable fix yet**: add an exception (`SKILL.md` step 3b item 2) to whichever of `.pip-audit-ignore` and `.trivyignore` reports it.

Don't add a constraint for a vulnerability in jetstream's tools: that's step 3a, and jetstream fixes it.

## Verify (step 4)

After any change to `uv.lock`, run both scanners and the license check, since a new version can bring a new finding or a new license:

```bash
run-trivy.sh
run-pip-audit.sh
run-licensecheck.sh
pre-commit run --all-files
```
