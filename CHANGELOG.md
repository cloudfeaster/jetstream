# Changelog

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
