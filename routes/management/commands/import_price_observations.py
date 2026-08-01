import hashlib
import json
from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal, InvalidOperation
from pathlib import Path

from django.conf import settings
from django.core.management.base import BaseCommand, CommandError
from django.db import transaction

from routes.application.observations import (
    ObservationCreate,
    validate_and_store_observation,
)
from routes.domain.fuel_data import (
    FuelType,
    GeographicPrecision,
    ObservationState,
    SourceType,
)
from routes.models import (
    FuelStation,
    PriceImportBatch,
    SourceRegistry,
)

SCHEMA_VERSION = 1


@dataclass(frozen=True, slots=True)
class ImportRow:
    source_record_id: str
    geography_precision: GeographicPrecision
    geography_id: str
    fuel_type: FuelType
    fuel_grade: str
    unit_price: Decimal
    observed_at: datetime
    effective_at: datetime
    expires_at: datetime
    station: FuelStation | None


class Command(BaseCommand):
    help = "Import a registry-approved local price-reference JSON snapshot."

    def add_arguments(self, parser):
        parser.add_argument("input_path")
        parser.add_argument("--source-slug", required=True)
        parser.add_argument(
            "--market-code",
            default=settings.MARKET_CONFIG["code"],
        )

    def handle(self, *args, **options):
        market_code = _market_code(options["market_code"])
        source = _approved_manual_source(options["source_slug"])
        raw, payload, checksum = _read_payload(options["input_path"])
        _validate_header(payload, market_code=market_code, source=source)
        source_generated_at = _aware_datetime(
            payload.get("source_generated_at"),
            "source_generated_at",
        )
        source_url = _required_text(payload, "source_url", maximum=1000)

        existing = PriceImportBatch.objects.filter(
            market_code=market_code,
            source=source,
            checksum_sha256=checksum,
        ).first()
        if existing is not None:
            self.stdout.write(
                self.style.WARNING(
                    f"Import batch {existing.id} already exists; no changes made."
                )
            )
            return

        rows = _normalize_rows(payload, market_code=market_code)
        counts = {state: 0 for state in ObservationState}
        with transaction.atomic():
            batch = PriceImportBatch.objects.create(
                market_code=market_code,
                source=source,
                source_url=source_url,
                checksum_sha256=checksum,
                source_generated_at=source_generated_at,
                observation_count=len(rows),
            )
            for row in rows:
                stored = validate_and_store_observation(
                    ObservationCreate(
                        market_code=market_code,
                        source=source,
                        source_type=SourceType.OFFICIAL_REFERENCE,
                        station=row.station,
                        import_batch=batch,
                        geography_precision=row.geography_precision,
                        geography_id=row.geography_id,
                        fuel_type=row.fuel_type,
                        fuel_grade=row.fuel_grade,
                        unit_price=row.unit_price,
                        observed_at=row.observed_at,
                        effective_at=row.effective_at,
                        expires_at=row.expires_at,
                        evidence={
                            "source_url": source_url,
                            "source_record_id": row.source_record_id,
                            "source_generated_at": source_generated_at.isoformat(),
                            "checksum_sha256": checksum,
                            "import_schema_version": SCHEMA_VERSION,
                        },
                    )
                )
                counts[stored.outcome.state] += 1
            batch.accepted_count = counts[ObservationState.ACCEPTED]
            batch.quarantined_count = counts[ObservationState.QUARANTINED]
            batch.rejected_count = counts[ObservationState.REJECTED]
            batch.save(
                update_fields=(
                    "accepted_count",
                    "quarantined_count",
                    "rejected_count",
                )
            )

        self.stdout.write(
            self.style.SUCCESS(
                f"Imported batch {batch.id} from {len(raw)} bytes: "
                f"{batch.accepted_count} accepted, "
                f"{batch.quarantined_count} quarantined, "
                f"{batch.rejected_count} rejected."
            )
        )


def _approved_manual_source(source_slug: str) -> SourceRegistry:
    try:
        source = SourceRegistry.objects.get(slug=source_slug)
    except SourceRegistry.DoesNotExist as exc:
        raise CommandError("The price source is not registered.") from exc
    approved = source.permission_status.casefold().startswith("approved")
    if (
        not source.enabled
        or not approved
        or not source.permission_evidence.strip()
        or source.purpose != "official_price_reference"
    ):
        raise CommandError(
            f'The source "{source_slug}" is not approved for manual imports.'
        )
    return source


