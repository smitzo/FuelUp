from dataclasses import dataclass
from datetime import datetime, timedelta
from decimal import Decimal, InvalidOperation

from routes.domain.fuel_data import ObservationState


@dataclass(frozen=True, slots=True)
class ObservationPolicy:
    min_unit_price: Decimal
    max_unit_price: Decimal
    max_age: timedelta
    future_skew: timedelta
    duplicate_window: timedelta
    rapid_update_window: timedelta
    absolute_outlier_tolerance: Decimal
    relative_outlier_tolerance: Decimal

    def __post_init__(self):
        if not Decimal("0") < self.min_unit_price < self.max_unit_price:
            raise ValueError("Observation price bounds are invalid.")
        if self.absolute_outlier_tolerance < 0:
            raise ValueError("Absolute outlier tolerance cannot be negative.")
        if not Decimal("0") <= self.relative_outlier_tolerance <= Decimal("1"):
            raise ValueError("Relative outlier tolerance must be between 0 and 1.")
        for field_name in (
            "max_age",
            "future_skew",
            "duplicate_window",
            "rapid_update_window",
        ):
            if getattr(self, field_name) < timedelta(0):
                raise ValueError(f"{field_name} cannot be negative.")


@dataclass(frozen=True, slots=True)
class ObservationSubmission:
    unit_price: Decimal
    observed_at: datetime
    received_at: datetime


@dataclass(frozen=True, slots=True)
class ValidationContext:
    compatible_fuel: bool = True
    station_accepting_reports: bool = True
    duplicate: bool = False
    rapid_update: bool = False
    comparable_prices: tuple[Decimal, ...] = ()


@dataclass(frozen=True, slots=True)
class ValidationOutcome:
    state: ObservationState
    reason: str


def validate_observation(
    submission: ObservationSubmission,
    context: ValidationContext,
    policy: ObservationPolicy,
) -> ValidationOutcome:
    if not _is_aware(submission.observed_at) or not _is_aware(submission.received_at):
        return _rejected("invalid_timestamp")
    if not submission.unit_price.is_finite():
        return _rejected("invalid_price")
    try:
        outside_price_bounds = not (
            policy.min_unit_price <= submission.unit_price <= policy.max_unit_price
        )
    except InvalidOperation:
        outside_price_bounds = True
    if outside_price_bounds:
        return _rejected("price_out_of_bounds")
    if submission.observed_at > submission.received_at + policy.future_skew:
        return _rejected("observed_in_future")
    if submission.observed_at < submission.received_at - policy.max_age:
        return _rejected("observation_too_old")
    if not context.compatible_fuel:
        return _rejected("incompatible_fuel")
    if not context.station_accepting_reports:
        return _rejected("station_not_accepting_reports")
    if context.duplicate:
        return _rejected("duplicate")
    if context.rapid_update:
        return _quarantined("rapid_update")

    comparable = tuple(
        price for price in context.comparable_prices if price.is_finite()
    )
    if comparable:
        midpoint = _median(comparable)
        tolerance = max(
            policy.absolute_outlier_tolerance,
            midpoint * policy.relative_outlier_tolerance,
        )
        if abs(submission.unit_price - midpoint) > tolerance:
            return _quarantined("price_outlier")

    return ValidationOutcome(ObservationState.ACCEPTED, "accepted")


def _is_aware(value: datetime) -> bool:
    return value.tzinfo is not None and value.utcoffset() is not None


def _median(values: tuple[Decimal, ...]) -> Decimal:
    ordered = sorted(values)
    midpoint = len(ordered) // 2
    if len(ordered) % 2:
        return ordered[midpoint]
    return (ordered[midpoint - 1] + ordered[midpoint]) / Decimal("2")


def _rejected(reason: str) -> ValidationOutcome:
    return ValidationOutcome(ObservationState.REJECTED, reason)


def _quarantined(reason: str) -> ValidationOutcome:
    return ValidationOutcome(ObservationState.QUARANTINED, reason)
