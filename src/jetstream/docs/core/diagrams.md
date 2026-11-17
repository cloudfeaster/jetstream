# Diagrams

Diagrams are written in [D2](https://d2lang.com/) and compiled to SVG, and both are committed:

- a source at `<dir>/images/d2/<name>.d2` compiles to `<dir>/images/<name>.svg`;
- `run-d2-compile.sh` compiles every source, in D2's sketch style;
- the `check-svg` hook fails if an SVG in an `images/` folder has no D2 source, or isn't what its source compiles to. SVGs anywhere else aren't checked.

After changing a `.d2` file:

```bash
run-d2-compile.sh
```

Then commit the source and the SVG together.