def _read_payload(path):
    try:
        raw = Path(path).read_bytes()
        payload = json.loads(raw)
    except (OSError, json.JSONDecodeError) as exc:
        raise CommandError("The input must be readable JSON.") from exc
    if not isinstance(payload, dict):
        raise CommandError("The import payload must be a JSON object.")
    return raw, payload, hashlib.sha256(raw).hexdigest()


def _validate_header(payload, *, market_code, source):
    if payload.get("schema_version") != SCHEMA_VERSION:
        raise CommandError(f"schema_version must be {SCHEMA_VERSION}.")
    if payload.get("market_code") != market_code:
        raise CommandError("Payload market_code does not match --market-code.")
    if payload.get("source_slug") != source.slug:
        raise CommandError("Payload source_slug does not match --source-slug.")
    if not isinstance(payload.get("observations"), list) or not payload["observations"]:
        raise CommandError("observations must be a non-empty list.")


def _normalize_rows(payload, *, market_code):
    rows = []
    source_record_ids = set()
    for position, value in enumerate(payload["observations"]):
        field = f"observations[{position}]"
        if not isinstance(value, dict):
            raise CommandError(f"{field} must be an object.")
        source_record_id = _required_text(
            value,
            "source_record_id",
            maximum=160,
            prefix=field,
        )
        if source_record_id in source_record_ids:
            raise CommandError(f"{field}.source_record_id is duplicated.")
        source_record_ids.add(source_record_id)
        try:
            precision = GeographicPrecision(value.get("geography_precision"))
            fuel_type = FuelType(value.get("fuel_type"))
        except (TypeError, ValueError) as exc:
            raise CommandError(f"{field} has an unsupported enum value.") from exc
        geography_id = _required_text(
            value,
            "geography_id",
            maximum=160,
            prefix=field,
        )
        station = _station_for_row(
            value,
            market_code=market_code,
            precision=precision,
            geography_id=geography_id,
            field=field,
        )
        rows.append(
            ImportRow(
                source_record_id=source_record_id,
                geography_precision=precision,
                geography_id=geography_id,
                fuel_type=fuel_type,
                fuel_grade=str(value.get("fuel_grade") or "").strip().casefold()[:50],
                unit_price=_unit_price(value.get("unit_price"), field),
                observed_at=_aware_datetime(
                    value.get("observed_at"), f"{field}.observed_at"
                ),
                effective_at=_aware_datetime(
                    value.get("effective_at"), f"{field}.effective_at"
                ),
                expires_at=_aware_datetime(
                    value.get("expires_at"), f"{field}.expires_at"
                ),
                station=station,
            )
        )
        if rows[-1].expires_at <= rows[-1].observed_at:
            raise CommandError(f"{field}.expires_at must follow observed_at.")
    return tuple(rows)


def _station_for_row(value, *, market_code, precision, geography_id, field):
    station_id = str(value.get("station_id") or "").strip()
    if precision != GeographicPrecision.STATION:
        if station_id:
            raise CommandError(f"{field}.station_id requires station precision.")
        return None
    if not station_id or station_id != geography_id:
        raise CommandError(
            f"{field}.station_id must match geography_id for station precision."
        )
    try:
        return FuelStation.objects.select_related("snapshot").get(
            stable_id=station_id,
            snapshot__market_code=market_code,
            snapshot__is_active=True,
            snapshot__is_valid=True,
        )
    except FuelStation.DoesNotExist as exc:
        raise CommandError(
            f"{field}.station_id is not in the active catalogue."
        ) from exc


def _unit_price(value, field):
    try:
        price = Decimal(str(value))
        if not price.is_finite() or price != price.quantize(Decimal("0.001")):
            raise InvalidOperation
    except (InvalidOperation, TypeError, ValueError) as exc:
        raise CommandError(
            f"{field}.unit_price must be a finite decimal with at most 3 places."
        ) from exc
    return price


def _aware_datetime(value, field):
    if not isinstance(value, str):
        raise CommandError(f"{field} must be an ISO-8601 time.")
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError as exc:
        raise CommandError(f"{field} must be an ISO-8601 time.") from exc
    if parsed.tzinfo is None or parsed.utcoffset() is None:
        raise CommandError(f"{field} must include a timezone.")
    return parsed


def _required_text(payload, key, *, maximum, prefix=""):
    value = payload.get(key)
    field = f"{prefix}.{key}" if prefix else key
    if not isinstance(value, str) or not value.strip() or len(value.strip()) > maximum:
        raise CommandError(f"{field} must contain 1 to {maximum} characters.")
    return value.strip()


def _market_code(value):
    market_code = value.strip().upper()
    if len(market_code) != 2 or not market_code.isalpha():
        raise CommandError("--market-code must contain two letters.")
    return market_code
