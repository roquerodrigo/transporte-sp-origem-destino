"""Single source of truth: sources, CRS, the disaggregation knobs, paths.

Every scalar knob can be overridden from the environment or a ``.env`` at the repo root —
the env var name is shown next to each field. Non-scalar knobs (the vocabularies, the
municipality table) stay as code constants below.
"""

from __future__ import annotations

import os
from dataclasses import dataclass, field
from pathlib import Path

from dotenv import load_dotenv

PROJECT_ROOT = Path(__file__).resolve().parents[3]
load_dotenv(PROJECT_ROOT / ".env")


def _env(name: str, default, cast):
    def factory(n=name, d=default, c=cast):
        raw = os.environ.get(n)
        return d if raw is None or raw == "" else c(raw)

    return field(default_factory=factory)


def env_str(name: str, default: str):
    return _env(name, default, str)


def env_int(name: str, default: int):
    return _env(name, default, int)


def env_float(name: str, default: float):
    return _env(name, default, float)


# The OD survey publishes coordinates in Córrego Alegre / UTM zone 23S; CNEFE publishes in
# WGS84 lat/lon. The pipeline works in the survey's projected metres — zones and survey
# points are already there, so only CNEFE has to be reprojected in.
CRS_SURVEY = "EPSG:22523"  # Córrego Alegre UTM 23S (metres)
CRS_WGS84 = "EPSG:4326"


@dataclass(frozen=True)
class Settings:
    data_dir: Path = _env("TSPOD_DATA_DIR", PROJECT_ROOT / "data", Path)

    od_zip_url: str = env_str(
        "TSPOD_OD_ZIP_URL",
        "https://transparencia.metrosp.com.br/sites/default/files/Site_190225_PesquisaOD2023.zip",
    )
    cnefe_base_url: str = env_str(
        "TSPOD_CNEFE_BASE_URL",
        "https://ftp.ibge.gov.br/Cadastro_Nacional_de_Enderecos_para_Fins_Estatisticos/"
        "Censo_Demografico_2022/Arquivos_CNEFE/CSV/Municipio/35_SP/",
    )

    user_agent: str = env_str(
        "TSPOD_USER_AGENT",
        "transporte-sp-od/0.1 (+https://github.com/roquerodrigo/transporte-sp-origem-destino)",
    )
    http_timeout: float = env_float("TSPOD_HTTP_TIMEOUT", 600.0)
    http_retries: int = env_int("TSPOD_HTTP_RETRIES", 3)

    # One materialised point stands for this many real people / jobs / trips. The survey
    # totals are preserved exactly; only the granularity of the dots is sampled. 50 turns
    # 21 M residents into ~420 k mappable points.
    people_per_point: int = env_int("TSPOD_PEOPLE_PER_POINT", 50)

    # Number of address-level OD arcs (feixes) to materialise. Each arc links two real
    # addresses and carries a share of its OD cell's trips; the total is preserved exactly.
    # A downstream import expects roughly this many rows.
    flows_target: int = env_int("TSPOD_FLOWS_TARGET", 100_000)

    @property
    def raw_dir(self) -> Path:
        return self.data_dir / "raw"

    @property
    def dist_dir(self) -> Path:
        return self.data_dir / "dist"


settings = Settings()


