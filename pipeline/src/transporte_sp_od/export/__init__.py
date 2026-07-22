"""Writing the disaggregated demand out.

Two forms of each point layer: a Parquet with the survey-CRS coordinates for analysis, and
a simplified GeoJSON in WGS84 for the map. The map file is deliberately thinned — hundreds
of thousands of points — by rounding coordinates and dropping to the fields a dot needs.
"""

from __future__ import annotations

import json
import logging

import pyarrow as pa
import pyarrow.parquet as pq
from pyproj import Transformer

from transporte_sp_od.config import CRS_SURVEY, CRS_WGS84, settings

log = logging.getLogger(__name__)

_to_wgs = Transformer.from_crs(CRS_SURVEY, CRS_WGS84, always_xy=True)


def write_all(layers: dict[str, list[dict]], summary: dict) -> None:
    settings.dist_dir.mkdir(parents=True, exist_ok=True)
    for name, points in layers.items():
        _write_parquet(name, points)
        _write_geojson(name, points)
    _write(settings.dist_dir / "resumo.json", summary)


def _write(path, payload) -> None:
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n")
    log.info("wrote %s (%.1f KB)", path.name, path.stat().st_size / 1024)


def _write_parquet(name: str, points: list[dict]) -> None:
    if not points:
        return
    columns = sorted({key for point in points for key in point})
    table = pa.table({col: [point.get(col) for point in points] for col in columns})
    pq.write_table(table, settings.dist_dir / f"{name}.parquet")


def _write_geojson(name: str, points: list[dict]) -> None:
    features = []
    for point in points:
        lon, lat = _to_wgs.transform(point["x"], point["y"])
        properties = {k: v for k, v in point.items() if k not in ("x", "y")}
        features.append(
            {
                "type": "Feature",
                "geometry": {"type": "Point", "coordinates": [round(lon, 6), round(lat, 6)]},
                "properties": properties,
            }
        )
    _write(
        settings.dist_dir / f"{name}.geojson",
        {"type": "FeatureCollection", "features": features},
    )
