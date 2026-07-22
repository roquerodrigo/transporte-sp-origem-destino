"""The observed origin→destination trips, one arc per geolocated survey record.

The survey microdata geolocates every trip: a real origin coordinate (``CO_O``), a real
destination coordinate (``CO_D``), the destination's motive (``MOTIVO_D``) and an expansion
weight (``FE_VIA``) saying how many daily trips the record stands for. This keeps each such
record as one arc — the real pair, at real coordinates, not scattered onto zone addresses —
so the origin↔destination pairing is the observed one, not a synthetic within-zone draw.

Only records with both endpoints geolocated are kept (~113k of ~143k; the rest have no
coordinate). Coordinates are in the survey CRS (Córrego Alegre / UTM 23S, metres) and are
reprojected to WGS84 on export.
"""

from __future__ import annotations

import logging
from collections import defaultdict

from transporte_sp_od.config import MOTIVE
from transporte_sp_od.sources import survey

log = logging.getLogger(__name__)


def run() -> dict:
    """Materialise one arc per geolocated trip; return counts for the exporter."""
    arcs: list[dict] = []
    for row in survey.records():
        ox, oy = row.get("CO_O_X"), row.get("CO_O_Y")
        dx, dy = row.get("CO_D_X"), row.get("CO_D_Y")
        motive, weight = row.get("MOTIVO_D"), row.get("FE_VIA")
        if not (ox and oy and dx and dy and motive and weight):
            continue
        motive = int(motive)
        arcs.append(
            {
                "origin_zone": int(row["ZONA_O"]) if row.get("ZONA_O") else 0,
                "dest_zone": int(row["ZONA_D"]) if row.get("ZONA_D") else 0,
                "motive": motive,
                "motive_name": MOTIVE.get(motive, str(motive)),
                "weight": round(weight),
                "ox": float(ox),
                "oy": float(oy),
                "dx": float(dx),
                "dy": float(dy),
            }
        )

    run.arcs = arcs
    by_motive: dict[str, int] = defaultdict(int)
    for arc in arcs:
        by_motive[arc["motive_name"]] += arc["weight"]
    summary = {
        "arcs": len(arcs),
        "trips": sum(arc["weight"] for arc in arcs),
        "by_motive": dict(sorted(by_motive.items(), key=lambda kv: -kv[1])),
    }
    log.info(
        "flows: %d observed trips, %d trips/day across %d motives",
        len(arcs),
        summary["trips"],
        len(by_motive),
    )
    return summary
