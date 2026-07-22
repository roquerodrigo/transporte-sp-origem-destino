"""Demand points come straight from the survey's real coordinates, weighted by FE_PESS."""

from __future__ import annotations

from transporte_sp_od.build import demand


def _person(**over):
    row = {
        "FE_PESS": 100.0,
        "CO_DOM_X": 333725.0,
        "CO_DOM_Y": 7394554.0,
        "CO_TR1_X": 332814.0,
        "CO_TR1_Y": 7395769.0,
        "SETOR1": 4,
        "CO_ESC_X": None,
        "CO_ESC_Y": None,
        "ESTUDA": 1,
    }
    row.update(over)
    return row


def _run(people, monkeypatch):
    monkeypatch.setattr(demand.survey, "people", lambda: iter(people))
    return demand.run()


def test_a_person_becomes_a_home_and_a_work_point(monkeypatch):
    summary = _run([_person()], monkeypatch)
    assert summary["layers"]["residencia"] == 1
    assert summary["layers"]["trabalho"] == 1
    assert summary["layers"]["educacao"] == 0
    home = demand.run.layers["residencia"][0]
    assert (home["x"], home["y"]) == (333725.0, 7394554.0)
    assert home["weight"] == 100


def test_totals_sum_the_expansion_weight(monkeypatch):
    summary = _run([_person(FE_PESS=100.0), _person(FE_PESS=50.0)], monkeypatch)
    assert summary["totals"]["residents"] == 150
    assert summary["totals"]["jobs"] == 150


def test_a_person_without_a_workplace_makes_no_work_point(monkeypatch):
    summary = _run([_person(CO_TR1_X=0, CO_TR1_Y=0, SETOR1=0)], monkeypatch)
    assert summary["layers"]["trabalho"] == 0
    assert summary["layers"]["residencia"] == 1


def test_a_student_makes_a_school_point(monkeypatch):
    summary = _run([_person(ESTUDA=2, CO_ESC_X=331000.0, CO_ESC_Y=7396000.0)], monkeypatch)
    assert summary["layers"]["educacao"] == 1
