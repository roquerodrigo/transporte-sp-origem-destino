"""Turn the raw CNEFE archives into one indexed table of candidate addresses.

Reading, reprojecting and zone-assigning ~8 million addresses is the slow part, so it runs
once and its result — ``data/dist/enderecos.parquet`` (zone, species, x, y) — is what the
disaggregation samples from. Only the species groups the demand actually lands on are kept
(dwellings, establishments, schools, health units); construction sites and the like are
dropped.
"""

from __future__ import annotations

import logging

import numpy as np
import pyarrow as pa
import pyarrow.parquet as pq

from transporte_sp_od.config import (
    ESTABLISHMENT_SPECIES,
    MUNICIPALITIES,
    RESIDENTIAL_SPECIES,
    settings,
)
from transporte_sp_od.geo import ZoneIndex
from transporte_sp_od.sources import cnefe, survey

log = logging.getLogger(__name__)

KEEP_SPECIES = RESIDENTIAL_SPECIES | ESTABLISHMENT_SPECIES

SCHEMA = pa.schema(
    [
        ("zone", pa.int32()),
        ("species", pa.string()),
        ("x", pa.float64()),
        ("y", pa.float64()),
    ]
)


def run() -> None:
    index = ZoneIndex(survey.zones())
    settings.dist_dir.mkdir(parents=True, exist_ok=True)
    target = settings.dist_dir / "enderecos.parquet"

    kept = dropped = 0
    with pq.ParquetWriter(target, SCHEMA) as writer:
        for number, (name, code) in MUNICIPALITIES.items():
            xs, ys, species = [], [], []
            for x, y, esp, _sector in cnefe.addresses(code):
                if esp not in KEEP_SPECIES:
                    continue
                xs.append(x)
                ys.append(y)
                species.append(esp)
            if not xs:
                continue
            zones = index.zones_of(np.asarray(xs), np.asarray(ys))
            batch_zone, batch_species, batch_x, batch_y = [], [], [], []
            for zone, esp, x, y in zip(zones, species, xs, ys, strict=True):
                if zone is None:
                    dropped += 1
                    continue
                batch_zone.append(zone)
                batch_species.append(esp)
                batch_x.append(x)
                batch_y.append(y)
            writer.write_table(
                pa.table(
                    {
                        "zone": pa.array(batch_zone, pa.int32()),
                        "species": pa.array(batch_species, pa.string()),
                        "x": pa.array(batch_x, pa.float64()),
                        "y": pa.array(batch_y, pa.float64()),
                    }
                )
            )
            kept += len(batch_zone)
            log.info("prepare: %2d/39 %-24s %8d addresses", number, name, len(batch_zone))
    log.info("prepare: %d addresses kept, %d outside every zone → %s", kept, dropped, target.name)
