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
| `.github/workflows/jetstream-website-ci.yaml` | builds the site (`astro build`) on every pull request and push to `main`, then checks the links between its pages and files, `#fragments` included (`run-lychee.sh`, offline) |
| `.github/workflows/jetstream-website-links.yaml` | every night, builds the site and checks every link, links to other sites included (`run-lychee.sh --external`), so a link that stops working fails without anyone pushing |
| the `astro-check` hook | `astro check` (Astro components, TypeScript and content collections), at every commit, since it checks the whole project |
| a Dependabot `npm` entry | the site's npm updates, grouped and with core's cooldown |
| `.gitignore` lines | `node_modules/` and `.astro/` |

Locally, `cfg4dev.sh` runs `npm ci` when `package-lock.json` is newer than what's in `node_modules`. In CI, `jetstream-lint.yaml` installs Node when the repo has an `.nvmrc`, and runs `npm ci` when it has a `package-lock.json` too, so the `astro-check` hook runs there too. `npm ci` fails when `package-lock.json` doesn't match `package.json`, so that's checked as well.

## Links

[lychee](https://lychee.cli.rs/) checks the links in the built site, `dist/`, as the deployed site would resolve them: `run-lychee.sh` reads `site` and `base` from the Astro config, so a link to `/<base>/about/`, or to `<site>/<base>/about/`, is checked against `dist/about/index.html`. Pull requests only check the site's own links, so another site's outage or rate limit can't fail one; the nightly run checks the rest. To check them yourself, after `astro build`:

```bash
run-lychee.sh             # the site's own links
run-lychee.sh --external  # and links to other sites
```

A link to another site that's right but can't be checked, because the site blocks link checkers, say, goes in the repo's `.lycheeignore`, one regular expression per line, which lychee reads.

## Node

Install Node yourself, at the major version in `.nvmrc`, which is the one CI uses (with [nvm](https://github.com/nvm-sh/nvm), `nvm install`). `cfg4dev.sh` warns when `node` is another version, or isn't installed.

## Adding the pack

1. Add `"website"` to `[tool.jetstream] packs`, and `website` to the extras on `cloudfeaster-jetstream` in `[dependency-groups] dev` (`[core,website]`, ...).
1. Run `uv lock`, then `source cfg4dev.sh`, and commit what `jetstream sync` wrote.
