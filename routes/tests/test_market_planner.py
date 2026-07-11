from datetime import timedelta
from decimal import Decimal

from django.test import SimpleTestCase
from django.utils import timezone

from routes.application.market_planner import build_route_plan
from routes.domain.entities import Coordinate, GeocodedLocation, PricedStation
from routes.domain.exceptions import InsufficientPriceDataError
from routes.domain.fuel_data import (
    Confidence,
    FuelType,
    GeographicPrecision,
    PriceLabel,
    PriceQualityPolicy,
    ResolvedPriceQuote,
    RoutePlanRequest,
    RouteStrategy,
    VehicleProfile,
)
from routes.infrastructure.priced_station_repository import (
    StationCatalogue,
)
from routes.tests.factories import market_config


class FakeMapClient:
    def geocode(self, query):
        coordinates = {
            "Ahmedabad": Coordinate(23, 72),
            "Anand": Coordinate(23, 73),
            "Vadodara": Coordinate(23, 74),
        }
        return GeocodedLocation(
            query=query,
            display_name=f"{query}, Gujarat, India",
            coordinate=coordinates[query],
        )

    def routes_through(self, locations):
        return [
            {
                "distance": 200_000,
                "duration": 7200,
                "geometry": {
                    "type": "LineString",
                    "coordinates": [
                        [location.coordinate.longitude, location.coordinate.latitude]
                        for location in locations
                    ],
                },
            }
        ]


class MarketRoutePlannerTests(SimpleTestCase):
    def setUp(self):
        now = timezone.now()
        self.quote = ResolvedPriceQuote(
            unit_price=Decimal("100"),
            label=PriceLabel.REFERENCE,
            geography_precision=GeographicPrecision.CITY,
            confidence=Confidence.LOW,
            as_of=now,
            expires_at=now + timedelta(hours=24),
            observation_ids=("price-1",),
        )
        self.station = PricedStation(
            stable_id="osm-node-1",
            name="Anand Fuel",
            address="NH 48",
            city="Anand",
            state="Gujarat",
            coordinate=Coordinate(23, 73),
            fuel_types=frozenset({FuelType.PETROL}),
            price_quote=self.quote,
        )
        self.market = market_config()
        self.catalogue = StationCatalogue(
            market_code=self.market.code,
            stations=(self.station,),
            snapshot_version="india-test-v1",
            snapshot_generated_at=now,
            observation_watermark=3,
            attribution="OpenStreetMap contributors",
        )
        self.request = RoutePlanRequest(
            start="Ahmedabad",
            finish="Vadodara",
            waypoints=("Anand",),
            vehicle=VehicleProfile(
                fuel_type=FuelType.PETROL,
                tank_capacity=Decimal("35"),
                efficiency=Decimal("20"),
                starting_fuel=Decimal("6"),
                reserve_fuel=Decimal("3"),
            ),
            maximum_detour=Decimal("5"),
            strategy=RouteStrategy.BALANCED,
        )

    def test_builds_configured_market_plan_with_waypoint_and_quality(self):
        plan = build_route_plan(
            self.request,
            catalogue=self.catalogue,
            market=self.market,
            client=FakeMapClient(),
        )

        self.assertEqual(plan["api_version"], "v2")
        self.assertEqual(plan["market"]["code"], "IN")
        self.assertEqual(plan["route"]["distance"], 200)
        self.assertEqual(plan["waypoints"][0]["query"], "Anand")
        self.assertEqual(plan["fuel_plan"]["currency"], "INR")
        self.assertEqual(plan["fuel_plan"]["purchase_cost"], 400)
        self.assertEqual(plan["fuel_plan"]["stops"][0]["price"]["label"], "reference")
        self.assertEqual(plan["data_quality"]["label_counts"], {"reference": 1})
        self.assertEqual(plan["metadata"]["detour_validation"], "estimated")

    def test_station_reported_only_rejects_city_reference(self):
        strict_request = RoutePlanRequest(
            start=self.request.start,
            finish=self.request.finish,
            waypoints=self.request.waypoints,
            vehicle=self.request.vehicle,
            maximum_detour=self.request.maximum_detour,
            price_quality=PriceQualityPolicy.STATION_REPORTED_ONLY,
        )

        with self.assertRaises(InsufficientPriceDataError):
            build_route_plan(
                strict_request,
                catalogue=self.catalogue,
                market=self.market,
                client=FakeMapClient(),
            )
