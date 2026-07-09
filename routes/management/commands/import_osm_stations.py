import hashlib
import json
from datetime import datetime
from decimal import Decimal, InvalidOperation
from pathlib import Path

from django.conf import settings
from django.core.management.base import BaseCommand, CommandError
from django.db import transaction

from routes.domain.fuel_data import FuelType, GeographicPrecision
from routes.models import (
    FuelStation,
    SourceRegistry,
    StationFuel,
    StationSnapshot,
)


class Command(BaseCommand):
    help = "Import a filtered OSM fuel-station GeoJSON snapshot for a market."

    def add_arguments(self, parser):
        parser.add_argument("input_path")
        parser.add_argument("--snapshot-version", required=True)
        parser.add_argument("--generated-at", required=True)
        parser.add_argument(
            "--market-code",
            default=settings.MARKET_CONFIG["code"],
        )
        parser.add_argument(
            "--source-slug",
            default=settings.MARKET_CONFIG["station_source_slug"],
        )
        parser.add_argument("--activate", action="store_true")
        parser.add_argument("--infer-common-fuels", action="store_true")

    def handle(self, *args, **options):
        market_code = options["market_code"].strip().upper()
        if len(market_code) != 2:
            raise CommandError("--market-code must contain two letters.")
        source = self._source(options["source_slug"])
        raw, payload, checksum = self._read_payload(options["input_path"])
        generated_at = self._generated_at(options["generated_at"])
        snapshot_version = options["snapshot_version"]
        existing = StationSnapshot.objects.filter(
            market_code=market_code,
            version=snapshot_version,
        ).first()
        if existing:
            if existing.checksum_sha256 != checksum:
                raise CommandError(
                    "The snapshot version already exists with another checksum."
                )
            if options["activate"] and existing.is_valid:
                with transaction.atomic():
                    StationSnapshot.objects.filter(
                        market_code=market_code,
                        is_active=True,
                    ).update(is_active=False)
                    existing.is_active = True
                    existing.save(update_fields=("is_active",))
            self.stdout.write(
                self.style.WARNING(
                    f"Snapshot {existing.version} already imported; no changes made."
                )
            )
            return

        stations, fuels, metrics = _normalize_features(
            payload,
            infer_common_fuels=options["infer_common_fuels"],
            last_seen_at=generated_at,
        )
        if not stations:
            raise CommandError("The GeoJSON contains no valid fuel stations.")

        with transaction.atomic():
            snapshot = StationSnapshot.objects.create(
                source=source,
                market_code=market_code,
                version=snapshot_version,
                source_generated_at=generated_at,
                checksum_sha256=checksum,
                is_valid=True,
                quality_metrics=metrics,
            )
            station_models = [
                FuelStation(snapshot=snapshot, **station) for station in stations
            ]
            FuelStation.objects.bulk_create(station_models, batch_size=1000)
            station_ids = {
                station.stable_id: station
                for station in FuelStation.objects.filter(snapshot=snapshot)
            }
            StationFuel.objects.bulk_create(
                [
                    StationFuel(station=station_ids[stable_id], **fuel)
                    for stable_id, fuel in fuels
                ],
                batch_size=2000,
            )
            if options["activate"]:
                StationSnapshot.objects.filter(
                    market_code=market_code,
                    is_active=True,
                ).update(is_active=False)
                snapshot.is_active = True
                snapshot.save(update_fields=("is_active",))

        self.stdout.write(
            self.style.SUCCESS(
                f"Imported {metrics['station_count']} {market_code} fuel "
                f"stations from {len(raw)} bytes as {snapshot_version}."
            )
        )

    @staticmethod
    def _source(source_slug):
        try:
            source = SourceRegistry.objects.get(slug=source_slug)
        except SourceRegistry.DoesNotExist as exc:
            raise CommandError(
                "Run sync_source_registry before importing stations."
            ) from exc
        if not source.can_fetch:
            raise CommandError(f'The source "{source_slug}" is not enabled.')
        return source

    @staticmethod
    def _read_payload(path):
        try:
            raw = Path(path).read_bytes()
            payload = json.loads(raw)
        except (OSError, json.JSONDecodeError) as exc:
            raise CommandError("The input must be readable GeoJSON.") from exc
        if payload.get("type") != "FeatureCollection" or not isinstance(
            payload.get("features"), list
        ):
            raise CommandError("Expected a GeoJSON FeatureCollection.")
        return raw, payload, hashlib.sha256(raw).hexdigest()

    @staticmethod
    def _generated_at(value):
        try:
            parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
        except ValueError as exc:
            raise CommandError("--generated-at must be an ISO-8601 time.") from exc
        if parsed.tzinfo is None:
            raise CommandError("--generated-at must include a timezone.")
        return parsed


