import { defineConfig } from "astro/config";
import starlight from "@astrojs/starlight";

// GitHub Pages project URL; both overridable so a fork publishes under its own account.
const site = process.env.SITE_URL ?? "https://www.rodrigoroque.dev";
const base = process.env.BASE_PATH ?? "/transporte-sp-origem-destino";

export default defineConfig({
  site,
  base,
  trailingSlash: "always",
  integrations: [
    starlight({
      title: "Demanda OD-SP",
      description:
        "A Pesquisa Origem-Destino 2023 do Metrô-SP desagregada da zona para o endereço.",
      defaultLocale: "root",
      locales: { root: { label: "Português", lang: "pt-BR" } },
      social: [
        {
          icon: "github",
          label: "GitHub",
          href: "https://github.com/roquerodrigo/transporte-sp-origem-destino",
        },
      ],
      customCss: ["./src/styles/custom.css"],
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
