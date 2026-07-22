# transporte-sp-origem-destino

Desagrega a **Pesquisa Origem-Destino 2023 do Metrô de São Paulo** do nível de zona
(~527 zonas) para o nível de **endereço**, na Região Metropolitana de São Paulo.

Os microdados da pesquisa já trazem coordenada real de cada ponto de viagem — domicílio,
trabalho (com o setor econômico), escola, origem e destino — mais o fator de expansão de
cada registro. O projeto materializa essa demanda em pontos espalhados sobre endereços
reais do **CNEFE (IBGE 2022)**, respeitando a espécie do endereço (domicílio, estabelecimento,
escola, saúde), para que a densidade caia em lotes e não em ruas.

Repositório da rede (projeto irmão): `roquerodrigo/transporte-sp`.
