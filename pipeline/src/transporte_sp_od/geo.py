"""Spatial helpers, all in the survey's projected CRS (Córrego Alegre UTM 23S, metres)."""

from __future__ import annotations

import logging

from shapely import STRtree
from shapely.geometry import Polygon
from shapely.geometry import shape as to_shape

log = logging.getLogger(__name__)


class ZoneIndex:
    """Assigns points to OD zones by point-in-polygon, indexed for millions of queries.

    Built from the survey's zone rings. A point that falls in no zone (outside the RMSP, or
    in a coordinate gap) returns ``None`` and is dropped by the caller.
    """

    def __init__(self, zones: list[dict]) -> None:
        self._zone_numbers: list[int] = []
        polygons: list[Polygon] = []
        for zone in zones:
            rings = zone["rings"]
            if not rings:
                continue
            polygon = to_shape(
                {"type": "Polygon", "coordinates": rings}
            )
            if not polygon.is_valid:
                polygon = polygon.buffer(0)
            polygons.append(polygon)
            self._zone_numbers.append(zone["zone"])
        self._polygons = polygons
        self._tree = STRtree(polygons)
        log.info("zone index: %d zones", len(polygons))

    def zone_of(self, x: float, y: float) -> int | None:
        from shapely.geometry import Point

        point = Point(x, y)
        for candidate in self._tree.query(point):
            if self._polygons[candidate].contains(point):
                return self._zone_numbers[candidate]
        return None

    def zones_of(self, xs, ys) -> list[int | None]:
        """Vectorised assignment for many points at once.

        ``STRtree.query`` returns ``[input_indices, tree_indices]``: point ``input[k]`` is
        within polygon ``tree[k]``. Zones do not overlap, so the first match per point wins.
        """
        from shapely import points

        pts = points(xs, ys)
        result: list[int | None] = [None] * len(pts)
        input_idx, poly_idx = self._tree.query(pts, predicate="within")
        for point_position, polygon_position in zip(input_idx, poly_idx, strict=True):
            if result[point_position] is None:
                result[point_position] = self._zone_numbers[polygon_position]
        return result
