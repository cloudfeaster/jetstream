#!/usr/bin/env node
//
// pre-commit hook: run markdownlint-cli2 on the Markdown files pre-commit
// passes in. markdownlint-cli2 reads its config (.markdownlint.json and
// friends) from the repo being checked.
//
// markdownlint-cli2 treats its arguments as globs, so a filename containing
// glob characters could match other files or none. A ":" prefix makes an
// argument a literal path, so every filename gets one. Options (and the value
// after --config or --configPointer) pass through unchanged.
//

import { main } from "markdownlint-cli2";

const OPTIONS_WITH_VALUES = new Set(["--config", "--configPointer"]);

const argv = [];
let optionValueNext = false;
for (const arg of process.argv.slice(2)) {
  if (optionValueNext || arg.startsWith("-")) {
    argv.push(arg);
    optionValueNext = OPTIONS_WITH_VALUES.has(arg);
  } else {
    argv.push(`:${arg}`);
  }
}

try {
  process.exitCode = await main({
    argv,
    logMessage: console.log,
    logError: console.error,
    allowStdin: false,
  });
} catch (error) {
  console.error(error);
  process.exitCode = 2;
}
