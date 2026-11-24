// @ts-check
import { defineConfig } from "astro/config";

// The site's URL on GitHub Pages. With a custom domain, site is the domain
// and base goes.
export default defineConfig({
  site: "https://cloudfeaster.github.io",
  base: "/$name",
  trailingSlash: "always", // GitHub Pages serves a page at /page/
});
