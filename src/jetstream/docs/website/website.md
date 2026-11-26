# Website

The website pack is for a repo that's an [Astro](https://astro.build/) site. The site's npm packages, Astro among them, belong to the repo: they're in its `package.json` and `package-lock.json`, and Dependabot proposes their updates. jetstream sets up Node and npm and checks the site, with its own `@astrojs/check`, TypeScript and Lighthouse CI.

## What the repo needs

- a `package.json` and a `package-lock.json`, with `astro` in `devDependencies`;
- an `astro.config.mjs` (or `.ts`), with the site in `src/`.

A package whose code ships to the browser, and so ends up in the built site, goes in `dependencies`. Everything that only builds or checks the site, Astro included, goes in `devDependencies`: under [licensing.md](../core/licensing.md), those are development tools, and the products are the `dependencies`.

The `npm-licenses` hook checks the licenses of what `dependencies` bring in, read from `package-lock.json`, which records each package's license: MIT, Apache-2.0, BSD-2-Clause, BSD-3-Clause, ISC or 0BSD, OFL-1.1 for a font, or MPL-2.0 for a package that's only there because another needs it. `devDependencies` aren't checked. A package that fails and only builds the site goes in `devDependencies`; one that ships needs replacing, or an exception, which is jetstream's to make. A font ships, so it's in `dependencies`, as a package such as `@fontsource-variable/inter`. Don't use a font Astro downloads when it builds (its `fonts` setting): it isn't in `package-lock.json`, so its license isn't checked.

## What the pack adds

