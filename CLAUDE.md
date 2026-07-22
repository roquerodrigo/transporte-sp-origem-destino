# transporte-sp-origem-destino

Desagrega a **Pesquisa Origem-Destino 2023 do Metrô-SP** do nível de zona (~527 zonas) para
o nível de **endereço**, na RMSP. Projeto irmão da rede: `roquerodrigo/transporte-sp`.

Pipeline Python (`pipeline/`, uv/ruff/pytest) + site Astro/Starlight (`site/`) com mapa
MapLibre lendo **PMTiles**.

---

## A ideia central (não é o que parece)

A Pesquisa OD **não** dá só demanda por zona. Os microdados trazem **coordenada real por
registro** — domicílio (`CO_DOM`), trabalho (`CO_TR1` com o setor econômico `SETOR1`),
escola, origem e destino de cada viagem — mais o peso de expansão (`FE_PESS`, `FE_VIA`).
Somados por zona, os pesos são os totais da zona. A desagregação **espalha** esses totais
sobre endereços reais do **CNEFE (IBGE 2022)**, respeitando a espécie do endereço, de forma
que a demanda caia em lotes e não em ruas. Os totais por zona são preservados exatamente; só
a granularidade do ponto é amostrada (`people_per_point`, default 50).

## Comandos

```bash
cd pipeline
uv run transporte-sp-od fetch      # baixa survey + 39 municípios do CNEFE (~460 MB)
uv run transporte-sp-od prepare    # CNEFE -> endereços indexados por zona (parquet)
uv run transporte-sp-od build      # desagrega -> data/dist/ (parquet + geojson + resumo)
uv run ruff check . && uv run pytest

# vector tiles para o mapa (tippecanoe):
cd ../data/dist && tippecanoe -o demanda.pmtiles -Z5 -z15 --drop-densest-as-needed \
  --extend-zooms-if-still-dropping --force \
  -L residencia:residencia.geojson -L trabalho:trabalho.geojson -L educacao:educacao.geojson
cp demanda.pmtiles resumo.json ../../site/public/dados/
```

## Onde mexer

| Quero mudar | Mexo em |
|---|---|
| URLs, CRS, os 39 municípios, `people_per_point` | `pipeline/src/transporte_sp_od/config.py` — **fonte única** |
| Como a pesquisa é lida | `sources/survey.py` |
| Como o CNEFE é lido/reprojetado | `sources/cnefe.py` |
| Atribuição de zona | `geo.py` (STRtree, CRS da pesquisa) |
| A desagregação em si | `build/disaggregate.py` |
| O mapa | `site/src/components/Mapa.astro` |

## Armadilhas (custaram tempo)

- **Os códigos IBGE do shapefile da pesquisa (`Municipios_2023`, coluna `CD_IBGE`) são
  furados** — mapeiam Itapevi para *Inúbia Paulista* e vários outros estão trocados. Os
  códigos corretos em `config.py` foram derivados **casando o nome** contra a listagem do
  FTP do CNEFE, não confiando no shapefile.
- **CRS**: a pesquisa é Córrego Alegre UTM 23S (`EPSG:22523`, metros); o CNEFE é WGS84.
  Reprojeta-se o CNEFE para o CRS da pesquisa na ingestão; zonas e pontos ficam todos em
  metros para o point-in-polygon.
- **`STRtree.query(pts, predicate="within")` retorna `[input_idx, tree_idx]`** — ponto
  `input[k]` está em polígono `tree[k]`. Trocar a ordem põe todo mundo na zona errada.
- **CNEFE não separa comércio/indústria/serviço** (tudo em espécie 06); separa só
  domicílio × estabelecimento × escola × saúde. A finalidade fina do emprego vem do
  `SETOR1` da pesquisa (usado só para o total por zona×setor), não do endereço.
- **PMTiles precisa de servidor com Range requests.** O `http.server` do Python não suporta
  bem; usar `astro preview` localmente. GitHub Pages suporta.
- **Os payloads crus não são commitados** (survey 198 MB, CNEFE 264 MB); os artefatos
  GeoJSON/Parquet também não. Só o PMTiles (7 MB) vai no repo (`site/public/dados/`), mais
  os manifests e o `resumo.json`. O CI não regenera o dado (download pesado demais); só faz
  lint/test do pipeline e build do site.

## Fora de escopo, de propósito

Modelar a densidade fina de estabelecimentos por CNAE (geocodificar CNPJ). A pesquisa já dá
o setor e a coordenada do trabalho; a separação comércio×indústria dentro do CNEFE fica
genérica, e isso é aceito — ver `site/src/content/docs/metodologia.mdx`.
