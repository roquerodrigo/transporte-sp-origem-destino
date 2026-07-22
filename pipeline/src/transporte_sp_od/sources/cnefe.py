"""CNEFE — Cadastro Nacional de Endereços para Fins Estatísticos, Censo 2022 (IBGE).

The "lot" surface the demand is scattered onto: every real address in the country, with a
field-collected coordinate (on the building, not the street centreline) and a species code
that separates dwellings from establishments, schools and health units. Downloaded per
municipality for the 39 of the RMSP; published in WGS84 and reprojected to the survey's CRS
on read.
"""

from __future__ import annotations

import csv
import io
import logging
import zipfile
from collections.abc import Iterator

from pyproj import Transformer

from transporte_sp_od import snapshot
from transporte_sp_od.config import CRS_SURVEY, CRS_WGS84, MUNICIPALITIES, settings

log = logging.getLogger(__name__)

SOURCE = "cnefe"
LICENCE = "IBGE — dados abertos"

_to_survey = Transformer.from_crs(CRS_WGS84, CRS_SURVEY, always_xy=True)


def _listing() -> dict[str, str]:
    """IBGE code -> the FTP filename (which carries the municipality name)."""
    html = snapshot.download(settings.cnefe_base_url).decode("utf-8", "replace")
    import re

    files = re.findall(r'href="(\d{7}_[^"]*\.zip)"', html)
    return {name.split("_", 1)[0]: name for name in files}


def fetch() -> None:
    """Download each RMSP municipality's CNEFE archive into the snapshot."""
    listing = _listing()
    faltando = [code for _, code in MUNICIPALITIES.values() if code not in listing]
    if faltando:
        raise RuntimeError(f"CNEFE FTP missing municipalities: {faltando}")
    for number, (name, code) in MUNICIPALITIES.items():
        filename = listing[code]
        payload = snapshot.download(settings.cnefe_base_url + filename)
        if not payload.startswith(b"PK"):
            raise RuntimeError(f"{name} did not return a zip")
        snapshot.write(SOURCE, f"{code}.zip", payload, settings.cnefe_base_url + filename, LICENCE)
        log.info("cnefe: %2d/39 %s (%.0f MB)", number, name, len(payload) / 1e6)


def _rows(code: str) -> Iterator[dict]:
    directory = snapshot.latest_snapshot(SOURCE)
    with zipfile.ZipFile(directory / f"{code}.zip") as archive:
        name = next(n for n in archive.namelist() if n.lower().endswith(".csv"))
        with archive.open(name) as handle:
            yield from csv.DictReader(io.TextIOWrapper(handle, encoding="utf-8"), delimiter=";")


def addresses(code: str) -> Iterator[tuple[float, float, str, str]]:
    """``(x, y, species, sector)`` in the survey CRS for one municipality's addresses.

    ``sector`` is the census sector code; ``species`` is COD_ESPECIE. Rows without a usable
    coordinate are skipped — a handful per municipality.
    """
    for row in _rows(code):
        lat, lon = row.get("LATITUDE"), row.get("LONGITUDE")
        if not lat or not lon:
            continue
        try:
            x, y = _to_survey.transform(float(lon), float(lat))
        except (ValueError, OverflowError):
            continue
        yield x, y, row.get("COD_ESPECIE", ""), row.get("COD_SETOR", "")
