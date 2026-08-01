from django.db.models import Prefetch, Q
from django.utils import timezone

from routes.domain.entities import Coordinate, PricedStation
from routes.domain.fuel_data import (
    FuelType,
    ObservationState,
    OperatingStatus,
)
from routes.domain.market import MarketConfig
from routes.domain.price_resolver import resolve_price_quote
from routes.infrastructure.observation_queries import (
    applicable_reference_values,
    group_observations,
)
from routes.models import (
    FuelStation,
    ObservationWatermark,
    PriceObservation,
    StationFuel,
    StationSnapshot,
)


class PricedStationRepository:
    def __init__(self, market: MarketConfig):
        self.market = market

    def load(
        self,
        *,
        fuel_type: FuelType,
        fuel_grade: str | None,
        at=None,
        allow_stale=False,
    ):
        at = at or timezone.now()
        snapshot = (
            StationSnapshot.objects.filter(
                market_code=self.market.code,
                is_active=True,
                is_valid=True,
            )
            .select_related("source")
            .first()
        )
        if snapshot is None:
            return StationCatalogue.empty(self.market.code)

        fuel_rows = StationFuel.objects.filter(
            fuel_type=fuel_type,
            is_available=True,
        )
        if fuel_grade:
            fuel_rows = fuel_rows.filter(grade__iexact=fuel_grade.strip())
        else:
            fuel_rows = fuel_rows.filter(grade="")
        stations = tuple(
            FuelStation.objects.filter(snapshot=snapshot)
            .prefetch_related(Prefetch("fuels", queryset=fuel_rows))
            .order_by("stable_id")
        )
        station_ids = [station.id for station in stations]
        observations = PriceObservation.objects.filter(
            Q(station_id__in=station_ids) | Q(station__isnull=True),
            market_code=self.market.code,
            fuel_type=fuel_type,
            state=ObservationState.ACCEPTED,
        ).select_related("station", "source")
        by_station, references = group_observations(observations)

        resolved_stations = []
        for station in stations:
            if not station.fuels.all():
                continue
            applicable = [*by_station[station.id]]
            applicable.extend(
                applicable_reference_values(station, references, self.market)
            )
            quote = resolve_price_quote(
                applicable,
                fuel_type=fuel_type,
                fuel_grade=fuel_grade,
                at=at,
                allow_stale=allow_stale,
            )
            resolved_stations.append(
                PricedStation(
                    stable_id=station.stable_id,
                    name=station.name,
                    address=station.address,
                    city=station.city,
                    state=station.state,
                    coordinate=Coordinate(
                        latitude=float(station.latitude),
                        longitude=float(station.longitude),
                    ),
                    fuel_types=frozenset({fuel_type}),
                    price_quote=quote,
                    operating_status=OperatingStatus(station.operating_status),
                )
            )

        watermark = (
            ObservationWatermark.objects.filter(scope=self.market.code)
            .values_list("version", flat=True)
            .first()
            or 0
        )
        return StationCatalogue(
            market_code=self.market.code,
            stations=tuple(resolved_stations),
            snapshot_version=snapshot.version,
            snapshot_generated_at=snapshot.source_generated_at,
            observation_watermark=watermark,
            attribution=snapshot.source.attribution,
        )


class StationCatalogue:
    def __init__(
        self,
        *,
        market_code,
        stations,
        snapshot_version,
        snapshot_generated_at,
        observation_watermark,
        attribution,
    ):
        self.market_code = market_code
        self.stations = stations
        self.snapshot_version = snapshot_version
        self.snapshot_generated_at = snapshot_generated_at
        self.observation_watermark = observation_watermark
        self.attribution = attribution

    @property
    def earliest_quote_expiry(self):
        expiries = [
            station.price_quote.expires_at
            for station in self.stations
            if station.price_quote.expires_at is not None
        ]
        return min(expiries) if expiries else None

    @classmethod
    def empty(cls, market_code):
        return cls(
            market_code=market_code,
            stations=(),
            snapshot_version="unavailable",
            snapshot_generated_at=None,
            observation_watermark=0,
            attribution="",
        )
