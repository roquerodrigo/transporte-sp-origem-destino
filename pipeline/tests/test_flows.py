"""One arc per geolocated survey trip: real endpoints, destination motive, expansion weight."""

from __future__ import annotations

from transporte_sp_od.build import flows


def _trip(**over):
    row = {
        "CO_O_X": 333725.0,
        "CO_O_Y": 7394554.0,
        "CO_D_X": 332814.0,
        "CO_D_Y": 7395769.0,
        "ZONA_O": 1,
        "ZONA_D": 2,
        "MOTIVO_D": 3,
        "FE_VIA": 51.0,
    }
    row.update(over)
    return row


def _run(trips, monkeypatch):
    monkeypatch.setattr(flows.survey, "records", lambda: iter(trips))
    return flows.run()


def test_each_geolocated_trip_becomes_one_arc(monkeypatch):
    summary = _run([_trip(), _trip(FE_VIA=22.0, MOTIVO_D=8)], monkeypatch)
    assert summary["arcs"] == 2
    assert summary["trips"] == 73  # 51 + 22, the expansion weights
    first = flows.run.arcs[0]
    assert (first["ox"], first["oy"]) == (333725.0, 7394554.0)  # real origin, survey CRS
    assert (first["dx"], first["dy"]) == (332814.0, 7395769.0)  # real destination
    assert first["weight"] == 51
    assert first["motive"] == 3
    assert first["motive_name"] == "Trabalho Serviços"


def test_the_destination_motive_labels_a_home_trip_as_home(monkeypatch):
    _run([_trip(MOTIVO_D=8)], monkeypatch)
    assert flows.run.arcs[0]["motive_name"] == "Residência"


def test_a_trip_missing_either_endpoint_is_skipped(monkeypatch):
    summary = _run(
        [
            _trip(CO_O_X=0, CO_O_Y=0),  # no origin coordinate
            _trip(CO_D_X=None),  # no destination coordinate
            _trip(FE_VIA=None),  # no weight
            _trip(),  # the one good trip
        ],
        monkeypatch,
    )
    assert summary["arcs"] == 1


def test_zones_are_carried_through(monkeypatch):
    _run([_trip(ZONA_O=17, ZONA_D=42)], monkeypatch)
    arc = flows.run.arcs[0]
    assert arc["origin_zone"] == 17
    assert arc["dest_zone"] == 42


def _arc(weight, ox=333725.0, oy=7394554.0, dx=332814.0, dy=7395769.0):
    return {
        "origin_zone": 1,
        "dest_zone": 2,
        "motive": 3,
        "motive_name": "Trabalho Serviços",
        "weight": weight,
        "ox": ox,
        "oy": oy,
        "dx": dx,
        "dy": dy,
    }


def test_subsample_hits_the_target_and_preserves_the_total():
    arcs = [_arc(100) for _ in range(2000)]  # total 200000
    light, summary = flows.subsample(arcs, target=400, seed=1)
    assert 320 <= summary["arcs"] <= 480  # ~400
    assert abs(summary["trips"] - 200000) / 200000 < 0.1  # total preserved


def test_a_dominant_trip_is_always_kept_with_its_own_weight():
    arcs = [_arc(1_000_000)] + [_arc(1) for _ in range(200)]
    light, _ = flows.subsample(arcs, target=10, seed=1)
    assert 1_000_000 in [a["weight"] for a in light]


def test_subsample_keeps_the_real_coordinates():
    arcs = [_arc(100) for _ in range(500)]
    light, _ = flows.subsample(arcs, target=100, seed=2)
    assert light and all(a["ox"] == 333725.0 and a["dy"] == 7395769.0 for a in light)
