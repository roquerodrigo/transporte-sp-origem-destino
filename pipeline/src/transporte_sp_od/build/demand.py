"""The demand as points at the survey's real coordinates.

Each surveyed person carries a real coordinate for their dwelling (``CO_DOM``) and — when they
have one — their workplace (``CO_TR1``) and school (``CO_ESC``), plus an expansion weight
(``FE_PESS``) saying how many residents, workers or students they stand for. This emits one
point per real location, carrying its weight; the map renders them as a weighted heatmap.
Nothing is invented — the coordinates are the ones the survey reports, not addresses drawn
within a zone. The weighted totals are the survey's population, jobs and students exactly.
"""

from __future__ import annotations

import logging

from transporte_sp_od.sources import survey

log = logging.getLogger(__name__)


def run() -> dict:
    """Materialise the demand point layers from the survey's coordinates; return counts."""
    layers: dict[str, list[dict]] = {"residencia": [], "trabalho": [], "educacao": []}

    for person in survey.people():
        weight = person.get("FE_PESS") or 0
        if not weight:
            continue
        weight = round(weight)

        home_x, home_y = person.get("CO_DOM_X"), person.get("CO_DOM_Y")
        if home_x and home_y:
            layers["residencia"].append({"x": float(home_x), "y": float(home_y), "weight": weight})

        work_x, work_y = person.get("CO_TR1_X"), person.get("CO_TR1_Y")
        sector = person.get("SETOR1")
        if work_x and work_y and sector and str(sector).strip() not in ("", "0"):
            layers["trabalho"].append({"x": float(work_x), "y": float(work_y), "weight": weight})

        school_x, school_y = person.get("CO_ESC_X"), person.get("CO_ESC_Y")
        if school_x and school_y and person.get("ESTUDA") and person["ESTUDA"] != 1:
            layers["educacao"].append(
                {"x": float(school_x), "y": float(school_y), "weight": weight}
            )

    summary = {
        "layers": {name: len(points) for name, points in layers.items()},
        "totals": {
            "residents": sum(p["weight"] for p in layers["residencia"]),
            "jobs": sum(p["weight"] for p in layers["trabalho"]),
            "students": sum(p["weight"] for p in layers["educacao"]),
        },
    }
    run.layers = layers
    log.info(
        "demand: %(residencia)d residências, %(trabalho)d trabalho, %(educacao)d educação",
        summary["layers"],
    )
    return summary
