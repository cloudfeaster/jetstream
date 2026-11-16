#!/usr/bin/env node
//
// pre-commit hook: generate mado.toml from .markdownlint.json, so mado and
// markdownlint check the same rules the same way. If the generated file
// differs from the repo's mado.toml, write it and fail so it gets reviewed and
// committed.
//
// Both tools publish a JSON schema of their config with defaults:
// markdownlint's ships in its npm package, and mado's for the pinned version
// is vendored next to this script as mado-<version>.schema.json. For each
// rule mado has:
//
// - it's on if markdownlint has the rule and .markdownlint.json turns it on
//   (explicitly, or through "default", which is true unless set)
// - each of mado's options for the rule is set explicitly, to the value in
//   .markdownlint.json or else markdownlint's default, because the two tools'
//   defaults differ (MD007's indent is 2 in markdownlint and 4 in mado)
//
// It fails rather than generate a config that would make the two disagree:
// an option value mado can't express, or an option set in .markdownlint.json
// that mado doesn't have.
//
// Only .markdownlint.json with rule IDs (MD013, not line-length) is read.
//

import { execFileSync } from "node:child_process";
import { existsSync, readFileSync, writeFileSync } from "node:fs";
import { createRequire } from "node:module";
import { dirname, join } from "node:path";
import { fileURLToPath } from "node:url";

const MARKDOWNLINT_CONFIG = ".markdownlint.json";
const MADO_CONFIG = "mado.toml";

// mado options whose markdownlint name isn't the mado name in snake_case.
const MARKDOWNLINT_OPTION_NAMES = {
  md024: { "allow-different-nesting": "siblings_only" },
};
// Options markdownlint has on every rule that don't change what's checked.
const IGNORED_MARKDOWNLINT_OPTIONS = new Set(["enabled", "severity"]);

const HERE = dirname(fileURLToPath(import.meta.url));

function fail(message) {
  console.error(`mado-config-up-to-date: ${message}`);
  process.exit(1);
}

function readJson(path) {
  return JSON.parse(readFileSync(path, "utf8"));
}

// mado: the pinned version and its config schema.
const madoVersion = execFileSync(
  "bash",
  [join(HERE, "install-mado.sh"), "--version"],
  { encoding: "utf8" },
).trim();
const madoSchemaPath = join(HERE, `mado-${madoVersion}.schema.json`);
if (!existsSync(madoSchemaPath)) {
  fail(`no vendored schema for mado ${madoVersion} at ${madoSchemaPath}; run bin/update-mado.sh ${madoVersion} in jetstream`);
}
const madoLint = readJson(madoSchemaPath).properties.lint.properties;
// The schema's list also has each rule's aliases and tags (line-length,
// headings); mado.toml only needs the IDs.
const madoRules = madoLint.rules.items.enum.filter((rule) => /^MD\d{3}$/.test(rule));

// markdownlint: its version and config schema, from the package
// markdownlint-cli2 depends on. The schema isn't in markdownlint's exports,
// so it's found relative to the package's entry point.
const requireFromCli2 = createRequire(
  createRequire(import.meta.url).resolve("markdownlint-cli2"),
);
const markdownlintDir = join(dirname(requireFromCli2.resolve("markdownlint")), "..");
const markdownlintVersion = readJson(join(markdownlintDir, "package.json")).version;
const markdownlintRules = readJson(
  join(markdownlintDir, "schema", "markdownlint-config-schema.json"),
).properties;

function markdownlintOptions(ruleId) {
  const schema = markdownlintRules[ruleId];
  if (schema === undefined) {
    return undefined;
  }
  const variants = schema.oneOf ?? schema.anyOf ?? [schema];
  return variants.find((variant) => variant.properties)?.properties ?? {};
}

// The repo's markdownlint config.
const config = existsSync(MARKDOWNLINT_CONFIG) ? readJson(MARKDOWNLINT_CONFIG) : {};
const ruleSettings = {};
for (const [key, value] of Object.entries(config)) {
  if (key === "default" || key === "$schema") {
    continue;
  }
  if (key === "extends") {
    if (value !== null) {
      fail(`${MARKDOWNLINT_CONFIG}: "extends" isn't supported; put the settings in ${MARKDOWNLINT_CONFIG}`);
    }
    continue;
  }
  if (!/^MD\d{3}$/i.test(key)) {
    fail(`${MARKDOWNLINT_CONFIG}: "${key}" isn't a rule ID; use rule IDs (MD013, not line-length)`);
  }
  ruleSettings[key.toUpperCase()] = value;
}
const onByDefault = config.default ?? true;

