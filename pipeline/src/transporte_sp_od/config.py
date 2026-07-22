"""Single source of truth: source, CRS, paths, the motive vocabulary.

Every scalar knob can be overridden from the environment or a ``.env`` at the repo root — the
env var name is shown next to each field.
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


# The OD survey publishes coordinates in Córrego Alegre / UTM zone 23S (metres); everything is
# reprojected to WGS84 only on export, for the map and the downloads.
CRS_SURVEY = "EPSG:22523"  # Córrego Alegre UTM 23S (metres)
CRS_WGS84 = "EPSG:4326"


@dataclass(frozen=True)
class Settings:
    data_dir: Path = _env("TSPOD_DATA_DIR", PROJECT_ROOT / "data", Path)

    od_zip_url: str = env_str(
        "TSPOD_OD_ZIP_URL",
        "https://transparencia.metrosp.com.br/sites/default/files/Site_190225_PesquisaOD2023.zip",
    )

    user_agent: str = env_str(
        "TSPOD_USER_AGENT",
        "transporte-sp-od/0.1 (+https://github.com/roquerodrigo/transporte-sp-origem-destino)",
    )
    http_timeout: float = env_float("TSPOD_HTTP_TIMEOUT", 600.0)
    http_retries: int = env_int("TSPOD_HTTP_RETRIES", 3)

    @property
    def raw_dir(self) -> Path:
        return self.data_dir / "raw"

    @property
    def dist_dir(self) -> Path:
        return self.data_dir / "dist"


settings = Settings()


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