| File | What it does |
|---|---|
| `.nvmrc` | the Node version, for local setup and every workflow |
| steps in `jetstream lint` | on every pull request and push to `main`, builds the site (`astro build`), then checks the links between its pages and files, `#fragments` included (`run-lychee.sh`, offline), and that it has nothing a site shouldn't publish (`run-check-dist.sh`; see [What a site publishes](#what-a-site-publishes)); they're in `jetstream lint` because it's the one check a pull request must pass |
| `.github/workflows/jetstream-website-ci.yaml` | on every push to `main`, builds the site and runs the same checks, then, once they pass, deploys it to GitHub Pages, if the repo has turned that on (see [Deploying](#deploying)) |
| `.github/workflows/jetstream-website-links.yaml` | every night, builds the site and checks every link, links to other sites included (`run-lychee.sh --external`), so a link that stops working fails without anyone pushing |
| `.github/workflows/jetstream-website-lighthouse.yaml` | every night, builds the site and checks the Lighthouse budgets (`run-lighthouse.sh`; see [Lighthouse](#lighthouse)) |
| the `astro-check` hook | the site's Astro components, TypeScript and content collections, at every commit, since it checks the whole project (`run-astro-check.sh`; see [Checking types](#checking-types)) |
| the `npm-licenses` hook | the licenses of the site's product dependencies, the packages in `package-lock.json` that aren't dev dependencies, are ones [licensing.md](../core/licensing.md) allows in a product (`run-npm-licenses.sh`) |
| `.npmrc` | `npm install` takes no version released in the last 7 days (`min-release-age`, as uv's `exclude-newer`), and saves exact versions |
| a Dependabot `npm` entry | the site's npm updates, grouped and with core's cooldown |
| `.gitignore` lines | `node_modules/`, `.astro/` and `.lighthouseci/` |

Locally, `cfg4dev.sh` writes `package-lock.json` if there isn't one (`npm install --package-lock-only`), and runs `npm ci` when `package-lock.json` is newer than what's in `node_modules`. In CI, `jetstream-lint.yaml` installs Node when the repo has an `.nvmrc`, and runs `npm ci` when it has a `package-lock.json` too, so the `astro-check` hook runs there too. `npm ci` fails when `package-lock.json` doesn't match `package.json`, so that's checked as well.

## Checking types

`run-astro-check.sh` does what `astro check` does, with jetstream's `@astrojs/check` and TypeScript: a site doesn't list either, and takes new versions of them in jetstream releases. The first run installs them into `.venv`, from the lockfile jetstream ships, so it needs the network once. `astro check` itself asks to install them, so run the script instead:

```bash
run-astro-check.sh
```

A site whose own code imports `typescript` lists it, as any other package.

## Licenses

A site's text and logo usually need other terms than its code. The files that hold them, `LICENSE-docs` for the Markdown and MDX in `src/content/` and `TRADEMARKS.md` for brand assets, are in [licensing.md](../core/licensing.md#the-repos-own-licenses). A page's text in a `.astro` file is code, under `LICENSE`.

## Links

[lychee](https://lychee.cli.rs/) checks the links in the built site, `dist/`, as the deployed site would resolve them: `run-lychee.sh` reads `site` and `base` from the Astro config, so a link to `/<base>/about/`, or to `<site>/<base>/about/`, is checked against `dist/about/index.html`. A relative link is resolved against its page's URL, so `../about/` from the home page goes to `/about/`, as a browser's does, rather than to a file beside `dist/`; lychee names each page by its path in `.dist/`, a temporary folder that holds the site where its `base` puts it. The links in a web app manifest (a `*.webmanifest` or `manifest.json` in `dist/`: its `start_url`, `icons`, `screenshots` and `shortcuts`) are checked too, resolved against the manifest's own URL, as a browser resolves them; lychee reports a broken one under `<manifest>.html` in a temporary folder, at the file's local path. Pull requests only check the site's own links, so another site's outage or rate limit can't fail one; the nightly run checks the rest. To check them yourself, after `astro build`:

```bash
run-lychee.sh             # the site's own links
run-lychee.sh --external  # and links to other sites
```

A link to another site that's right but can't be checked, because the site blocks link checkers, say, goes in the repo's `.lycheeignore`, one regular expression per line, which lychee reads.

## What a site publishes

Everything in `dist/` is deployed as it is, and `astro build` puts two things there: the pages it makes from `src/`, and a copy of `public/`. So:

- **every file in `public/` is published**, wherever it is in that folder, an image with whatever metadata it has;
- **every page in the content folders is published as soon as it merges**: there's no "draft", so keep a page that isn't ready on a branch.

The repo itself, its `.env` and the rest, isn't: only what the build writes. `run-check-dist.sh` fails, naming the file, if `dist/` has:

- a secret, which [gitleaks](https://github.com/gitleaks/gitleaks) finds (a false positive goes in `.gitleaksignore`);
- a source map (`*.map`), which gives away the site's source;
- a hidden file or folder, such as `.env` or `.DS_Store`, except `.well-known/` at the top, which is meant to be published;
- metadata in an image, such as its camera, GPS location, author or the software that made it: text, EXIF and time chunks in a PNG, and EXIF or XMP in a JPEG or WebP. Astro strips it from the images it processes, but copies `public/` as it is. Strip it before committing the image, for example with `exiftool -all= <image>`.

`jetstream lint` runs it on every pull request, and website CI before every deploy. To run it yourself, after `astro build`:

```bash
run-check-dist.sh
```

## Lighthouse

Every night, `jetstream-website-lighthouse.yaml` checks the built site against jetstream's Lighthouse budgets, the same for every site (decision 25 in jetstream's #1): performance at least 0.90, and accessibility, best practices and SEO at least 0.95. `run-lighthouse.sh` serves `dist/` under the site's `base`, as it's deployed, and runs Lighthouse 3 times on each of up to 5 pages, the shallowest first; a category's median score must meet its budget. A budget that's wrong for every site is a change to jetstream. No pull request or deploy waits for it, so a page that misses a budget can be live before that night's run fails. To check before merging, run the workflow on the branch (`gh workflow run jetstream-website-lighthouse.yaml --ref <branch>`), or run it yourself, after `astro build`:

```bash
run-lighthouse.sh
```

The reports go in `.lighthouseci/`, an HTML file for each run. The first run installs Lighthouse CI into `.venv`, from the lockfile jetstream ships, so it needs the network once. It also needs Chrome: install Google's package (`google-chrome-stable`), or set `CHROME_PATH` to another Chrome. On Ubuntu 23.10 and later, Chrome can only use its sandbox where an AppArmor profile allows it, and Ubuntu's (`/etc/apparmor.d/chrome`) covers where Google's package installs it, `/opt/google/chrome/`; an unpacked Chrome elsewhere, such as Chrome for Testing, fails with "No usable sandbox!". GitHub's runners have Google's Chrome.

## Deploying

Website CI deploys the site to [GitHub Pages](https://docs.github.com/en/pages) after every push to `main` whose build passes its checks, but only once the repo's Pages source is "GitHub Actions". Until then nothing is published, and the deploy job is skipped, with a notice saying why. So a site goes live when an owner chooses, not when it first takes the pack:

1. Set `site` (and `base`, for a project site without a custom domain) in the Astro config, to the URL the site will have.
1. For a custom domain, verify it for the org first, so no other account's repo can publish to it: in the org's Settings → Pages, "Add a domain", add the TXT record GitHub gives (`_github-pages-challenge-<org>.<domain>`) at the domain's DNS provider, then "Verify".
1. In the repo's Settings → Pages, set the source to "GitHub Actions", and add the custom domain, if it has one. GitHub creates the `github-pages` environment, which only `main` can deploy to. Add the domain before the first deploy: until then the site is served from `https://<org>.github.io/<repo>/`, where a site with no `base` has broken root-relative links.
1. For a custom domain, point its DNS at Pages, and remove any other A, AAAA or CNAME records for the same names (leave MX and TXT records alone). For an apex domain (`example.com`), add four A records, `185.199.108.153`, `185.199.109.153`, `185.199.110.153` and `185.199.111.153`, and a `www` CNAME to `<org>.github.io`, which Pages redirects to the apex. For a subdomain (`docs.example.com`), add one CNAME to `<org>.github.io`. See [GitHub's docs](https://docs.github.com/en/pages/configuring-a-custom-domain-for-your-github-pages-site/managing-a-custom-domain-for-your-github-pages-site) for the AAAA records, for IPv6.
1. Once Settings → Pages shows the certificate is issued, which can take a while after DNS changes, turn on "Enforce HTTPS" (`gh api -X PUT repos/<org>/<repo>/pages -F https_enforced=true`).
1. Run website CI on `main` (`gh workflow run jetstream-website-ci.yaml`), or push to it.

To stop publishing, an owner turns Pages off: in Settings → Pages, sets the source to "Deploy from a branch" with the branch `None`, or runs `gh api -X DELETE repos/<owner>/<repo>/pages`. Unpublishing the site isn't enough: the source stays "GitHub Actions", so the next run on `main` publishes it again. A private repo's site is public, as any Pages site is.

## Local preview

Pages has no previews of pull requests, so look at a change locally. `astro dev` serves the site as you edit it. `astro build`, then `astro preview`, serves what's deployed:

```bash
node_modules/.bin/astro build
node_modules/.bin/astro preview
```

Either serves the site under its `base`, such as `http://localhost:4321/<base>/`.

## Trailing slashes

Set `trailingSlash: "always"` in the Astro config, as a new site does, and end every link to a page with a slash. Astro builds `/about/` as `about/index.html`, and GitHub Pages redirects `/about` to it. With the setting, `astro dev` and `astro preview` return a 404 for `/about`, so a link without its slash shows up locally. Nothing else catches one: `run-lychee.sh` passes a link either way.

## Node

Install Node yourself, at the major version in `.nvmrc`, which is the one CI uses (with [nvm](https://github.com/nvm-sh/nvm), `nvm install`). `cfg4dev.sh` warns when `node` is another version, or isn't installed.

## Adding the pack

1. Add `"website"` to `[tool.jetstream] packs`, and `website` to the extras on `cloudfeaster-jetstream` in `[dependency-groups] dev` (`[core,website]`, ...).
1. Run `uv lock`, then `source cfg4dev.sh`, and commit what `jetstream sync` wrote.
