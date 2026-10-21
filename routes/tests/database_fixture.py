"""Synthetic recovery data, usable with current or historical Django models."""

from datetime import UTC, datetime, timedelta
from decimal import Decimal

from django.apps import apps as current_apps


def seed_recovery_fixture(apps=current_apps):
    def model(name):
        return apps.get_model("routes", name)

    observed_at = datetime(2026, 10, 26, 9, tzinfo=UTC)
    source = model("SourceRegistry").objects.create(
        slug="synthetic-recovery-fixture",
        owner="Synthetic tests",
        purpose="recovery_test",
        terms_url="https://example.invalid/synthetic-fixture",
        permitted_use="Synthetic tests only; no upstream dataset or live prices.",
    )
    snapshot = model("StationSnapshot").objects.create(
        source=source,
        market_code="IN",
        version="synthetic-recovery-v1",
        source_generated_at=observed_at,
        checksum_sha256="a" * 64,
        is_active=True,
        is_valid=True,
        quality_metrics={"station_count": 1, "synthetic": True},
    )
    station = model("FuelStation").objects.create(
        snapshot=snapshot,
        stable_id="synthetic-recovery-station",
        source_id="synthetic/1",
        name="Synthetic recovery station — परीक्षण",
        city="Ahmedabad",
        state="Gujarat",
        latitude=Decimal("23.022500"),
        longitude=Decimal("72.571400"),
        last_seen_at=observed_at,
    )
    model("StationFuel").objects.create(station=station, fuel_type="petrol")
    batch = model("PriceImportBatch").objects.create(
        market_code="IN",
        source=source,
        source_url="https://example.invalid/synthetic-fixture",
        checksum_sha256="b" * 64,
        source_generated_at=observed_at,
        observation_count=1,
        accepted_count=1,
    )
    observation = model("PriceObservation").objects.create(
        market_code="IN",
        station=station,
        import_batch=batch,
        geography_precision="station",
        geography_id=station.stable_id,
        fuel_type="petrol",
        unit_price=Decimal("101.250"),
        source=source,
        source_type="community_report",
        observed_at=observed_at,
        effective_at=observed_at,
        expires_at=observed_at + timedelta(hours=24),
        state="accepted",
        contributor_id="synthetic-contributor",
        evidence={"synthetic": True},
    )
    model("PriceModerationEvent").objects.create(
        observation=observation,
        actor_id="synthetic-moderator",
        action="accept",
        reason_code="synthetic_fixture",
        previous_state="pending",
        new_state="accepted",
    )
    model("ContributionReceipt").objects.create(
        observation=observation,
        receipt_hash="c" * 64,
        idempotency_hash="d" * 64,
        payload_hash="e" * 64,
        contributor_id="synthetic-contributor",
        expires_at=observed_at + timedelta(days=30),
    )
    model("ObservationWatermark").objects.create(scope="global", version=42)
