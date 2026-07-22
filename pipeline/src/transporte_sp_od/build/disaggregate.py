"""Turn the zone-level survey demand into address-level points.

The survey gives, per record, an expansion weight and a real coordinate for the dwelling and
(for workers) the workplace with its economic sector. Summed by zone, those weights are the
zone totals — population per home zone, jobs per (work zone × sector), students and patients
per destination zone. Disaggregation places those totals onto real CNEFE addresses of the
matching species within each zone, one materialised point per ``people_per_point`` demand.

The totals are preserved exactly (the last point in a zone absorbs the rounding); only the
granularity of the dots is sampled. Nothing is placed on a street, because every candidate
is a CNEFE address, which sits on the lot.
"""

from __future__ import annotations

import logging
from collections import defaultdict

import numpy as np
import pyarrow.parquet as pq

from transporte_sp_od.config import (
    EDUCATION_SPECIES,
    ESTABLISHMENT_SPECIES,
    HEALTH_SPECIES,
    RESIDENTIAL_SPECIES,
    SECTOR,
    settings,
)
from transporte_sp_od.sources import survey

log = logging.getLogger(__name__)

# Where each kind of demand lands. Education and health have their own CNEFE species; every
# other job lands on a generic establishment; residents on dwellings.
SECTOR_SPECIES = {11: EDUCATION_SPECIES, 10: HEALTH_SPECIES}


class Candidates:
    """The CNEFE addresses available in each zone, grouped by species, for sampling."""

    def __init__(self) -> None:
        table = pq.read_table(settings.dist_dir / "enderecos.parquet")
        zones = table.column("zone").to_numpy()
        species = table.column("species").to_pylist()
        self._x = table.column("x").to_numpy()
        self._y = table.column("y").to_numpy()
        self._by: dict[tuple[int, str], list[int]] = defaultdict(list)
        for i, (zone, esp) in enumerate(zip(zones, species, strict=True)):
            self._by[(int(zone), esp)].append(i)
        # A pool of candidate row indices per (zone, species-set), built on first use. Flows
        # sample the same few species-sets per zone hundreds of thousands of times, so the
        # pool is cached rather than rebuilt each call.
        self._pool_cache: dict[tuple[int, frozenset[str]], np.ndarray] = {}
        log.info("candidates: %d addresses in %d (zone, species) groups", len(self._x),
                 len(self._by))

    def _pool(self, zone: int, species: set[str]) -> np.ndarray:
        key = (zone, frozenset(species))
        pool = self._pool_cache.get(key)
        if pool is None:
            pool = np.fromiter(
                (i for esp in species for i in self._by.get((zone, esp), ())),
                dtype=np.int64,
            )
            self._pool_cache[key] = pool
        return pool

    def sample(self, zone: int, species: set[str], count: int, rng) -> list[tuple[float, float]]:
        pool = self._pool(zone, species)
        if pool.size == 0 or count <= 0:
            return []
        chosen = rng.choice(pool, size=count, replace=pool.size < count)
        return list(zip(self._x[chosen].tolist(), self._y[chosen].tolist(), strict=True))


def _zone_totals() -> tuple[
    dict[int, float], dict[tuple[int, int], float], dict[int, float], dict[int, float]
]:
    """Weighted demand from the microdata: residents, jobs by sector, students, patients."""
    residents: dict[int, float] = defaultdict(float)
    jobs: dict[tuple[int, int], float] = defaultdict(float)  # (work zone, sector) -> jobs
    students: dict[int, float] = defaultdict(float)
    for person in survey.people():
        weight = person.get("FE_PESS") or 0.0
        home = person.get("ZONA")
        if home and weight:
            residents[int(home)] += weight
        sector = person.get("SETOR1")
        work_zone = person.get("ZONATRA1")
        if sector and work_zone and str(sector).strip() not in ("", "0") and weight:
            jobs[(int(work_zone), int(sector))] += weight
        if person.get("ESTUDA") and person["ESTUDA"] != 1 and person.get("ZONA_ESC") and weight:
            students[int(person["ZONA_ESC"])] += weight
    patients: dict[int, float] = defaultdict(float)  # placeholder for a future health pass
    return residents, jobs, students, patients


def run(seed: int = 20230101) -> dict:
    """Materialise the point layers; return per-layer counts for the caller to export."""
    rng = np.random.default_rng(seed)
    factor = settings.people_per_point
    candidates = Candidates()
    residents, jobs, students, _patients = _zone_totals()

    layers: dict[str, list[dict]] = {"residencia": [], "trabalho": [], "educacao": []}

    def place(zone: int, species: set[str], demand: float, layer: str, extra: dict) -> None:
        count = round(demand / factor)
        for x, y in candidates.sample(zone, species, count, rng):
            layers[layer].append({"zone": zone, "x": x, "y": y, "weight": factor, **extra})

    for zone, demand in residents.items():
        place(zone, RESIDENTIAL_SPECIES, demand, "residencia", {})
    for (zone, sector), demand in jobs.items():
        species = SECTOR_SPECIES.get(sector, ESTABLISHMENT_SPECIES)
        place(zone, species, demand, "trabalho", {"sector": sector, "sector_name": SECTOR[sector]})
    for zone, demand in students.items():
        place(zone, EDUCATION_SPECIES, demand, "educacao", {})

    summary = {
        "people_per_point": factor,
        "layers": {name: len(points) for name, points in layers.items()},
        "totals": {
            "residents": round(sum(residents.values())),
            "jobs": round(sum(jobs.values())),
            "students": round(sum(students.values())),
        },
    }
    log.info(
        "disaggregate: %(residencia)d residências, %(trabalho)d trabalho, %(educacao)d educação",
        summary["layers"],
    )
    run.layers = layers  # handed to the exporter
    return summary
