from django.db.models import Prefetch, Q
from django.utils import timezone

from routes.domain.exceptions import (
    StationCatalogueUnavailableError,
    StationNotFoundError,
)
from routes.domain.fuel_data import FuelType, ObservationState, PriceLabel
from routes.domain.price_resolver import resolve_price_quote
from routes.infrastructure.observation_queries import (
    applicable_reference_values,
    group_observations,
)
from routes.models import FuelStation, PriceObservation, StationFuel, StationSnapshot


def search_station_directory(
    market,
    *,
    query="",
    fuel_type: FuelType | None = None,
    fuel_grade: str | None = None,
    page=1,
    page_size=20,
    at=None,
):
    at = at or timezone.now()
    snapshot = _active_snapshot(market.code)
    queryset = _station_queryset(snapshot, fuel_type, fuel_grade)
    if query:
        lookup = query.strip()
        queryset = queryset.filter(
            Q(stable_id__icontains=lookup)
            | Q(name__icontains=lookup)
            | Q(brand__icontains=lookup)
            | Q(address__icontains=lookup)
            | Q(city__icontains=lookup)
            | Q(district__icontains=lookup)
            | Q(state__icontains=lookup)
            | Q(postcode__icontains=lookup)
        )
    queryset = queryset.distinct().order_by("stable_id")
    total = queryset.count()
    start = (page - 1) * page_size
    stations = tuple(queryset[start : start + page_size])
    return {
        "api_version": "v2",
        "market": market.response_metadata(),
        "snapshot": _snapshot_payload(snapshot),
        "pagination": {
            "page": page,
            "page_size": page_size,
            "total_items": total,
            "total_pages": (total + page_size - 1) // page_size,
            "has_next": start + len(stations) < total,
            "has_previous": page > 1,
        },
        "stations": _serialize_stations(stations, market, at),
    }


def get_station_detail(market, stable_id, *, at=None):
    at = at or timezone.now()
    snapshot = _active_snapshot(market.code)
    try:
        station = _station_queryset(snapshot, None, None).get(stable_id=stable_id)
    except FuelStation.DoesNotExist as exc:
        raise StationNotFoundError(
            "The station is not in the active market catalogue."
        ) from exc
    return {
        "api_version": "v2",
        "market": market.response_metadata(),
        "snapshot": _snapshot_payload(snapshot),
        "station": _serialize_stations((station,), market, at)[0],
    }


def _active_snapshot(market_code):
    snapshot = (
        StationSnapshot.objects.filter(
            market_code=market_code,
            is_active=True,
            is_valid=True,
        )
        .select_related("source")
        .first()
    )
    if snapshot is None:
        raise StationCatalogueUnavailableError(
            "No active station catalogue is available for this market."
        )
    return snapshot


def _station_queryset(snapshot, fuel_type, fuel_grade):
    fuels = StationFuel.objects.order_by("fuel_type", "grade")
    queryset = FuelStation.objects.filter(snapshot=snapshot)
    if fuel_type is not None:
        fuels = fuels.filter(fuel_type=fuel_type, is_available=True)
        queryset = queryset.filter(
            fuels__fuel_type=fuel_type,
            fuels__is_available=True,
        )
    if fuel_grade is not None:
        normalized_grade = fuel_grade.strip()
        fuels = fuels.filter(grade__iexact=normalized_grade)
        queryset = queryset.filter(fuels__grade__iexact=normalized_grade)
    return queryset.prefetch_related(Prefetch("fuels", queryset=fuels))


def _serialize_stations(stations, market, at):
    station_ids = [station.id for station in stations]
    fuel_rows = [fuel for station in stations for fuel in station.fuels.all()]
    fuel_types = {fuel.fuel_type for fuel in fuel_rows}
    observations = tuple(
        PriceObservation.objects.filter(
            Q(station_id__in=station_ids) | Q(station__isnull=True),
            market_code=market.code,
            fuel_type__in=fuel_types,
            state=ObservationState.ACCEPTED,
        ).select_related("station", "source")
    )
    by_station, references = group_observations(observations)
    by_id = {str(observation.id): observation for observation in observations}
    serialized = []
    for station in stations:
        prices = []
        for fuel in station.fuels.all():
            applicable = [*by_station[station.id]]
            applicable.extend(applicable_reference_values(station, references, market))
            quote = resolve_price_quote(
                applicable,
                fuel_type=FuelType(fuel.fuel_type),
                fuel_grade=fuel.grade or None,
                at=at,
            )
            prices.append(_price_payload(fuel, quote, by_id))
        serialized.append(_station_payload(station, prices))
    return serialized


def _station_payload(station, prices):
    return {
        "id": station.stable_id,
        "name": station.name,
        "brand": station.brand,
        "address": {
            "line": station.address,
            "city": station.city,
            "district": station.district,
            "state": station.state,
            "postcode": station.postcode,
        },
        "location": {
            "latitude": float(station.latitude),
            "longitude": float(station.longitude),
            "precision": station.coordinate_precision,
        },
        "operating_status": station.operating_status,
        "last_seen_at": station.last_seen_at.isoformat(),
        "fuels": prices,
    }


def _price_payload(fuel, quote, observations):
    sources = []
    seen_sources = set()
    for observation_id in quote.observation_ids:
        observation = observations.get(observation_id)
        if observation is None or observation.source_id in seen_sources:
            continue
        seen_sources.add(observation.source_id)
        sources.append(
            {
                "slug": observation.source_id,
                "attribution": observation.source.attribution,
                "terms_url": observation.source.terms_url,
            }
        )
    return {
        "type": fuel.fuel_type,
        "grade": fuel.grade or None,
        "available": fuel.is_available,
        "inferred": fuel.is_inferred,
        "price": {
            "unit_price": (
                str(quote.unit_price) if quote.unit_price is not None else None
            ),
            "label": quote.label,
            "geographic_precision": (
                quote.geography_precision.value
                if quote.geography_precision is not None
                else None
            ),
            "confidence": quote.confidence,
            "as_of": quote.as_of.isoformat() if quote.as_of else None,
            "expires_at": (quote.expires_at.isoformat() if quote.expires_at else None),
            "observation_ids": list(quote.observation_ids),
            "resolver_version": quote.resolver_version,
            "sources": sources,
            "available": quote.label != PriceLabel.UNAVAILABLE,
        },
    }


def _snapshot_payload(snapshot):
    return {
        "version": snapshot.version,
        "source_generated_at": snapshot.source_generated_at.isoformat(),
        "imported_at": snapshot.imported_at.isoformat(),
        "source": {
            "slug": snapshot.source_id,
            "attribution": snapshot.source.attribution,
            "terms_url": snapshot.source.terms_url,
        },
    }
