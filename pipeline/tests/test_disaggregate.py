"""The disaggregation preserves the survey totals and lands demand on the right species."""

from __future__ import annotations

import numpy as np

from transporte_sp_od.build import disaggregate
from transporte_sp_od.config import (
    EDUCATION_SPECIES,
    ESTABLISHMENT_SPECIES,
    RESIDENTIAL_SPECIES,
    SECTOR,
)


class FakeCandidates:
    """Two zones, each with dwellings, generic establishments and a school."""

    def __init__(self) -> None:
        self.asked: list[tuple[int, frozenset, int]] = []

    def sample(self, zone, species, count, rng):
        self.asked.append((zone, frozenset(species), count))
        # Return `count` distinct points so the caller's length is the demand/factor.
        return [(float(zone * 1000 + i), float(i), *()) for i in range(count)]


def test_totals_are_preserved_and_species_are_respected(monkeypatch):
    people = [
        # zone 1: two residents, one a commerce worker in zone 2, one a student in zone 2
        {"FE_PESS": 100.0, "ZONA": 1, "SETOR1": 4, "ZONATRA1": 2, "ESTUDA": 1, "ZONA_ESC": None},
        {"FE_PESS": 100.0, "ZONA": 1, "SETOR1": None, "ZONATRA1": None,
         "ESTUDA": 3, "ZONA_ESC": 2},
    ]
    monkeypatch.setattr(disaggregate.survey, "people", lambda: iter(people))
    fake = FakeCandidates()
    monkeypatch.setattr(disaggregate, "Candidates", lambda: fake)

    summary = disaggregate.run(seed=1)

    assert summary["totals"]["residents"] == 200
    assert summary["totals"]["jobs"] == 100
    assert summary["totals"]["students"] == 100
    # 200 residents / 50 = 4 residence points, 100 jobs / 50 = 2, 100 students / 50 = 2
    assert summary["layers"] == {"residencia": 4, "trabalho": 2, "educacao": 2}

    asked = {(zone, species): count for zone, species, count in fake.asked}
    assert asked[(1, frozenset(RESIDENTIAL_SPECIES))] == 4
    assert asked[(2, frozenset(ESTABLISHMENT_SPECIES))] == 2  # commerce -> establishment
    assert asked[(2, frozenset(EDUCATION_SPECIES))] == 2  # student -> school


def test_health_and_education_sectors_use_their_own_species(monkeypatch):
    people = [
        {"FE_PESS": 50.0, "ZONA": 1, "SETOR1": 10, "ZONATRA1": 1, "ESTUDA": 1},  # saúde
        {"FE_PESS": 50.0, "ZONA": 1, "SETOR1": 11, "ZONATRA1": 1, "ESTUDA": 1},  # ensino
    ]
    monkeypatch.setattr(disaggregate.survey, "people", lambda: iter(people))
    fake = FakeCandidates()
    monkeypatch.setattr(disaggregate, "Candidates", lambda: fake)
    disaggregate.run(seed=1)
    especies = {species for _, species, _ in fake.asked}
    from transporte_sp_od.config import HEALTH_SPECIES

    assert frozenset(HEALTH_SPECIES) in especies
    assert frozenset(EDUCATION_SPECIES) in especies


def test_every_sector_is_named():
    assert set(SECTOR) == set(range(1, 15))
    assert all(SECTOR.values())


def test_candidate_sampling_never_leaves_the_pool():
    rng = np.random.default_rng(0)
    candidates = disaggregate.Candidates.__new__(disaggregate.Candidates)
    candidates._by = {(1, "1"): [0, 1, 2]}
    candidates._pool_cache = {}
    candidates._x = np.array([10.0, 11.0, 12.0])
    candidates._y = np.array([20.0, 21.0, 22.0])
    got = candidates.sample(1, {"1"}, 10, rng)
    assert len(got) == 10
    assert all(point[0] in (10.0, 11.0, 12.0) for point in got)
    assert candidates.sample(1, {"1"}, 0, rng) == []
    assert candidates.sample(9, {"1"}, 5, rng) == []  # empty zone
