# Website

The website pack is for a repo that's an [Astro](https://astro.build/) site. The site's npm packages, Astro among them, belong to the repo: they're in its `package.json` and `package-lock.json`, and Dependabot proposes their updates. jetstream sets up Node and npm and runs Astro's checks.

## What the repo needs

- a `package.json` and a `package-lock.json`, with `astro`, `@astrojs/check` and `typescript` in `devDependencies`;
- an `astro.config.mjs` (or `.ts`), with the site in `src/`.

A package whose code ships to the browser, and so ends up in the built site, goes in `dependencies`. Everything that only builds or checks the site, Astro included, goes in `devDependencies`: under [licensing.md](../core/licensing.md), those are development tools, and the products are the `dependencies`.

## What the pack adds

| File | What it does |
|---|---|
| `.nvmrc` | the Node version, for local setup and every workflow |
| `.github/workflows/jetstream-website-ci.yaml` | builds the site (`astro build`) on every pull request and push to `main` |
| the `astro-check` hook | `astro check` (Astro components, TypeScript and content collections), when anything in `src/` or the site's config changes |
| a Dependabot `npm` entry | the site's npm updates, grouped and with core's cooldown |
| `.gitignore` lines | `node_modules/` and `.astro/` |

Locally, `cfg4dev.sh` runs `npm ci` when `package-lock.json` is newer than what's in `node_modules`. In CI, `jetstream-lint.yaml` installs Node and runs `npm ci` when the repo has an `.nvmrc`, so the `astro-check` hook runs there too. `npm ci` fails when `package-lock.json` doesn't match `package.json`, so that's checked as well.

Install Node yourself, at the version in `.nvmrc` (with [nvm](https://github.com/nvm-sh/nvm), `nvm use`).

## Adding the pack

1. Add `"website"` to `[tool.jetstream] packs`, and `website` to the extras on `cloudfeaster-jetstream` in `[dependency-groups] dev` (`[core,website]`, ...).
1. Run `uv lock`, then `source cfg4dev.sh`, and commit what `jetstream sync` wrote.
