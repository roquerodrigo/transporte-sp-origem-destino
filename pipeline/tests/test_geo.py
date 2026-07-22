from transporte_sp_od.geo import ZoneIndex


def square(zone, x0, y0, size):
    return {
        "zone": zone,
        "rings": [[[x0, y0], [x0 + size, y0], [x0 + size, y0 + size], [x0, y0 + size], [x0, y0]]],
    }


def test_a_point_is_assigned_to_the_zone_that_contains_it():
    index = ZoneIndex([square(10, 0, 0, 100), square(20, 100, 0, 100)])
    assert index.zone_of(50, 50) == 10
    assert index.zone_of(150, 50) == 20


def test_a_point_outside_every_zone_is_none():
    index = ZoneIndex([square(10, 0, 0, 100)])
    assert index.zone_of(500, 500) is None


def test_vectorised_assignment_matches_the_scalar_one():
    import numpy as np

    index = ZoneIndex([square(10, 0, 0, 100), square(20, 100, 0, 100)])
    xs = np.array([50.0, 150.0, 500.0])
    ys = np.array([50.0, 50.0, 500.0])
    assert index.zones_of(xs, ys) == [10, 20, None]
