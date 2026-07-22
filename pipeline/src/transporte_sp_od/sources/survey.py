"""The Metrô-SP Origin-Destination 2023 survey — the spine of the project.

Unlike its zone-aggregated result tables, the microdata carries a real coordinate for every
trip end: the dwelling (``CO_DOM``), the workplace (``CO_TR1`` with its economic ``SETOR1``),
the school, and each trip's origin and destination. Each record also carries an expansion
weight (``FE_PESS`` for people, ``FE_VIA`` for trips) saying how many real people or trips it
stands for — the demand and the flows are built from those real weighted points.

Coordinates are in Córrego Alegre / UTM 23S (metres).
"""

from __future__ import annotations

import logging
import zipfile
from collections.abc import Iterator
from pathlib import Path

from dbfread import DBF

from transporte_sp_od import snapshot

log = logging.getLogger(__name__)

SOURCE = "od_survey"
ARCHIVE = "od2023.zip"

_DBF = "Site_190225/Banco2023_divulgacao_190225.dbf"

# The microdata columns the build actually reads, so the DBF is not carried in full.
_FIELDS = (
    "ID_DOM ID_PESS F_PESS FE_PESS FE_VIA "
    "ZONA MUNI_DOM CO_DOM_X CO_DOM_Y "
    "ESTUDA ZONA_ESC MUNIESC CO_ESC_X CO_ESC_Y "
    "SETOR1 ZONATRA1 MUNITRA1 CO_TR1_X CO_TR1_Y "
    "N_VIAG ZONA_O CO_O_X CO_O_Y ZONA_D CO_D_X CO_D_Y MOTIVO MOTIVO_D MODOPRIN"
).split()


def _extracted() -> Path:
    """Extract the microdata DBF once, next to the raw archive."""
    out = snapshot.latest_snapshot(SOURCE) / "_extracted"
    target = out / _DBF
    if target.exists():
        return out
    target.parent.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(snapshot.path(SOURCE, ARCHIVE)) as archive:
        target.write_bytes(archive.read(_DBF))
    log.info("%s: extracted microdata", SOURCE)
    return out


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
