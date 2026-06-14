import math
from collections import defaultdict

from routes.domain.entities import Coordinate, RouteStation

EARTH_RADIUS_MILES = 3958.7613
GRID_SIZE_DEGREES = 0.25
CORRIDOR_MILES = 25.0


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


def route_stations(stations, coordinates, route_distance_miles):
    points = [
        Coordinate(latitude=latitude, longitude=longitude)
        for longitude, latitude in coordinates
    ]
    if len(points) < 2:
        return []

    cumulative = [0.0]
    for index in range(1, len(points)):
        cumulative.append(
            cumulative[-1] + haversine_miles(points[index - 1], points[index])
        )
    geometry_distance = cumulative[-1]
    distance_scale = route_distance_miles / geometry_distance if geometry_distance else 1

    route_grid = defaultdict(list)
    for index, point in enumerate(points):
        route_grid[_cell(point)].append(index)

    matched = {}
    for station in stations:
        nearest = _nearest_route_point(station.coordinate, points, route_grid)
        if nearest is None:
            continue
        point_index, distance = nearest
        if distance > CORRIDOR_MILES:
            continue
        route_mile = cumulative[point_index] * distance_scale
        key = (round(route_mile, 1), station.city.casefold(), station.state)
        candidate = RouteStation(
            station=station,
            route_mile=route_mile,
            distance_to_route_miles=distance,
        )
        existing = matched.get(key)
        if existing is None or station.retail_price < existing.station.retail_price:
            matched[key] = candidate

    return sorted(matched.values(), key=lambda item: item.route_mile)


def _nearest_route_point(coordinate, points, route_grid):
    row, column = _cell(coordinate)
    nearest = None
    # Two cells cover at least 34 latitude miles; longitude cells are narrower
    # in the northern U.S., so three cells keeps the 25-mile corridor covered.
    for row_offset in range(-2, 3):
        for column_offset in range(-3, 4):
            for index in route_grid.get((row + row_offset, column + column_offset), ()):
                distance = haversine_miles(coordinate, points[index])
                if nearest is None or distance < nearest[1]:
                    nearest = (index, distance)
    return nearest


def _cell(coordinate):
    return (
        math.floor(coordinate.latitude / GRID_SIZE_DEGREES),
        math.floor(coordinate.longitude / GRID_SIZE_DEGREES),
    )
