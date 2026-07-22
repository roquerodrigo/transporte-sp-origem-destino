# transporte-sp-origem-destino

Mapeia a **Pesquisa Origem-Destino 2023 do Metrô-SP** nas **coordenadas reais** de cada
registro, na RMSP. Projeto irmão da rede: `roquerodrigo/transporte-sp`.

Pipeline Python (`pipeline/`, uv/ruff/pytest) + site Astro/Starlight (`site/`) com mapas
MapLibre lendo **PMTiles**.

---

## A ideia central

A Pesquisa OD **geolocaliza cada ponto** de cada registro — domicílio (`CO_DOM`), trabalho
(`CO_TR1` com o setor `SETOR1`), escola (`CO_ESC`), origem/destino de cada viagem (`CO_O`,
`CO_D`) — mais o peso de expansão (`FE_PESS` p/ pessoas, `FE_VIA` p/ viagens). O projeto usa
**essas coordenadas diretamente**: nada de CNEFE, nada de sorteio de endereço, nada de
agregação por zona. Só entram os registros **geolocalizados** (o resto não tem coordenada).

- **Demanda** (`build/demand.py`) — cada pessoa vira até 3 pontos (casa/trabalho/escola) na
  coordenada real, peso `FE_PESS`; o mapa desenha um **heatmap ponderado**. Totais = população,
  empregos e estudantes da pesquisa (21,2 M / 10,5 M / 5,2 M).
- **Viagens** (`build/flows.py`) — cada viagem geolocalizada vira uma linha O→D real, motivo
  `MOTIVO_D`, peso `FE_VIA` (~112,9k viagens, 35,7 M/dia). O par O→D é o **observado**.

## Comandos

```bash
cd pipeline
uv run transporte-sp-od fetch      # baixa o survey (snapshot datado)
uv run transporte-sp-od build      # demanda (coords reais) -> data/dist/ (geojson + resumo)
uv run transporte-sp-od flows      # viagens reais O→D -> data/dist/fluxos.{csv,parquet} + pontos p/ mapa (geojson)
uv run ruff check . && uv run pytest

# vector tiles para os mapas (tippecanoe):
# demanda é heatmap -> mantém TODOS os pontos (-r1), não pode dropar senão distorce a densidade
cd ../data/dist && tippecanoe -o demanda.pmtiles -Z5 -z15 -r1 --no-tile-size-limit --force \
  -L residencia:residencia.geojson -L trabalho:trabalho.geojson -L educacao:educacao.geojson
tippecanoe -o fluxos.pmtiles -Z5 -z15 --drop-densest-as-needed --extend-zooms-if-still-dropping --force \
  -L origens:origens.geojson -L dest_casa:dest_casa.geojson -L dest_trabalho:dest_trabalho.geojson \
  -L dest_educacao:dest_educacao.geojson -L dest_saude:dest_saude.geojson -L dest_outros:dest_outros.geojson
cp demanda.pmtiles fluxos.pmtiles resumo.json ../../site/public/dados/
```

## Onde mexer

| Quero mudar | Mexo em |
|---|---|
| URL do survey, CRS, vocabulário de motivos | `pipeline/src/transporte_sp_od/config.py` — **fonte única** |
| Como a pesquisa é lida (campos, `people()`) | `sources/survey.py` |
| A demanda (casa/trabalho/escola por coord real) | `build/demand.py` |
| As viagens observadas O→D | `build/flows.py` (uma linha por registro geolocalizado) |
| Agrupamento de motivos no mapa de viagens | `export.DEST_CATEGORY` (casa/trabalho/educação/saúde/outros) |
| O mapa de demanda (heatmap) | `site/src/components/Mapa.astro` |
| O mapa de viagens (pontos) | `site/src/components/MapaFluxos.astro` |
| A página de download dos dados | `site/src/content/docs/dados.mdx` + `components/Downloads.astro` |

## Armadilhas (custaram tempo)

- **`MOTIVO` vs `MOTIVO_D`:** `MOTIVO` não tem o motivo 8 (casa) — dobra o retorno no propósito
  da ida; `MOTIVO_D` é o motivo **literal do destino** (metade das viagens é volta pra casa). As
  viagens usam `MOTIVO_D`.
- **CRS:** a pesquisa é Córrego Alegre UTM 23S (`EPSG:22523`, metros); tudo é processado em
  metros e reprojetado para WGS84 só na exportação (`export._to_wgs`).
- **Heatmap não pode dropar pontos:** o `tippecanoe` da demanda usa `-r1 --no-tile-size-limit`
  (mantém todos os ~135k pontos em todo zoom); `--drop-densest-as-needed` distorceria a densidade.
- **PMTiles atrás do Cloudflare:** o range request quebra (tira `accept-ranges`, gzipa). Os dois
  mapas leem o arquivo inteiro via `BufferSource` (um GET só). Localmente usar `astro preview`.
- **Só registros geolocalizados entram:** ~112,9k de ~143k viagens; os sem coordenada ficam de
  fora. Os totais somam ao esperado porque o peso expande o que sobra.
- **Payloads crus e artefatos não commitados** (survey ~198 MB; geojson/parquet intermediários).
  Vão no repo, em `site/public/dados/`: os PMTiles dos dois mapas, os `fluxos.{csv,parquet}`
  (~113k viagens) que a página **Dados** disponibiliza, os manifests e o `resumo.json`. O CI só
  faz lint/test do pipeline e build do site — não regenera o dado.
