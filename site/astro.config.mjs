import { readFileSync } from "node:fs";

import { defineConfig } from "astro/config";
import starlight from "@astrojs/starlight";
import blackTheme from "starlight-theme-black";

// GitHub Pages project URL; both overridable so a fork publishes under its own account.
const site = process.env.SITE_URL ?? "https://www.rodrigoroque.dev";
const base = process.env.BASE_PATH ?? "/transporte-sp-origem-destino";

export default defineConfig({
  site,
  base,
  trailingSlash: "always",
  integrations: [
    starlight({
      plugins: [
        blackTheme({
          navLinks: [
            { label: "Mapa da demanda", slug: "mapa" },
            { label: "Mapa de viagens", slug: "viagens" },
            { label: "Dados", slug: "dados" },
            { label: "Metodologia", slug: "metodologia" },
            { label: "Fontes", slug: "fontes" },
          ],
          // The theme offers "open this page in ChatGPT/Claude" buttons; they send the page
          // to a third party and add nothing here.
          docs: { showMarkdownActions: false },
        }),
      ],
      title: "Demanda OD-SP",
      description:
        "A Pesquisa Origem-Destino 2023 do Metrô-SP mapeada nas coordenadas reais de cada registro.",
      defaultLocale: "root",
      locales: { root: { label: "Português", lang: "pt-BR" } },
      social: [
        {
          icon: "github",
          label: "GitHub",
          href: "https://github.com/roquerodrigo/transporte-sp-origem-destino",
        },
      ],
      customCss: ["./src/styles/custom.css", "./src/styles/tables.css"],
      // Injected here rather than from a `Head` override: themes routinely override `Head`,
      // and whichever override loses simply does not render. Starlight injects the SVG favicon
      // on its own; the raster fallbacks and the iOS touch icon are added here, base-prefixed.
      head: [
        {
          tag: "script",
          content: readFileSync(
            new URL("./src/scripts/wrap-tables.js", import.meta.url),
            "utf8",
          ),
        },
        { tag: "link", attrs: { rel: "icon", href: `${base}/favicon.ico`, sizes: "48x48" } },
        {
          tag: "link",
          attrs: { rel: "icon", type: "image/png", sizes: "32x32", href: `${base}/favicon-32.png` },
        },
        {
          tag: "link",
          attrs: { rel: "icon", type: "image/png", sizes: "16x16", href: `${base}/favicon-16.png` },
        },
        {
          tag: "link",
          attrs: { rel: "apple-touch-icon", sizes: "180x180", href: `${base}/apple-touch-icon.png` },
        },
        { tag: "meta", attrs: { name: "theme-color", content: "#0f172a" } },
      ],
      sidebar: [
        { label: "Mapa da demanda", link: "/mapa/" },
        { label: "Mapa de viagens", link: "/viagens/" },
        { label: "Dados", link: "/dados/" },
        { label: "Metodologia", link: "/metodologia/" },
        { label: "Fontes", link: "/fontes/" },
      ],
    }),
  ],
});
