"""The exporter reprojects to WGS84 and writes both forms of each layer."""

from __future__ import annotations

import json

from transporte_sp_od import export
from transporte_sp_od.config import settings


def test_writes_parquet_and_geojson_in_wgs84(tmp_path, monkeypatch):
    monkeypatch.setattr(type(settings), "dist_dir", property(lambda self: tmp_path))
    layers = {
        "residencia": [{"zone": 1, "x": 333725.0, "y": 7394554.0, "weight": 50}],
        "trabalho": [
            {"zone": 6, "x": 332814.0, "y": 7395769.0, "weight": 50,
             "sector": 4, "sector_name": "Comércio"},
        ],
    }
    export.write_all(layers, {"people_per_point": 50})

    assert (tmp_path / "residencia.parquet").exists()
    assert (tmp_path / "trabalho.parquet").exists()

    geo = json.loads((tmp_path / "residencia.geojson").read_text())
    lon, lat = geo["features"][0]["geometry"]["coordinates"]
    # Sé, São Paulo — the survey coordinate reprojected out of UTM 23S.
    assert -47 < lon < -46 and -24 < lat < -23
    assert "x" not in geo["features"][0]["properties"]
    assert geo["features"][0]["properties"]["weight"] == 50

    trabalho = json.loads((tmp_path / "trabalho.geojson").read_text())
    assert trabalho["features"][0]["properties"]["sector_name"] == "Comércio"


def test_an_empty_layer_writes_no_parquet(tmp_path, monkeypatch):
    monkeypatch.setattr(type(settings), "dist_dir", property(lambda self: tmp_path))
    export.write_all({"vazio": []}, {})
    assert not (tmp_path / "vazio.parquet").exists()
    assert (tmp_path / "vazio.geojson").exists()
