from dataclasses import dataclass
from datetime import datetime, timedelta
from decimal import Decimal

from django.conf import settings
from django.db import transaction
from django.db.models import F, Q
from django.utils import timezone

from routes.domain.fuel_data import (
    FuelType,
    GeographicPrecision,
    ObservationState,
    OperatingStatus,
    SourceType,
)
from routes.domain.observation_validation import (
    ObservationPolicy,
    ObservationSubmission,
    ValidationContext,
    ValidationOutcome,
    validate_observation,
)
from routes.models import (
    FuelStation,
    ObservationWatermark,
    PriceImportBatch,
    PriceModerationEvent,
    PriceObservation,
    SourceRegistry,
    StationFuel,
)


@dataclass(frozen=True, slots=True)
class ObservationCreate:
    market_code: str
    source: SourceRegistry
    source_type: SourceType
    geography_precision: GeographicPrecision
    geography_id: str
    fuel_type: FuelType
    fuel_grade: str
    unit_price: Decimal
    observed_at: datetime
    effective_at: datetime
    expires_at: datetime
    station: FuelStation | None = None
    contributor_id: str = ""
    evidence: dict | None = None
    import_batch: PriceImportBatch | None = None
    supersedes: PriceObservation | None = None


@dataclass(frozen=True, slots=True)
class StoredObservation:
    observation: PriceObservation
    outcome: ValidationOutcome


@transaction.atomic
def validate_and_store_observation(command: ObservationCreate) -> StoredObservation:
    received_at = timezone.now()
    policy = configured_observation_policy()
    station = _locked_station(command.station)
    context = _validation_context(command, station, received_at, policy)
    outcome = validate_observation(
        ObservationSubmission(
            unit_price=command.unit_price,
            observed_at=command.observed_at,
            received_at=received_at,
        ),
        context,
        policy,
    )
    observation = PriceObservation.objects.create(
        market_code=command.market_code.upper(),
        station=station,
        import_batch=command.import_batch,
        supersedes=command.supersedes,
        geography_precision=command.geography_precision,
        geography_id=command.geography_id,
        fuel_type=command.fuel_type,
        fuel_grade=command.fuel_grade.strip().casefold(),
        unit_price=command.unit_price,
        source=command.source,
        source_type=command.source_type,
        observed_at=command.observed_at,
        effective_at=command.effective_at,
        expires_at=command.expires_at,
        state=outcome.state,
        contributor_id=command.contributor_id,
        evidence=command.evidence or {},
        validation_reason=outcome.reason,
    )
    if outcome.state == ObservationState.ACCEPTED:
        advance_observation_watermark(command.market_code)
    return StoredObservation(observation, outcome)


@transaction.atomic
def transition_observation(
    observation_id: int,
    *,
    new_state: ObservationState,
    actor_id: str,
    reason_code: str,
    metadata: dict | None = None,
) -> PriceObservation:
    observation = PriceObservation.objects.select_for_update().get(id=observation_id)
    previous_state = ObservationState(observation.state)
    if new_state == previous_state:
        return observation
    if new_state not in _allowed_transitions(previous_state):
        raise ValueError(
            f"Cannot transition observation from {previous_state} to {new_state}."
        )
    observation.state = new_state
    observation.validation_reason = reason_code
    observation.save(update_fields=("state", "validation_reason"))
    PriceModerationEvent.objects.create(
        observation=observation,
        actor_id=actor_id,
        action="state_transition",
        reason_code=reason_code,
        previous_state=previous_state,
        new_state=new_state,
        metadata=metadata or {},
    )
    if ObservationState.ACCEPTED in {previous_state, new_state}:
        advance_observation_watermark(observation.market_code)
    return observation


@transaction.atomic
def advance_observation_watermark(market_code: str) -> int:
    scope = market_code.upper()
    watermark, _created = (
        ObservationWatermark.objects.select_for_update().get_or_create(scope=scope)
    )
    ObservationWatermark.objects.filter(scope=scope).update(version=F("version") + 1)
    watermark.refresh_from_db(fields=("version",))
    return watermark.version


