# Website

The website pack is for a repo that's an [Astro](https://astro.build/) site. The site's npm packages, Astro among them, belong to the repo: they're in its `package.json` and `package-lock.json`, and Dependabot proposes their updates. jetstream sets up Node and npm and runs Astro's checks.

## What the repo needs

- a `package.json` and a `package-lock.json`, with `astro`, `@astrojs/check` and `typescript` in `devDependencies`;
- an `astro.config.mjs` (or `.ts`), with the site in `src/`.

A package whose code ships to the browser, and so ends up in the built site, goes in `dependencies`. Everything that only builds or checks the site, Astro included, goes in `devDependencies`: under [licensing.md](../core/licensing.md), those are development tools, and the products are the `dependencies`.

The `npm-licenses` hook checks the licenses of what `dependencies` bring in, read from `package-lock.json`, which records each package's license: MIT, Apache-2.0, a BSD license, ISC or 0BSD, or MPL-2.0 for a package that's only there because another needs it. `devDependencies` aren't checked. A package that fails and only builds the site goes in `devDependencies`; one that ships needs replacing, or an exception, which is jetstream's to make.

## What the pack adds

| File | What it does |
|---|---|
| `.nvmrc` | the Node version, for local setup and every workflow |
| `.github/workflows/jetstream-website-ci.yaml` | builds the site (`astro build`) on every pull request and push to `main`, then checks the links between its pages and files, `#fragments` included (`run-lychee.sh`, offline), and the Lighthouse budgets (`run-lighthouse.sh`); on `main`, once they pass, deploys it to GitHub Pages, if the repo has turned that on (see [Deploying](#deploying)) |
| `.github/workflows/jetstream-website-links.yaml` | every night, builds the site and checks every link, links to other sites included (`run-lychee.sh --external`), so a link that stops working fails without anyone pushing |
| the `astro-check` hook | `astro check` (Astro components, TypeScript and content collections), at every commit, since it checks the whole project |
| the `npm-licenses` hook | the licenses of the site's product dependencies, the packages in `package-lock.json` that aren't dev dependencies, are ones [licensing.md](../core/licensing.md) allows in a product (`run-npm-licenses.sh`) |
| `.npmrc` | `npm install` takes no version released in the last 7 days (`min-release-age`, as uv's `exclude-newer`), and saves exact versions |
| a Dependabot `npm` entry | the site's npm updates, grouped and with core's cooldown |
| `.gitignore` lines | `node_modules/`, `.astro/` and `.lighthouseci/` |

Locally, `cfg4dev.sh` runs `npm ci` when `package-lock.json` is newer than what's in `node_modules`. In CI, `jetstream-lint.yaml` installs Node when the repo has an `.nvmrc`, and runs `npm ci` when it has a `package-lock.json` too, so the `astro-check` hook runs there too. `npm ci` fails when `package-lock.json` doesn't match `package.json`, so that's checked as well.

## Licenses

A site's text and logo usually need other terms than its code. The files that hold them, `LICENSE-docs` for the Markdown and MDX in `src/content/` and `TRADEMARKS.md` for brand assets, are in [licensing.md](../core/licensing.md#the-repos-own-licenses). A page's text in a `.astro` file is code, under `LICENSE`.

## Links

[lychee](https://lychee.cli.rs/) checks the links in the built site, `dist/`, as the deployed site would resolve them: `run-lychee.sh` reads `site` and `base` from the Astro config, so a link to `/<base>/about/`, or to `<site>/<base>/about/`, is checked against `dist/about/index.html`. The links in a web app manifest (a `*.webmanifest` or `manifest.json` in `dist/`: its `start_url`, `icons`, `screenshots` and `shortcuts`) are checked too, resolved against the manifest's own URL, as a browser resolves them; lychee reports a broken one under `<manifest>.html` in a temporary folder, at the file's local path. Pull requests only check the site's own links, so another site's outage or rate limit can't fail one; the nightly run checks the rest. To check them yourself, after `astro build`:

```bash
run-lychee.sh             # the site's own links
run-lychee.sh --external  # and links to other sites
```

A link to another site that's right but can't be checked, because the site blocks link checkers, say, goes in the repo's `.lycheeignore`, one regular expression per line, which lychee reads.

## Lighthouse

Website CI checks the built site against jetstream's Lighthouse budgets, the same for every site (decision 25 in jetstream's #1): performance at least 0.90, and accessibility, best practices and SEO at least 0.95. `run-lighthouse.sh` serves `dist/` under the site's `base`, as it's deployed, and runs Lighthouse 3 times on each of up to 5 pages, the shallowest first; a category's median score must meet its budget. A budget that's wrong for every site is a change to jetstream. To run it yourself, after `astro build`:

```bash
run-lighthouse.sh
```

The reports go in `.lighthouseci/`, an HTML file for each run. The first run installs Lighthouse CI into `.venv`, from the lockfile jetstream ships, so it needs the network once. It also needs Chrome: install Google's package (`google-chrome-stable`), or set `CHROME_PATH` to another Chrome. On Ubuntu 23.10 and later, Chrome can only use its sandbox where an AppArmor profile allows it, and Ubuntu's (`/etc/apparmor.d/chrome`) covers where Google's package installs it, `/opt/google/chrome/`; an unpacked Chrome elsewhere, such as Chrome for Testing, fails with "No usable sandbox!". GitHub's runners have Google's Chrome.

## Deploying

Website CI deploys the site to [GitHub Pages](https://docs.github.com/en/pages) after every push to `main` whose build passes its link and Lighthouse checks, but only once the repo's Pages source is "GitHub Actions". Until then nothing is published, and the deploy job is skipped, with a notice saying why. So a site goes live when an owner chooses, not when it first takes the pack:

1. Set `site` (and `base`, for a project site without a custom domain) in the Astro config, to the URL the site will have.
1. In the repo's Settings → Pages, set the source to "GitHub Actions", and add the custom domain, if it has one. GitHub creates the `github-pages` environment, which only `main` can deploy to.
1. Run website CI on `main` (`gh workflow run jetstream-website-ci.yaml`), or push to it.

To stop publishing, an owner turns Pages off: in Settings → Pages, sets the source to "Deploy from a branch" with the branch `None`, or runs `gh api -X DELETE repos/<owner>/<repo>/pages`. Unpublishing the site isn't enough: the source stays "GitHub Actions", so the next run on `main` publishes it again. A private repo's site is public, as any Pages site is. Pull requests get no preview: build the site and look at it locally (`astro build`, then `astro preview`).

## Node

Install Node yourself, at the major version in `.nvmrc`, which is the one CI uses (with [nvm](https://github.com/nvm-sh/nvm), `nvm install`). `cfg4dev.sh` warns when `node` is another version, or isn't installed.

## Adding the pack

1. Add `"website"` to `[tool.jetstream] packs`, and `website` to the extras on `cloudfeaster-jetstream` in `[dependency-groups] dev` (`[core,website]`, ...).
1. Run `uv lock`, then `source cfg4dev.sh`, and commit what `jetstream sync` wrote.
