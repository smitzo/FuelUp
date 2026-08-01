from collections import defaultdict

from routes.domain.fuel_data import (
    FuelType,
    GeographicPrecision,
    ObservationState,
    PriceObservationValue,
    SourceType,
)


def group_observations(observations):
    by_station = defaultdict(list)
    references = defaultdict(list)
    for observation in observations:
        value = observation_value(observation)
        if observation.station_id:
            by_station[observation.station_id].append(value)
        else:
            references[observation.geography_precision].append(value)
    return by_station, references


def applicable_reference_values(station, references, market):
    values = {
        GeographicPrecision.CITY: station.city,
        GeographicPrecision.DISTRICT: station.district,
        GeographicPrecision.STATE: station.state,
        GeographicPrecision.COUNTRY: market.country_geography_id,
    }
    applicable = []
    for precision, geography_value in values.items():
        normalized = normalize_geography(geography_value)
        applicable.extend(
            observation
            for observation in references[precision.value]
            if normalize_geography(observation.geography_id) == normalized
        )
    return applicable


def observation_value(observation):
    return PriceObservationValue(
        observation_id=str(observation.id),
        station_id=(observation.station.stable_id if observation.station_id else None),
        geography_precision=GeographicPrecision(observation.geography_precision),
        geography_id=observation.geography_id,
        fuel_type=FuelType(observation.fuel_type),
        fuel_grade=observation.fuel_grade or None,
        unit_price=observation.unit_price,
        source_type=SourceType(observation.source_type),
        source_id=observation.source_id,
        observed_at=observation.observed_at,
        effective_at=observation.effective_at,
        received_at=observation.received_at,
        expires_at=observation.expires_at,
        state=ObservationState(observation.state),
        contributor_id=observation.contributor_id or None,
    )


def normalize_geography(value):
    return " ".join(value.strip().casefold().split())