def configured_observation_policy() -> ObservationPolicy:
    values = settings.OBSERVATION_POLICY
    return ObservationPolicy(
        min_unit_price=values["min_unit_price"],
        max_unit_price=values["max_unit_price"],
        max_age=timedelta(seconds=values["max_age_seconds"]),
        future_skew=timedelta(seconds=values["future_skew_seconds"]),
        duplicate_window=timedelta(seconds=values["duplicate_window_seconds"]),
        rapid_update_window=timedelta(seconds=values["rapid_update_window_seconds"]),
        absolute_outlier_tolerance=values["absolute_outlier_tolerance"],
        relative_outlier_tolerance=values["relative_outlier_tolerance"],
    )


def _locked_station(station: FuelStation | None) -> FuelStation | None:
    if station is None:
        return None
    return (
        FuelStation.objects.select_for_update()
        .select_related("snapshot")
        .get(id=station.id)
    )


def _validation_context(command, station, received_at, policy):
    compatible_fuel = True
    station_accepting_reports = True
    if station is not None:
        fuel_rows = StationFuel.objects.filter(
            station=station,
            fuel_type=command.fuel_type,
            is_available=True,
        )
        if command.fuel_grade:
            fuel_rows = fuel_rows.filter(grade__iexact=command.fuel_grade.strip())
        else:
            fuel_rows = fuel_rows.filter(grade="")
        compatible_fuel = fuel_rows.exists()
        station_accepting_reports = (
            station.operating_status != OperatingStatus.CLOSED
            and station.snapshot.market_code.upper() == command.market_code.upper()
            and station.snapshot.is_active
            and station.snapshot.is_valid
        )

    candidates = PriceObservation.objects.filter(
        market_code__iexact=command.market_code,
        station=station,
        fuel_type=command.fuel_type,
        fuel_grade__iexact=command.fuel_grade.strip(),
    )
    if station is None:
        candidates = candidates.filter(
            geography_precision=command.geography_precision,
            geography_id__iexact=command.geography_id.strip(),
        )
    duplicate = False
    rapid_update = False
    if command.contributor_id:
        contributor_rows = candidates.filter(
            contributor_id=command.contributor_id,
            observed_at__gte=received_at - policy.duplicate_window,
        ).exclude(state__in=(ObservationState.RETRACTED, ObservationState.SUPERSEDED))
        duplicate = contributor_rows.filter(unit_price=command.unit_price).exists()
        rapid_update = (
            not duplicate
            and contributor_rows.filter(
                observed_at__gte=received_at - policy.rapid_update_window
            ).exists()
        )

    comparable_prices = tuple(
        candidates.filter(
            state=ObservationState.ACCEPTED,
            observed_at__gte=received_at - policy.max_age,
            effective_at__lte=received_at,
            expires_at__gt=received_at,
        )
        .filter(Q(contributor_id="") | ~Q(contributor_id=command.contributor_id))
        .values_list("unit_price", flat=True)
    )
    return ValidationContext(
        compatible_fuel=compatible_fuel,
        station_accepting_reports=station_accepting_reports,
        duplicate=duplicate,
        rapid_update=rapid_update,
        comparable_prices=comparable_prices,
    )


def _allowed_transitions(state: ObservationState) -> frozenset[ObservationState]:
    return {
        ObservationState.PENDING: frozenset(
            {
                ObservationState.ACCEPTED,
                ObservationState.QUARANTINED,
                ObservationState.REJECTED,
            }
        ),
        ObservationState.QUARANTINED: frozenset(
            {
                ObservationState.ACCEPTED,
                ObservationState.REJECTED,
                ObservationState.RETRACTED,
            }
        ),
        ObservationState.REJECTED: frozenset({ObservationState.ACCEPTED}),
        ObservationState.ACCEPTED: frozenset(
            {ObservationState.RETRACTED, ObservationState.SUPERSEDED}
        ),
        ObservationState.RETRACTED: frozenset(),
        ObservationState.SUPERSEDED: frozenset(),
    }[state]
