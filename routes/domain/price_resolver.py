from collections import defaultdict
from datetime import datetime
from decimal import Decimal
from statistics import median

from routes.domain.fuel_data import (
    Confidence,
    FuelType,
    GeographicPrecision,
    ObservationState,
    PriceLabel,
    ResolvedPriceQuote,
    SourceType,
)

RESOLVER_VERSION = "fuel-price:v2"
DEFAULT_ABSOLUTE_TOLERANCE = Decimal("3.00")
DEFAULT_PERCENT_TOLERANCE = Decimal("0.03")
PRECISION_RANK = {
    GeographicPrecision.STATION: 0,
    GeographicPrecision.CITY: 1,
    GeographicPrecision.DISTRICT: 2,
    GeographicPrecision.STATE: 3,
    GeographicPrecision.COUNTRY: 4,
}


def resolve_price_quote(
    observations,
    *,
    fuel_type: FuelType,
    fuel_grade: str | None,
    at: datetime,
    allow_stale=False,
    absolute_tolerance=DEFAULT_ABSOLUTE_TOLERANCE,
    percent_tolerance=DEFAULT_PERCENT_TOLERANCE,
):
    candidates = tuple(
        observation
        for observation in observations
        if _matches_request(observation, fuel_type, fuel_grade)
        and observation.state == ObservationState.ACCEPTED
        and observation.effective_at <= at
    )
    current = tuple(
        observation for observation in candidates if observation.is_current(at)
    )

    official_station = _best(
        observation
        for observation in current
        if observation.source_type == SourceType.OFFICIAL_REFERENCE
        and observation.geography_precision == GeographicPrecision.STATION
    )
    if official_station:
        return _single_quote(
            official_station,
            label=PriceLabel.REFERENCE,
            confidence=Confidence.HIGH,
        )

    community = tuple(
        observation
        for observation in current
        if observation.source_type == SourceType.COMMUNITY_REPORT
        and observation.geography_precision == GeographicPrecision.STATION
    )
    consensus = _community_consensus(
        community,
        absolute_tolerance=Decimal(str(absolute_tolerance)),
        percent_tolerance=Decimal(str(percent_tolerance)),
    )
    if consensus:
        return consensus

    single_report = _best(community)
    if single_report:
        return _single_quote(
            single_report,
            label=PriceLabel.REPORTED,
            confidence=Confidence.LOW,
        )

    official_reference = _best(
        observation
        for observation in current
        if observation.source_type == SourceType.OFFICIAL_REFERENCE
    )
    if official_reference:
        return _single_quote(
            official_reference,
            label=PriceLabel.REFERENCE,
            confidence=Confidence.LOW,
        )

    third_party = _best(
        observation
        for observation in current
        if observation.source_type == SourceType.THIRD_PARTY_REFERENCE
    )
    if third_party:
        return _single_quote(
            third_party, label=PriceLabel.REFERENCE, confidence=Confidence.LOW
        )

    estimate = _best(
        observation
        for observation in current
        if observation.source_type == SourceType.MODEL_ESTIMATE
    )
    if estimate:
        return _single_quote(
            estimate,
            label=PriceLabel.ESTIMATED,
            confidence=Confidence.LOW,
        )

    if allow_stale:
        stale = _best(
            observation
            for observation in candidates
            if observation.expires_at <= at
        )
        if stale:
            return _single_quote(
                stale,
                label=PriceLabel.STALE,
                confidence=Confidence.LOW,
            )
    return ResolvedPriceQuote.unavailable()


def _matches_request(observation, fuel_type, fuel_grade):
    if observation.fuel_type != fuel_type:
        return False
    requested_grade = fuel_grade.strip().casefold() if fuel_grade else None
    observed_grade = (
        observation.fuel_grade.strip().casefold()
        if observation.fuel_grade
        else None
    )
    return requested_grade == observed_grade


def _community_consensus(
    observations,
    *,
    absolute_tolerance,
    percent_tolerance,
):
    latest_by_contributor = {}
    for observation in observations:
        if observation.contributor_id:
            existing = latest_by_contributor.get(observation.contributor_id)
            if existing is None or _newer(observation, existing):
                latest_by_contributor[observation.contributor_id] = observation
    independent = tuple(latest_by_contributor.values())
    if len(independent) < 2:
        return None

    middle = Decimal(str(median(item.unit_price for item in independent)))
    tolerance = max(absolute_tolerance, middle * percent_tolerance)
    accepted = tuple(
        item
        for item in independent
        if abs(item.unit_price - middle) <= tolerance
    )
    if len(accepted) < 2:
        return None

    resolved = Decimal(str(median(item.unit_price for item in accepted)))
    as_of = max(item.observed_at for item in accepted)
    expires_at = min(item.expires_at for item in accepted)
    return ResolvedPriceQuote(
        unit_price=resolved,
        label=PriceLabel.REPORTED,
        geography_precision=GeographicPrecision.STATION,
        confidence=(
            Confidence.HIGH if len(accepted) >= 3 else Confidence.MEDIUM
        ),
        as_of=as_of,
        expires_at=expires_at,
        observation_ids=tuple(
            sorted(item.observation_id for item in accepted)
        ),
        resolver_version=RESOLVER_VERSION,
    )


def _single_quote(observation, *, label, confidence):
    return ResolvedPriceQuote(
        unit_price=observation.unit_price,
        label=label,
        geography_precision=observation.geography_precision,
        confidence=confidence,
        as_of=observation.observed_at,
        expires_at=observation.expires_at,
        observation_ids=(observation.observation_id,),
        resolver_version=RESOLVER_VERSION,
    )


def _best(observations):
    grouped = defaultdict(list)
    for observation in observations:
        grouped[PRECISION_RANK[observation.geography_precision]].append(observation)
    if not grouped:
        return None
    most_precise = grouped[min(grouped)]
    return max(
        most_precise,
        key=lambda item: (
            item.observed_at,
            item.received_at,
            item.observation_id,
        ),
    )


def _newer(left, right):
    return (left.observed_at, left.received_at, left.observation_id) > (
        right.observed_at,
        right.received_at,
        right.observation_id,
    )