# The 39 municipalities of the RMSP, keyed by the survey's own municipality number, with the
# IBGE code used to fetch each municipality's CNEFE file. Derived by matching the municipality
# names against the CNEFE FTP listing — the CD_IBGE column of the survey's own Municipios
# shapefile is unreliable (it maps Itapevi to Inúbia Paulista, and several others are shifted).
MUNICIPALITIES: dict[int, tuple[str, str]] = {
    1: ("Arujá", "3503901"),
    2: ("Barueri", "3505708"),
    3: ("Biritiba-Mirim", "3506607"),
    4: ("Caieiras", "3509007"),
    5: ("Cajamar", "3509205"),
    6: ("Carapicuíba", "3510609"),
    7: ("Cotia", "3513009"),
    8: ("Diadema", "3513801"),
    9: ("Embu das Artes", "3515004"),
    10: ("Embu-Guaçu", "3515103"),
    11: ("Ferraz de Vasconcelos", "3515707"),
    12: ("Francisco Morato", "3516309"),
    13: ("Franco da Rocha", "3516408"),
    14: ("Guararema", "3518305"),
    15: ("Guarulhos", "3518800"),
    16: ("Itapecerica da Serra", "3522208"),
    17: ("Itapevi", "3522505"),
    18: ("Itaquaquecetuba", "3523107"),
    19: ("Jandira", "3525003"),
    20: ("Juquitiba", "3526209"),
    21: ("Mairiporã", "3528502"),
    22: ("Mauá", "3529401"),
    23: ("Mogi das Cruzes", "3530607"),
    24: ("Osasco", "3534401"),
    25: ("Pirapora do Bom Jesus", "3539103"),
    26: ("Poá", "3539806"),
    27: ("Ribeirão Pires", "3543303"),
    28: ("Rio Grande da Serra", "3544103"),
    29: ("Salesópolis", "3545001"),
    30: ("Santa Isabel", "3546801"),
    31: ("Santana de Parnaíba", "3547304"),
    32: ("Santo André", "3547809"),
    33: ("São Bernardo do Campo", "3548708"),
    34: ("São Caetano do Sul", "3548807"),
    35: ("São Lourenço da Serra", "3549953"),
    36: ("São Paulo", "3550308"),
    37: ("Suzano", "3552502"),
    38: ("Taboão da Serra", "3552809"),
    39: ("Vargem Grande Paulista", "3556453"),
}

# Trip motive (MOTIVO / MOTIVO_O / MOTIVO_D in the microdata).
MOTIVE: dict[int, str] = {
    1: "Trabalho Indústria",
    2: "Trabalho Comércio",
    3: "Trabalho Serviços",
    4: "Educação",
    5: "Compras",
    6: "Saúde",
    7: "Lazer",
    8: "Residência",
    9: "Procurar Emprego",
    10: "Assuntos Pessoais",
    11: "Refeição",
}

# Economic sector of the workplace (SETOR1 / SETOR2).
SECTOR: dict[int, str] = {
    1: "Agropecuária",
    2: "Construção Civil",
    3: "Indústria",
    4: "Comércio",
    5: "Serviço de Transporte de Carga",
    6: "Serviço de Transporte de Passageiros",
    7: "Serviço Creditício-financeiro",
    8: "Serviço Pessoal",
    9: "Serviço de Alimentação",
    10: "Serviço de Saúde",
    11: "Serviço de Educação",
    12: "Serviço Especializado",
    13: "Serviço de Administração Pública",
    14: "Outros Serviços",
}

# CNEFE address species (COD_ESPECIE) — the "lot" surface the demand is scattered onto.
CNEFE_SPECIES: dict[str, str] = {
    "1": "domicílio particular",
    "2": "domicílio coletivo",
    "3": "estabelecimento agropecuário",
    "4": "estabelecimento de ensino",
    "5": "estabelecimento de saúde",
    "6": "estabelecimento de outras finalidades",
    "7": "edificação em construção",
    "8": "estabelecimento religioso",
}

# Which CNEFE species hosts each kind of trip end. Origins (and any "home" end) land on
# dwellings; education and health land on their own establishments; every other work/service
# end lands on a generic establishment. This is the residential/non-residential split the
# survey needs, for free — CNEFE cannot separate commerce from industry within species 6.
RESIDENTIAL_SPECIES = {"1", "2"}
EDUCATION_SPECIES = {"4"}
HEALTH_SPECIES = {"5"}
ESTABLISHMENT_SPECIES = {"3", "4", "5", "6", "8"}
