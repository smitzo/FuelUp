import math
from collections import defaultdict
from dataclasses import dataclass

from routes.domain.entities import Coordinate, RouteStation

EARTH_RADIUS_MILES = 3958.7613
MILES_PER_LATITUDE_DEGREE = 69.0
GRID_SIZE_DEGREES = 0.25
CORRIDOR_MILES = 25.0


@dataclass(frozen=True, slots=True)
class RouteSegment:
    start: Coordinate
    finish: Coordinate
    start_mile: float
    length_miles: float


class RouteGeometryIndex:
    def __init__(self, coordinates, route_distance_miles):
        self.points = tuple(
            Coordinate(latitude=latitude, longitude=longitude)
            for longitude, latitude in coordinates
        )
        self.segments = self._build_segments()
        geometry_distance = sum(segment.length_miles for segment in self.segments)
        self.distance_scale = (
            route_distance_miles / geometry_distance if geometry_distance else 1.0
        )
        self.grid = self._build_grid()

    def project(self, coordinate):
        nearest = None
        for segment_index in self._candidate_segment_indexes(coordinate):
            segment = self.segments[segment_index]
            distance, fraction = project_to_segment_miles(coordinate, segment)
            if nearest is None or distance < nearest[0]:
                route_mile = (
                    segment.start_mile + segment.length_miles * fraction
                ) * self.distance_scale
                nearest = (distance, route_mile)
        return nearest

    def _build_segments(self):
        segments = []
        cumulative_miles = 0.0
        for start, finish in zip(self.points, self.points[1:]):
            length = haversine_miles(start, finish)
            if length <= 0:
                continue
            segments.append(
                RouteSegment(
                    start=start,
                    finish=finish,
                    start_mile=cumulative_miles,
                    length_miles=length,
                )
            )
            cumulative_miles += length
        return tuple(segments)

    def _build_grid(self):
        grid = defaultdict(list)
        for index, segment in enumerate(self.segments):
            min_row, min_column = _cell(
                Coordinate(
                    latitude=min(segment.start.latitude, segment.finish.latitude),
                    longitude=min(segment.start.longitude, segment.finish.longitude),
                )
            )
            max_row, max_column = _cell(
                Coordinate(
                    latitude=max(segment.start.latitude, segment.finish.latitude),
                    longitude=max(segment.start.longitude, segment.finish.longitude),
                )
            )
            for row in range(min_row, max_row + 1):
                for column in range(min_column, max_column + 1):
                    grid[(row, column)].append(index)
        return grid

    def _candidate_segment_indexes(self, coordinate):
        row, column = _cell(coordinate)
        latitude_cells = math.ceil(
            CORRIDOR_MILES / (MILES_PER_LATITUDE_DEGREE * GRID_SIZE_DEGREES)
        )
        longitude_miles = max(
            1.0,
            MILES_PER_LATITUDE_DEGREE
            * math.cos(math.radians(coordinate.latitude))
            * GRID_SIZE_DEGREES,
        )
        longitude_cells = math.ceil(CORRIDOR_MILES / longitude_miles)
        indexes = set()
        for row_offset in range(-latitude_cells, latitude_cells + 1):
            for column_offset in range(-longitude_cells, longitude_cells + 1):
                indexes.update(
                    self.grid.get(
                        (row + row_offset, column + column_offset),
                        (),
                    )
                )
        return indexes


def haversine_miles(left, right):
    lat1 = math.radians(left.latitude)
    lat2 = math.radians(right.latitude)
    delta_lat = lat2 - lat1
    delta_lon = math.radians(right.longitude - left.longitude)
    value = (
        math.sin(delta_lat / 2) ** 2
        + math.cos(lat1) * math.cos(lat2) * math.sin(delta_lon / 2) ** 2
    )
    return 2 * EARTH_RADIUS_MILES * math.asin(math.sqrt(value))


def project_to_segment_miles(point, segment):
    reference_latitude = math.radians(point.latitude)
    longitude_scale = MILES_PER_LATITUDE_DEGREE * math.cos(reference_latitude)

    start_x = (segment.start.longitude - point.longitude) * longitude_scale
    start_y = (
        segment.start.latitude - point.latitude
    ) * MILES_PER_LATITUDE_DEGREE
    finish_x = (segment.finish.longitude - point.longitude) * longitude_scale
    finish_y = (
        segment.finish.latitude - point.latitude
    ) * MILES_PER_LATITUDE_DEGREE

    delta_x = finish_x - start_x
    delta_y = finish_y - start_y
    length_squared = delta_x * delta_x + delta_y * delta_y
    if length_squared == 0:
        return math.hypot(start_x, start_y), 0.0

    fraction = -(start_x * delta_x + start_y * delta_y) / length_squared
    fraction = min(1.0, max(0.0, fraction))
    projected_x = start_x + fraction * delta_x
    projected_y = start_y + fraction * delta_y
    return math.hypot(projected_x, projected_y), fraction


def route_stations(stations, coordinates, route_distance_miles):
    index = RouteGeometryIndex(coordinates, route_distance_miles)
    if not index.segments:
        return []

    matched = {}
    for station in stations:
        projection = index.project(station.coordinate)
        if projection is None:
            continue
        distance_to_route, route_mile = projection
        if distance_to_route > CORRIDOR_MILES:
            continue
        key = (round(route_mile, 1), station.city.casefold(), station.state)
        candidate = RouteStation(
            station=station,
            route_mile=route_mile,
            distance_to_route_miles=distance_to_route,
        )
        existing = matched.get(key)
        if existing is None or _candidate_rank(candidate) < _candidate_rank(existing):
            matched[key] = candidate

    return sorted(matched.values(), key=lambda item: item.route_mile)


def _candidate_rank(candidate):
    return (
        candidate.station.retail_price,
        candidate.distance_to_route_miles,
        candidate.station.opis_id,
    )


def _cell(coordinate):
    return (
        math.floor(coordinate.latitude / GRID_SIZE_DEGREES),
        math.floor(coordinate.longitude / GRID_SIZE_DEGREES),
    )
