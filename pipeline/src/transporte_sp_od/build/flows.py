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

import numpy as np

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


def _inclusion_probabilities(weights: np.ndarray, target: int) -> np.ndarray:
    """Inclusion probabilities ∝ weight that sum to ``target``, capped at 1.

    Trips heavier than the average share become certainties (probability 1); the remaining
    budget is shared among the rest, iterated because capping one trip raises the others.
    """
    probability = np.minimum(1.0, target * weights / weights.sum())
    for _ in range(50):
        certain = probability >= 1.0
        remaining_budget = target - int(certain.sum())
        if remaining_budget <= 0:
            break
        share = remaining_budget * weights / weights[~certain].sum()
        updated = np.where(certain, 1.0, np.minimum(1.0, share))
        if np.array_equal(updated, probability):
            break
        probability = updated
    return probability


def subsample(arcs: list[dict], target: int, seed: int = 20230101) -> tuple[list[dict], dict]:
    """A lighter set of ~``target`` trips that still sums to the same daily total.

    Probability-proportional-to-size: a trip is kept with probability ∝ its weight (heavy
    trips almost surely survive), and each survivor is reweighted by ``weight / probability``
    (Horvitz–Thompson), so the expected total is unchanged. The coordinates stay real — a
    survivor is a real surveyed trip, just standing for more of them.
    """
    rng = np.random.default_rng(seed)
    weights = np.fromiter((arc["weight"] for arc in arcs), dtype=float, count=len(arcs))
    probability = _inclusion_probabilities(weights, target)
    kept = np.nonzero(rng.random(len(arcs)) < probability)[0]

    lighter = [{**arcs[i], "weight": round(arcs[i]["weight"] / probability[i])} for i in kept]
    summary = {"target": target, "arcs": len(lighter), "trips": sum(a["weight"] for a in lighter)}
    log.info(
        "subsample: %d -> %d trips (target %d), %d trips/day",
        len(arcs),
        len(lighter),
        target,
        summary["trips"],
    )
    return lighter, summary
