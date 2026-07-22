"""The Metrô-SP Origin-Destination 2023 survey — the spine of the project.

Unlike its zone-aggregated result tables, the microdata carries a real coordinate for every
trip end: the dwelling (``CO_DOM``), the workplace (``CO_TR1`` with its economic ``SETOR1``),
the school, and each trip's origin and destination. Each record also carries an expansion
weight (``FE_PESS`` for people, ``FE_VIA`` for trips) saying how many real people or trips it
stands for. Disaggregation turns those weighted points into scattered address-level points.

Coordinates are in Córrego Alegre / UTM 23S (metres), the CRS of the zone shapefile too.
"""

from __future__ import annotations

import logging
import zipfile
from collections.abc import Iterator
from pathlib import Path

import shapefile
from dbfread import DBF

from transporte_sp_od import snapshot

log = logging.getLogger(__name__)

SOURCE = "od_survey"
ARCHIVE = "od2023.zip"

_INNER = "Site_190225/"
_DBF = _INNER + "Banco2023_divulgacao_190225.dbf"
_ZONES = _INNER + "002_Site Metro Mapas_190225/Shape/Zonas_2023"
_ZONE_PARTS = (".shp", ".shx", ".dbf", ".prj")

# The microdata columns the disaggregation actually reads, so the DBF is not carried in full.
_FIELDS = (
    "ID_DOM ID_PESS F_PESS FE_PESS FE_VIA "
    "ZONA MUNI_DOM CO_DOM_X CO_DOM_Y "
    "ESTUDA ZONA_ESC MUNIESC CO_ESC_X CO_ESC_Y "
    "SETOR1 ZONATRA1 MUNITRA1 CO_TR1_X CO_TR1_Y "
    "N_VIAG ZONA_O CO_O_X CO_O_Y ZONA_D CO_D_X CO_D_Y MOTIVO MODOPRIN"
).split()


def _extracted() -> Path:
    """Extract the DBF and zone shapefile once, next to the raw archive."""
    out = snapshot.latest_snapshot(SOURCE) / "_extracted"
    if (out / _DBF).exists():
        return out
    out.mkdir(parents=True, exist_ok=True)
    wanted = [_DBF, *(_ZONES + part for part in _ZONE_PARTS)]
    with zipfile.ZipFile(snapshot.path(SOURCE, ARCHIVE)) as archive:
        for name in wanted:
            target = out / name
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_bytes(archive.read(name))
    log.info("%s: extracted microdata and zone shapefile", SOURCE)
    return out


def zones() -> list[dict]:
    """Each OD zone: number, municipality, district, and its polygon (rings of [x, y])."""
    reader = shapefile.Reader(str(_extracted() / _ZONES), encoding="latin-1")
    columns = [f[0] for f in reader.fields[1:]]
    out = []
    for record, shape in zip(reader.records(), reader.shapes(), strict=True):
        row = dict(zip(columns, record, strict=True))
        out.append(
            {
                "zone": int(row["NumeroZona"]),
                "municipality": int(row["NumeroMuni"]),
                "municipality_name": row["NomeMunici"],
                "district": row.get("NomeDistri"),
                "rings": _rings(shape),
            }
        )
    log.info("%s: %d zones", SOURCE, len(out))
    return out


def _rings(shape) -> list[list[list[float]]]:
    points = [[float(x), float(y)] for x, y in shape.points]
    starts = list(shape.parts) + [len(points)]
    return [points[starts[i] : starts[i + 1]] for i in range(len(shape.parts))]


def records() -> Iterator[dict]:
    """Every microdata row, narrowed to the fields the disaggregation reads."""
    dbf = DBF(str(_extracted() / _DBF), encoding="latin-1", load=False)
    for row in dbf:
        yield {field: row.get(field) for field in _FIELDS}


def people() -> Iterator[dict]:
    """One record per person (the first-person-record flag), with home, work and school."""
    for row in records():
        if row.get("F_PESS") == 1:
            yield row
