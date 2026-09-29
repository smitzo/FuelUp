"""Normalize documented API Mitra rows without inventing locality or freshness."""

from dataclasses import dataclass
from datetime import datetime, timedelta
from decimal import Decimal, InvalidOperation
from zoneinfo import ZoneInfo

from django.utils import timezone
from django.utils.dateparse import parse_datetime

from routes.domain.fuel_data import FuelType, GeographicPrecision
from routes.domain.geography import scoped_geography_id

IST = ZoneInfo("Asia/Kolkata")


@dataclass(frozen=True)
class ReferencePrice:
    geography_id: str
    precision: GeographicPrecision
    fuel_type: FuelType
    unit_price: Decimal
    observed_at: datetime
    effective_at: datetime
    expires_at: datetime


def parse_mitra_prices(payload, *, at=None):
    at = at or timezone.now()
    if not isinstance(payload, dict) or payload.get("status") != "ok":
        raise ValueError("Price provider did not return a successful snapshot.")
    rows = payload.get("data")
    if not isinstance(rows, list) or not rows:
        raise ValueError("Expected a nonempty price row list.")
    result = []
    for row in rows:
        if not isinstance(row, dict):
            raise ValueError("Invalid price row.")
        observed = parse_datetime(str(row.get("updated_at") or ""))
        if observed is None or timezone.is_naive(observed):
            raise ValueError("Each price needs a source timestamp with timezone.")
        if observed > at + timedelta(minutes=5) or observed < at - timedelta(hours=36):
            raise ValueError("Price observation is stale or in the future.")
        kind = row.get("location_type")
        name, state = row.get("location"), row.get("state")
        if not isinstance(name, str) or not name.strip():
            raise ValueError("Price location is missing.")
        if kind == "state":
            precision = GeographicPrecision.STATE
            identifier = scoped_geography_id("in", name)
        elif kind == "city" and isinstance(state, str) and state.strip():
            precision = GeographicPrecision.CITY
            identifier = scoped_geography_id("in", state, name)
        else:
            raise ValueError("City prices require an explicit parent state.")
        # Expiry follows the source date, never the local fetch time.
        effective = observed.astimezone(IST).replace(
            hour=6, minute=0, second=0, microsecond=0
        )
        if effective > observed:
            effective -= timedelta(days=1)
        expires = effective + timedelta(days=1, hours=6)
        if expires <= at:
            raise ValueError("Price snapshot has expired.")
        for fuel in FuelType:
            product = row.get(fuel.value)
            if product is None:
                continue
            if not isinstance(product, dict) or product.get("unit") != "per_litre":
                raise ValueError("Expected an explicit per-litre price.")
            try:
                value = Decimal(str(product.get("price")))
            except InvalidOperation as exc:
                raise ValueError("Invalid price.") from exc
            if not value.is_finite() or not Decimal("20") <= value <= Decimal("300"):
                raise ValueError("Price is outside supported INR/litre bounds.")
            result.append(
                ReferencePrice(
                    identifier, precision, fuel, value, observed, effective, expires
                )
            )
    if not result:
        raise ValueError("Snapshot contains no compatible fuel prices.")
    keys = [(item.geography_id, item.fuel_type) for item in result]
    if len(set(keys)) != len(keys):
        raise ValueError("Snapshot contains duplicate geographic fuel prices.")
    return tuple(result)