def _normalize_features(payload, *, infer_common_fuels, last_seen_at):
    stations = []
    fuels = []
    seen = set()
    metrics = {
        "input_feature_count": len(payload["features"]),
        "station_count": 0,
        "invalid_feature_count": 0,
        "duplicate_count": 0,
        "named_count": 0,
        "addressed_count": 0,
        "fuel_tagged_count": 0,
        "fuel_inferred_count": 0,
    }
    for feature in payload["features"]:
        normalized = _normalize_feature(
            feature,
            infer_common_fuels,
            last_seen_at,
        )
        if normalized is None:
            metrics["invalid_feature_count"] += 1
            continue
        station, station_fuels = normalized
        if station["stable_id"] in seen:
            metrics["duplicate_count"] += 1
            continue
        seen.add(station["stable_id"])
        stations.append(station)
        fuels.extend(
            (station["stable_id"], fuel) for fuel in station_fuels
        )
        metrics["named_count"] += bool(station["name"] != "Unnamed fuel station")
        metrics["addressed_count"] += bool(station["address"])
        if any(not fuel["is_inferred"] for fuel in station_fuels):
            metrics["fuel_tagged_count"] += 1
        if any(fuel["is_inferred"] for fuel in station_fuels):
            metrics["fuel_inferred_count"] += 1
    metrics["station_count"] = len(stations)
    return stations, fuels, metrics


def _normalize_feature(feature, infer_common_fuels, last_seen_at):
    if feature.get("type") != "Feature":
        return None
    properties = feature.get("properties") or {}
    if properties.get("amenity") != "fuel":
        return None
    source_id = str(properties.get("@id") or feature.get("id") or "").strip()
    coordinates = _representative_coordinate(feature.get("geometry") or {})
    if not source_id or coordinates is None:
        return None
    longitude, latitude = coordinates
    if not (-180 <= longitude <= 180 and -90 <= latitude <= 90):
        return None
    stable_id = f"osm-{source_id.replace('/', '-')}"
    fuel_rows = _fuel_rows(properties, infer_common_fuels)
    address = ", ".join(
        value
        for value in (
            properties.get("addr:housenumber"),
            properties.get("addr:street"),
        )
        if value
    )
    return (
        {
            "stable_id": stable_id,
            "source_id": source_id,
            "name": str(properties.get("name") or "Unnamed fuel station")[:300],
            "brand": str(properties.get("brand") or "")[:150],
            "address": address[:500],
            "city": str(properties.get("addr:city") or "")[:120],
            "district": str(properties.get("addr:district") or "")[:120],
            "state": str(properties.get("addr:state") or "")[:120],
            "postcode": str(properties.get("addr:postcode") or "")[:20],
            "latitude": Decimal(str(latitude)).quantize(Decimal("0.000001")),
            "longitude": Decimal(str(longitude)).quantize(Decimal("0.000001")),
            "coordinate_precision": GeographicPrecision.STATION,
            "source_tags": properties,
            "last_seen_at": last_seen_at,
        },
        fuel_rows,
    )


def _fuel_rows(properties, infer_common_fuels):
    rows = []
    diesel = _truthy(properties.get("fuel:diesel"))
    petrol = _truthy(properties.get("fuel:petrol")) or any(
        _truthy(value)
        for key, value in properties.items()
        if key.startswith("fuel:octane_")
    )
    if petrol:
        rows.append(
            {"fuel_type": FuelType.PETROL, "grade": "", "is_inferred": False}
        )
    if diesel:
        rows.append(
            {"fuel_type": FuelType.DIESEL, "grade": "", "is_inferred": False}
        )
    if not rows and infer_common_fuels:
        rows.extend(
            {
                "fuel_type": fuel_type,
                "grade": "",
                "is_inferred": True,
            }
            for fuel_type in (FuelType.PETROL, FuelType.DIESEL)
        )
    return rows


def _representative_coordinate(geometry):
    coordinates = geometry.get("coordinates")
    if geometry.get("type") == "Point":
        return _coordinate_pair(coordinates)
    pairs = list(_coordinate_pairs(coordinates))
    if not pairs:
        return None
    return (
        sum(pair[0] for pair in pairs) / len(pairs),
        sum(pair[1] for pair in pairs) / len(pairs),
    )


def _coordinate_pairs(value):
    pair = _coordinate_pair(value)
    if pair is not None:
        yield pair
        return
    if isinstance(value, list):
        for child in value:
            yield from _coordinate_pairs(child)


def _coordinate_pair(value):
    if not isinstance(value, list) or len(value) < 2:
        return None
    try:
        longitude = float(value[0])
        latitude = float(value[1])
    except (TypeError, ValueError, InvalidOperation):
        return None
    return longitude, latitude


def _truthy(value):
    return str(value).strip().casefold() in {"yes", "true", "1"}
