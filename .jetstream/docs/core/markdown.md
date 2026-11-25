<!-- Written by `jetstream sync` from cloudfeaster/jetstream's docs; don't edit. -->

# Markdown

The `mado` hook lints every Markdown file with [mado](https://github.com/akiomik/mado), which implements markdownlint's rules. The rules it checks are listed in `mado.toml`, which jetstream owns.

Two rules are deliberately left out:

- **line length (MD013)**: write each paragraph on one line, or break lines where it reads well; long lines are fine in prose and tables;
- **inline HTML (MD033)**: badge rows, centered images and the like need it.

Conventions the rules enforce, among others:

- one `#` heading, on the file's first line, except in a page whose front matter has a `title`, such as a site's;
- headings increase one level at a time;
- a blank line around headings, lists and fenced code blocks;
- every fenced code block names its language (`bash`, `text`, ...);
- the file ends with exactly one newline.

To lint by hand:

```bash
run-mado.sh
```
