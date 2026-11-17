<!-- Written by `jetstream sync` from cloudfeaster/jetstream's docs; don't edit. -->

# JSON

The `json-lint` hook checks that every tracked `*.json` file is valid JSON and is formatted as `jq` formats it (2-space indent). To format a file:

```bash
jq . file.json > file.json.new && mv file.json.new file.json
```

`.jsonlintignore`, which jetstream owns, lists the files it skips, as git pathspec globs. It skips `.vscode` folders, because VS Code settings files are JSONC (they allow comments).
