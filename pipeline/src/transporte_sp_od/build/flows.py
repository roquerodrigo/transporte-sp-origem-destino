"""Materialise the survey trips as a fixed budget of address-level origin→destination arcs.

Each survey trip carries an origin zone, a destination zone, a motive and an expansion weight.
Summed by (origin zone, destination zone, motive), those weights are the true daily trips of
each OD cell. Rather than one arc per fixed number of trips — which lets the row count float
with the data — this spreads a **fixed budget** of arcs across the cells in proportion to
their trips: every non-empty cell gets at least one arc, and the rest are shared out by size.
Each arc places its origin on a real dwelling in the origin zone and its destination on a real
address of the motive's kind in the destination zone, and carries an integer share of the
cell's trips. The per-cell total is preserved exactly, so the grand total is too.

The pairing within a cell is synthetic — the survey does not say which exact home connects to
which exact workplace beyond its sample — but the origin-zone × destination-zone × motive
structure and its trip totals are exactly the survey's, now resolved to real addresses.
"""

from __future__ import annotations

import logging
from collections import defaultdict

import numpy as np

from transporte_sp_od.build.disaggregate import Candidates
from transporte_sp_od.config import (
    EDUCATION_SPECIES,
    ESTABLISHMENT_SPECIES,
    HEALTH_SPECIES,
    MOTIVE,
    RESIDENTIAL_SPECIES,
    settings,
)
from transporte_sp_od.sources import survey

log = logging.getLogger(__name__)

# Which CNEFE species the destination of a trip lands on, by motive. Education and health have
# their own species; a trip home lands on a dwelling; everything else — work, shopping, meals,
# leisure, personal — lands on a generic establishment.
MOTIVE_DESTINATION = {
    4: EDUCATION_SPECIES,
    6: HEALTH_SPECIES,
    8: RESIDENTIAL_SPECIES,
}

Cell = tuple[int, int, int]  # (origin zone, destination zone, motive)


def _cells() -> dict[Cell, float]:
    """Total expanded trips per OD cell, from the valid survey trip records."""
    totals: dict[Cell, float] = defaultdict(float)
    for row in survey.records():
        origin, destination = row.get("ZONA_O"), row.get("ZONA_D")
        motive, weight = row.get("MOTIVO"), row.get("FE_VIA")
        if not (origin and destination and motive and weight):
            continue
        totals[(int(origin), int(destination), int(motive))] += weight
    return totals


def _allocate(totals: dict[Cell, float], target: int) -> dict[Cell, int]:
    """Arcs per cell: one each, then the remaining budget shared by trips (largest remainder).

    The counts sum to exactly ``target`` and every non-empty cell keeps at least one arc.
    """
    cells = list(totals)
    if target < len(cells):
        raise ValueError(f"target {target} is below the {len(cells)} OD cells; raise it")
    grand = sum(totals.values())
    extra = target - len(cells)
    share = {cell: totals[cell] / grand * extra for cell in cells}
    base = {cell: int(share[cell]) for cell in cells}
    leftover = extra - sum(base.values())
    by_fraction = sorted(cells, key=lambda c: share[c] - base[c], reverse=True)
    for cell in by_fraction[:leftover]:
        base[cell] += 1
    return {cell: 1 + base[cell] for cell in cells}


def _split(total: int, parts: int) -> list[int]:
    """Split ``total`` trips into ``parts`` integers as evenly as possible; they sum to total."""
    base, remainder = divmod(total, parts)
    return [base + 1] * remainder + [base] * (parts - remainder)


def run(target: int | None = None, seed: int = 20230101) -> dict:
    """Materialise the arcs; return counts for the exporter. Coordinates stay in the survey CRS."""
    target = settings.flows_target if target is None else target
    rng = np.random.default_rng(seed)
    candidates = Candidates()
    totals = _cells()
    counts = _allocate(totals, target)

    arcs: list[dict] = []
    dropped = 0
    for (origin, destination, motive), count in counts.items():
        dest_species = MOTIVE_DESTINATION.get(motive, ESTABLISHMENT_SPECIES)
        origins = candidates.sample(origin, RESIDENTIAL_SPECIES, count, rng)
        dests = candidates.sample(destination, dest_species, count, rng)
        if not origins or not dests:
            dropped += 1
            continue
        trips = _split(round(totals[(origin, destination, motive)]), count)
        motive_name = MOTIVE.get(motive, str(motive))
        for (ox, oy), (dx, dy), weight in zip(origins, dests, trips, strict=True):
            arcs.append(
                {
                    "origin_zone": origin,
                    "dest_zone": destination,
                    "motive": motive,
                    "motive_name": motive_name,
                    "weight": weight,
                    "ox": ox,
                    "oy": oy,
                    "dx": dx,
                    "dy": dy,
                }
            )

    run.arcs = arcs
    by_motive: dict[str, int] = defaultdict(int)
    for arc in arcs:
        by_motive[arc["motive_name"]] += arc["weight"]
    summary = {
        "target": target,
        "arcs": len(arcs),
        "cells": len(totals),
        "dropped_cells": dropped,
        "trips": sum(arc["weight"] for arc in arcs),
        "by_motive": dict(sorted(by_motive.items(), key=lambda kv: -kv[1])),
    }
    log.info(
        "flows: %d arcs across %d cells (%d dropped, no candidate), %d trips/day",
        len(arcs),
        len(totals),
        dropped,
        summary["trips"],
    )
    return summary
