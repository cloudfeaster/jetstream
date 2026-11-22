# Changelog

## [0.10.0](https://github.com/cloudfeaster/jetstream/compare/v0.9.1...v0.10.0) (2026-11-22)


### Features

* skip CodeRabbit reviews of release-please PRs ([#70](https://github.com/cloudfeaster/jetstream/issues/70)) ([0a0d832](https://github.com/cloudfeaster/jetstream/commit/0a0d83247454a9df4660cb878bf7dd6fbb73c651))

## [0.9.1](https://github.com/cloudfeaster/jetstream/compare/v0.9.0...v0.9.1) (2026-11-22)


### Bug Fixes

* stage new-repo's files before the first check, and qualify CodeRabbit's review start ([#68](https://github.com/cloudfeaster/jetstream/issues/68)) ([0237d43](https://github.com/cloudfeaster/jetstream/commit/0237d438eac5cbaab6184c857618d49825bc8491))

## [0.9.0](https://github.com/cloudfeaster/jetstream/compare/v0.8.0...v0.9.0) (2026-11-22)


### Features

* add public pack with CodeRabbit config ([#67](https://github.com/cloudfeaster/jetstream/issues/67)) ([96a1a07](https://github.com/cloudfeaster/jetstream/commit/96a1a07580aa2236ef3d71267984918b9f7fb8f9))
* check the license of every tool jetstream installs ([#66](https://github.com/cloudfeaster/jetstream/issues/66)) ([1d85c55](https://github.com/cloudfeaster/jetstream/commit/1d85c5547e12cb969f4c05b3ec4e34722e7a6853))


### Bug Fixes

* start a new repo the way the org expects: branch main, no wiki, set up for jetstream at once ([#63](https://github.com/cloudfeaster/jetstream/issues/63)) ([7bcc92f](https://github.com/cloudfeaster/jetstream/commit/7bcc92fb54278b13a4c465ccfadeedb0c80795f9))

## [0.8.0](https://github.com/cloudfeaster/jetstream/compare/v0.7.0...v0.8.0) (2026-11-21)


### Features

* add jetstream new-repo, and the jetstream-new-repo skill ([#60](https://github.com/cloudfeaster/jetstream/issues/60)) ([c9e8cc7](https://github.com/cloudfeaster/jetstream/commit/c9e8cc70a644eabb6b9142d9cbe5e1108a356692))

## [0.7.0](https://github.com/cloudfeaster/jetstream/compare/v0.6.0...v0.7.0) (2026-11-21)


### Features

* document the python pack's conventions, and allow tests beside the code ([#58](https://github.com/cloudfeaster/jetstream/issues/58)) ([716646e](https://github.com/cloudfeaster/jetstream/commit/716646e2bbd65fc693d0d1c253add0bd42a206df))

## [0.6.0](https://github.com/cloudfeaster/jetstream/compare/v0.5.0...v0.6.0) (2026-11-20)


### Features

* update jetstream with a scheduled workflow, not Dependabot ([#55](https://github.com/cloudfeaster/jetstream/issues/55)) ([ef3a3d4](https://github.com/cloudfeaster/jetstream/commit/ef3a3d4ea9e267c5e422bf742f1cbe2d121da4f1))

## [0.5.0](https://github.com/cloudfeaster/jetstream/compare/v0.4.0...v0.5.0) (2026-11-20)


### Features

* add bandit, deptry and pyscn to the python pack ([#42](https://github.com/cloudfeaster/jetstream/issues/42)) ([ebf063c](https://github.com/cloudfeaster/jetstream/commit/ebf063ceda30b7c500c01b527ad5a91935253654))
* add pip-audit and licensecheck to the python pack ([#45](https://github.com/cloudfeaster/jetstream/issues/45)) ([15267f9](https://github.com/cloudfeaster/jetstream/commit/15267f99febca01ac84c9ee506bd5449a3560ecc))
* add the python pack's part of the patch-vuln skill ([#48](https://github.com/cloudfeaster/jetstream/issues/48)) ([bdd2d13](https://github.com/cloudfeaster/jetstream/commit/bdd2d133315e4cb5efcab705dbfe8baff6852baa))
* measure coverage in the unit-tests hook for the python pack ([#44](https://github.com/cloudfeaster/jetstream/issues/44)) ([08287b3](https://github.com/cloudfeaster/jetstream/commit/08287b3121efc63506dee2c898b7db3eeb3fde94))
* prune redundant [tool.uv] constraints and cooldown overrides ([#50](https://github.com/cloudfeaster/jetstream/issues/50)) ([a79054d](https://github.com/cloudfeaster/jetstream/commit/a79054df7eeeb5b8a5a6389393272b1adc30326c))
* prune scan exceptions that no longer match a finding ([#51](https://github.com/cloudfeaster/jetstream/issues/51)) ([cfb54bf](https://github.com/cloudfeaster/jetstream/commit/cfb54bf89faa803b6425e2c03be872d67f9100f0))
* run integration tests in CI, and build python-pack packages ([#49](https://github.com/cloudfeaster/jetstream/issues/49)) ([270dcc4](https://github.com/cloudfeaster/jetstream/commit/270dcc44219bf18d4df4922abd30dcbdb5ba0f8a))
* sync Dependabot alerts with the scanners' exceptions ([#52](https://github.com/cloudfeaster/jetstream/issues/52)) ([c60be1b](https://github.com/cloudfeaster/jetstream/commit/c60be1be59f8bb9bdb1842ae0e7b26ba690fa610))


### Documentation

* say how an org and a repo set up for jetstream ([#53](https://github.com/cloudfeaster/jetstream/issues/53)) ([c42946d](https://github.com/cloudfeaster/jetstream/commit/c42946defff29830321520e7a17f5d8c8653d20f))

## [0.4.0](https://github.com/cloudfeaster/jetstream/compare/v0.3.0...v0.4.0) (2026-11-18)


### Features

* add the python pack, starting with ruff and ty ([#39](https://github.com/cloudfeaster/jetstream/issues/39)) ([b4f52cb](https://github.com/cloudfeaster/jetstream/commit/b4f52cb927beda76f8e6a487273ff5379e76e588))

## [0.3.0](https://github.com/cloudfeaster/jetstream/compare/v0.2.0...v0.3.0) (2026-11-18)


### Features

* add sqlfluff to the core pack ([#38](https://github.com/cloudfeaster/jetstream/issues/38)) ([2336329](https://github.com/cloudfeaster/jetstream/commit/233632909618ab4e09100ca0b6fc26876f4ad84b))
* add the jetstream-patch-vuln skill to the core pack ([#34](https://github.com/cloudfeaster/jetstream/issues/34)) ([a9a2728](https://github.com/cloudfeaster/jetstream/commit/a9a272852d5b82a7933e5caca4e323cbb43627d2))
* scan dependencies nightly, with jetstream's own trivy exceptions ([#33](https://github.com/cloudfeaster/jetstream/issues/33)) ([1a5f833](https://github.com/cloudfeaster/jetstream/commit/1a5f8338b1f115d467fe7a1d66e6023de3ff9858))
* ship new-feature and ship as Claude Code skills in the core pack ([#32](https://github.com/cloudfeaster/jetstream/issues/32)) ([abdb46d](https://github.com/cloudfeaster/jetstream/commit/abdb46dedf795e59ce0725bf996abbdcf698f3e8))


### Documentation

* say how to take a jetstream release that changes owned files ([#29](https://github.com/cloudfeaster/jetstream/issues/29)) ([8fd3675](https://github.com/cloudfeaster/jetstream/commit/8fd3675e87dc64f94f1f2969eb64d29a2e7291e7))
* say jetstream ships Claude Code skills, not plugins ([#35](https://github.com/cloudfeaster/jetstream/issues/35)) ([d453025](https://github.com/cloudfeaster/jetstream/commit/d45302500a7ec5fd2ef9c19550d53d96898a3cdd))

## [0.2.0](https://github.com/cloudfeaster/jetstream/compare/v0.1.3...v0.2.0) (2026-11-18)


### Features

* document why jetstream can include GPL development tools ([#27](https://github.com/cloudfeaster/jetstream/issues/27)) ([11d3799](https://github.com/cloudfeaster/jetstream/commit/11d3799751fd17715448777325dc23a8fc06423c))

## [0.1.3](https://github.com/cloudfeaster/jetstream/compare/v0.1.2...v0.1.3) (2026-11-18)


### Documentation

* say how the org rulesets protect release tags ([#25](https://github.com/cloudfeaster/jetstream/issues/25)) ([ae6d3d2](https://github.com/cloudfeaster/jetstream/commit/ae6d3d2fd921f99e7961dcf3b76bf736078b08c1))

## [0.1.2](https://github.com/cloudfeaster/jetstream/compare/v0.1.1...v0.1.2) (2026-11-17)


### Bug Fixes

* skip Dependabot's cooldown for jetstream with any extras ([#23](https://github.com/cloudfeaster/jetstream/issues/23)) ([ca5bcb2](https://github.com/cloudfeaster/jetstream/commit/ca5bcb21c811fbbf8ceef38273ad0f143e6be96d)), closes [#1](https://github.com/cloudfeaster/jetstream/issues/1)

## [0.1.1](https://github.com/cloudfeaster/jetstream/compare/v0.1.0...v0.1.1) (2026-11-17)


### Documentation

* give the release PR's real branch name ([#21](https://github.com/cloudfeaster/jetstream/issues/21)) ([bdbe260](https://github.com/cloudfeaster/jetstream/commit/bdbe2604b5fa9f788d54449871609ec77e59c8af))

## 0.1.0 (2026-11-17)


### ⚠ BREAKING CHANGES

* .jetstream/docs/core/dco.md is gone, so a repo whose CLAUDE.md imports it or whose CONTRIBUTING.md links to it must drop those lines.

### Features

* add core's VS Code, Claude Code, Dependabot and docs files ([#9](https://github.com/cloudfeaster/jetstream/issues/9)) ([d2be71e](https://github.com/cloudfeaster/jetstream/commit/d2be71ebb2ce9d9a2fb7e28387c928aefdfd65b2))
* add jetstream sync and jetstream check for the core pack ([#7](https://github.com/cloudfeaster/jetstream/issues/7)) ([c9edc9f](https://github.com/cloudfeaster/jetstream/commit/c9edc9f9cb9a2463205b073d92a4f64fbd09636b))
* add the core pack's tools, scripts and configs ([#6](https://github.com/cloudfeaster/jetstream/issues/6)) ([af50967](https://github.com/cloudfeaster/jetstream/commit/af509670f53404103244abb1aee07b3711cb1a11))
* add the generated jetstream-lint.yaml workflow ([#8](https://github.com/cloudfeaster/jetstream/issues/8)) ([3772840](https://github.com/cloudfeaster/jetstream/commit/377284013be03e9b1c34f75bfde54d4bae8b6a7d))
* add the package and repo skeleton ([#4](https://github.com/cloudfeaster/jetstream/issues/4)) ([d1f7a93](https://github.com/cloudfeaster/jetstream/commit/d1f7a933cd3db4ebde085364d22464723b62812c))
* bundle the pinned binary tools into the wheel ([#5](https://github.com/cloudfeaster/jetstream/issues/5)) ([5cc2ba3](https://github.com/cloudfeaster/jetstream/commit/5cc2ba36fe97cb389d5cabde39e6d6b7f7fd30b5))
* cut releases with release-please ([#19](https://github.com/cloudfeaster/jetstream/issues/19)) ([5614ec7](https://github.com/cloudfeaster/jetstream/commit/5614ec78e3b44232024dd1ed49d6f17e226d3c73)), closes [#1](https://github.com/cloudfeaster/jetstream/issues/1)
* remove the DCO check from core ([#18](https://github.com/cloudfeaster/jetstream/issues/18)) ([b978fe6](https://github.com/cloudfeaster/jetstream/commit/b978fe6f09b6e9d45cac5a9ce90f2a4c1bd3795c))


### Bug Fixes

* enable all shellcheck checks and fix their findings ([#14](https://github.com/cloudfeaster/jetstream/issues/14)) ([9f4a7f2](https://github.com/cloudfeaster/jetstream/commit/9f4a7f258d3277462181de95f556e0e1ddf26ca6))


### Documentation

* add core's shared docs and use them in jetstream ([#10](https://github.com/cloudfeaster/jetstream/issues/10)) ([86e9f56](https://github.com/cloudfeaster/jetstream/commit/86e9f5688c0b2cb2aac9d34cefe25ce0bcf494af))
* update README.md ([#11](https://github.com/cloudfeaster/jetstream/issues/11)) ([7a2b306](https://github.com/cloudfeaster/jetstream/commit/7a2b306c93cc147036b620bd404f5ababa81ce47))
