# transporte-sp-origem-destino

Mapeia a **Pesquisa Origem-Destino 2023 do Metrô de São Paulo** nas **coordenadas reais** de
cada registro, na Região Metropolitana de São Paulo.

Os microdados da pesquisa geolocalizam cada ponto — domicílio, trabalho (com o setor
econômico), escola, e a origem e o destino de cada viagem — mais o fator de expansão de cada
registro. O projeto usa essas coordenadas diretamente: a **demanda** (onde as pessoas moram,
trabalham e estudam) vira um mapa de calor ponderado, e as **viagens** viram pares
origem→destino reais, por motivo, disponíveis para download. Nada é sorteado nem agregado por
zona.

Repositório da rede (projeto irmão): `roquerodrigo/transporte-sp`.