const enabled = [];
const notInMarkdownlint = [];
const tables = [];
for (const ruleId of madoRules) {
  const options = markdownlintOptions(ruleId);
  if (options === undefined) {
    notInMarkdownlint.push(ruleId);
    continue;
  }

  const setting = ruleSettings[ruleId];
  const isOn =
    setting === undefined ? onByDefault
      : typeof setting === "boolean" ? setting
        : setting.enabled ?? true;
  if (!isOn) {
    continue;
  }
  enabled.push(ruleId);

  const userOptions = typeof setting === "object" && setting !== null ? setting : {};
  const madoKey = ruleId.toLowerCase();
  const madoOptions = madoLint[madoKey]?.properties ?? {};
  const translated = new Set(IGNORED_MARKDOWNLINT_OPTIONS);
  const table = [];
  for (const [madoOption, madoOptionSchema] of Object.entries(madoOptions)) {
    const option = MARKDOWNLINT_OPTION_NAMES[madoKey]?.[madoOption] ?? madoOption.replaceAll("-", "_");
    if (!(option in options)) {
      fail(`mado ${madoVersion}'s ${ruleId} option ${madoOption} has no markdownlint ${markdownlintVersion} equivalent; add it to MARKDOWNLINT_OPTION_NAMES in jetstream's hooks/core/mado-config.mjs`);
    }
    translated.add(option);

    const isSet = option in userOptions;
    let value = isSet ? userOptions[option] : options[option].default;
    if (madoOptionSchema.enum) {
      const madoValue = typeof value === "string" ? value.replaceAll("_", "-") : value;
      if (!madoOptionSchema.enum.includes(madoValue)) {
        const choices = madoOptionSchema.enum.map((choice) => choice.replaceAll("-", "_")).join(", ");
        fail(`${ruleId} ${option} is ${JSON.stringify(value)}${isSet ? "" : " (markdownlint's default)"}, which mado ${madoVersion} can't express; set ${ruleId}.${option} in ${MARKDOWNLINT_CONFIG} to one of ${choices}, or turn ${ruleId} off`);
      }
      value = madoValue;
    }
    table.push(`${madoOption} = ${JSON.stringify(value)}`);
  }

  for (const [option, value] of Object.entries(userOptions)) {
    if (translated.has(option)) {
      continue;
    }
    if (JSON.stringify(value) !== JSON.stringify(options[option]?.default)) {
      fail(`${ruleId} ${option} is set in ${MARKDOWNLINT_CONFIG}, but mado ${madoVersion} has no such option, so the two linters would disagree; remove it or turn ${ruleId} off`);
    }
  }

  if (table.length > 0) {
    tables.push("", `[lint.${madoKey}]`, ...table);
  }
}

const lines = [
  `# Generated from ${MARKDOWNLINT_CONFIG} by jetstream's mado-config-up-to-date`,
  `# hook for mado ${madoVersion} and markdownlint ${markdownlintVersion}. Don't edit this`,
  `# file: change ${MARKDOWNLINT_CONFIG} and run pre-commit to regenerate it.`,
];
if (notInMarkdownlint.length > 0) {
  lines.push(`# Off because markdownlint doesn't have them: ${notInMarkdownlint.join(", ")}`);
}
lines.push("", "[lint]", "rules = [", ...enabled.map((ruleId) => `  "${ruleId}",`), "]", ...tables, "");
const generated = lines.join("\n");

const current = existsSync(MADO_CONFIG) ? readFileSync(MADO_CONFIG, "utf8") : undefined;
if (generated !== current) {
  writeFileSync(MADO_CONFIG, generated);
  fail(`${current === undefined ? "created" : "updated"} ${MADO_CONFIG} from ${MARKDOWNLINT_CONFIG}; review and commit it`);
}
