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

# The map toggles destinations by broad purpose; every other motive falls under "outros".
DEST_CATEGORY = {
    8: "casa",
    1: "trabalho",
    2: "trabalho",
    3: "trabalho",
    4: "educacao",
    6: "saude",
}


def write_all(layers: dict[str, list[dict]], summary: dict) -> None:
    settings.dist_dir.mkdir(parents=True, exist_ok=True)
    for name, points in layers.items():
        _write_parquet(name, points)
        _write_geojson(name, points)
    _write(settings.dist_dir / "resumo.json", summary)


def _write(path, payload) -> None:
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n")
    log.info("wrote %s (%.1f KB)", path.name, path.stat().st_size / 1024)


def write_flows(arcs: list[dict], summary: dict) -> None:
    """The observed OD trips, as Parquet and CSV.

    Each row is one trip: its real origin and destination in WGS84, the OD zones, the
    destination motive and the daily trips it stands for. Parquet (zstd) is the compact analyst
    form; CSV the universal one. Coordinates come in from the survey CRS, are reprojected once
    in a single batch, and are rounded to five decimals (~1 m).
    """
    settings.dist_dir.mkdir(parents=True, exist_ok=True)

    import numpy as np

    def wgs(key_x: str, key_y: str) -> tuple[list[float], list[float]]:
        lon, lat = _to_wgs.transform(
            np.fromiter((a[key_x] for a in arcs), dtype=float),
            np.fromiter((a[key_y] for a in arcs), dtype=float),
        )
        return np.round(lon, 5).tolist(), np.round(lat, 5).tolist()

    o_lon, o_lat = wgs("ox", "oy")
    d_lon, d_lat = wgs("dx", "dy")

    table = pa.table(
        {
            "origin_zone": [a["origin_zone"] for a in arcs],
            "dest_zone": [a["dest_zone"] for a in arcs],
            "motive": [a["motive"] for a in arcs],
            "motive_name": [a["motive_name"] for a in arcs],
            "trips": [a["weight"] for a in arcs],
            "o_lon": o_lon,
            "o_lat": o_lat,
            "d_lon": d_lon,
            "d_lat": d_lat,
        }
    )
    pq.write_table(table, settings.dist_dir / "fluxos.parquet", compression="zstd")
    _write_csv(settings.dist_dir / "fluxos.csv", table)
    log.info(
        "wrote fluxos.parquet and fluxos.csv (%d trips, %d trips/day)",
        len(arcs),
        summary["trips"],
    )


def write_flow_points(arcs: list[dict]) -> None:
    """Point layers for the flow map: the origins, and the destinations split by purpose.

    Points only — the arcs themselves are never drawn. Each layer is a GeoJSON in WGS84 that
    tippecanoe turns into the flow-map PMTiles; a point keeps just the trips it carries and,
    for destinations, the motive name for the hover label.
    """
    import numpy as np

    settings.dist_dir.mkdir(parents=True, exist_ok=True)

    def to_wgs(key_x: str, key_y: str) -> tuple[np.ndarray, np.ndarray]:
        lon, lat = _to_wgs.transform(
            np.fromiter((a[key_x] for a in arcs), dtype=float),
            np.fromiter((a[key_y] for a in arcs), dtype=float),
        )
        return np.round(lon, 5), np.round(lat, 5)

    o_lon, o_lat = to_wgs("ox", "oy")
    _write_points("origens", o_lon, o_lat, [{"weight": a["weight"]} for a in arcs])

    d_lon, d_lat = to_wgs("dx", "dy")
    categories: dict[str, list[int]] = {
        "casa": [],
        "trabalho": [],
        "educacao": [],
        "saude": [],
        "outros": [],
    }
    for i, arc in enumerate(arcs):
        categories[DEST_CATEGORY.get(arc["motive"], "outros")].append(i)
    for name, rows in categories.items():
        props = [{"weight": arcs[i]["weight"], "motive_name": arcs[i]["motive_name"]} for i in rows]
        _write_points(f"dest_{name}", d_lon[rows], d_lat[rows], props)


def _write_points(name: str, lon, lat, properties: list[dict]) -> None:
    features = [
        {
            "type": "Feature",
            "geometry": {"type": "Point", "coordinates": [float(lon[i]), float(lat[i])]},
            "properties": properties[i],
        }
        for i in range(len(properties))
    ]
    _write(
        settings.dist_dir / f"{name}.geojson",
        {"type": "FeatureCollection", "features": features},
    )


def _write_csv(path, table: pa.Table) -> None:
    import csv

    columns = table.column_names
    with open(path, "w", newline="", encoding="utf-8") as handle:
        writer = csv.writer(handle)
        writer.writerow(columns)
        writer.writerows(zip(*(table.column(c).to_pylist() for c in columns), strict=True))


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
