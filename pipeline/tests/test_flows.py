"""A fixed budget of arcs is spread across OD cells; each cell's trips are preserved exactly."""

from __future__ import annotations

import numpy as np
import pytest

from transporte_sp_od.build import flows
from transporte_sp_od.config import (
    EDUCATION_SPECIES,
    ESTABLISHMENT_SPECIES,
    HEALTH_SPECIES,
    RESIDENTIAL_SPECIES,
)


class FakeCandidates:
    """Records each (zone, species) sampled; returns `count` distinct placeholder points."""

    def __init__(self) -> None:
        self.asked: list[tuple[int, frozenset, int]] = []

    def sample(self, zone, species, count, rng):
        self.asked.append((zone, frozenset(species), count))
        return [(float(zone), float(i)) for i in range(count)]


def _run(trips, target, monkeypatch):
    monkeypatch.setattr(flows.survey, "records", lambda: iter(trips))
    fake = FakeCandidates()
    monkeypatch.setattr(flows, "Candidates", lambda: fake)
    summary = flows.run(target=target)
    return summary, fake


def test_allocation_hits_the_target_and_preserves_every_cell_total(monkeypatch):
    trips = [
        {"ZONA_O": 1, "ZONA_D": 2, "MOTIVO": 2, "FE_VIA": 900.0},
        {"ZONA_O": 1, "ZONA_D": 3, "MOTIVO": 2, "FE_VIA": 100.0},
    ]
    summary, _ = _run(trips, target=10, monkeypatch=monkeypatch)
    assert summary["arcs"] == 10  # exactly the budget
    assert summary["trips"] == 1000  # 900 + 100, preserved
    by_cell: dict[tuple[int, int], int] = {}
    for arc in flows.run.arcs:
        key = (arc["origin_zone"], arc["dest_zone"])
        by_cell[key] = by_cell.get(key, 0) + arc["weight"]
    assert by_cell[(1, 2)] == 900
    assert by_cell[(1, 3)] == 100


def test_every_cell_keeps_at_least_one_arc(monkeypatch):
    trips = [
        {"ZONA_O": 1, "ZONA_D": 2, "MOTIVO": 2, "FE_VIA": 999.0},
        {"ZONA_O": 5, "ZONA_D": 6, "MOTIVO": 2, "FE_VIA": 1.0},  # tiny, must still appear
    ]
    _run(trips, target=5, monkeypatch=monkeypatch)
    seen = {(arc["origin_zone"], arc["dest_zone"]) for arc in flows.run.arcs}
    assert (5, 6) in seen


def test_a_target_below_the_cell_count_is_rejected(monkeypatch):
    trips = [
        {"ZONA_O": 1, "ZONA_D": 2, "MOTIVO": 2, "FE_VIA": 500.0},
        {"ZONA_O": 1, "ZONA_D": 3, "MOTIVO": 2, "FE_VIA": 500.0},
    ]
    monkeypatch.setattr(flows.survey, "records", lambda: iter(trips))
    monkeypatch.setattr(flows, "Candidates", FakeCandidates)
    with pytest.raises(ValueError, match="below"):
        flows.run(target=1)


def test_destination_species_follows_the_motive(monkeypatch):
    trips = [
        {"ZONA_O": 1, "ZONA_D": 2, "MOTIVO": 2, "FE_VIA": 500.0},  # commerce -> establishment
        {"ZONA_O": 1, "ZONA_D": 3, "MOTIVO": 4, "FE_VIA": 500.0},  # education -> school
        {"ZONA_O": 1, "ZONA_D": 4, "MOTIVO": 6, "FE_VIA": 500.0},  # health -> health unit
        {"ZONA_O": 1, "ZONA_D": 5, "MOTIVO": 8, "FE_VIA": 500.0},  # home -> dwelling
    ]
    _, fake = _run(trips, target=8, monkeypatch=monkeypatch)
    dest_species = {zone: species for zone, species, _ in fake.asked if zone in (2, 3, 4, 5)}
    assert dest_species[2] == frozenset(ESTABLISHMENT_SPECIES)
    assert dest_species[3] == frozenset(EDUCATION_SPECIES)
    assert dest_species[4] == frozenset(HEALTH_SPECIES)
    assert dest_species[5] == frozenset(RESIDENTIAL_SPECIES)


def test_origin_is_always_a_dwelling(monkeypatch):
    trips = [{"ZONA_O": 7, "ZONA_D": 2, "MOTIVO": 4, "FE_VIA": 300.0}]
    _, fake = _run(trips, target=3, monkeypatch=monkeypatch)
    origin = next(entry for entry in fake.asked if entry[0] == 7)
    assert origin[1] == frozenset(RESIDENTIAL_SPECIES)


def test_incomplete_trips_are_ignored(monkeypatch):
    trips = [
        {"ZONA_O": 1, "ZONA_D": None, "MOTIVO": 2, "FE_VIA": 500.0},
        {"ZONA_O": 1, "ZONA_D": 2, "MOTIVO": 2, "FE_VIA": 500.0},
    ]
    summary, _ = _run(trips, target=3, monkeypatch=monkeypatch)
    assert summary["cells"] == 1  # only the complete trip formed a cell
    _ = np
