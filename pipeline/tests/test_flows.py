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
