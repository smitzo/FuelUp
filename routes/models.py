from decimal import Decimal

from django.core.validators import MaxValueValidator, MinValueValidator
from django.db import models
from django.db.models import F, Q

from routes.domain.fuel_data import (
    FuelType,
    GeographicPrecision,
    ObservationState,
    OperatingStatus,
    SourceType,
)


def _choices(enum_class):
    return [(item.value, item.name.replace("_", " ").title()) for item in enum_class]


class SourceRegistry(models.Model):
    slug = models.SlugField(primary_key=True, max_length=80)
    owner = models.CharField(max_length=200)
    purpose = models.CharField(max_length=100)
    terms_url = models.URLField(max_length=500)
    permission_status = models.CharField(max_length=50, default="unresolved")
    permission_evidence = models.TextField(blank=True)
    permitted_use = models.TextField()
    attribution = models.TextField(blank=True)
    automated_access_allowed = models.BooleanField(default=False)
    enabled = models.BooleanField(default=False)
    refresh_budget_per_day = models.PositiveIntegerField(default=0)
    retention_policy = models.TextField(blank=True)
    reviewed_at = models.DateTimeField(null=True, blank=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ("slug",)

    @property
    def can_fetch(self):
        return self.enabled and self.automated_access_allowed


class StationSnapshot(models.Model):
    source = models.ForeignKey(SourceRegistry, on_delete=models.PROTECT)
    market_code = models.CharField(max_length=2)
    version = models.CharField(max_length=120)
    source_generated_at = models.DateTimeField()
    imported_at = models.DateTimeField(auto_now_add=True)
    checksum_sha256 = models.CharField(max_length=64)
    is_active = models.BooleanField(default=False)
    is_valid = models.BooleanField(default=False)
    quality_metrics = models.JSONField(default=dict)

    class Meta:
        ordering = ("-source_generated_at", "-id")
        constraints = [
            models.UniqueConstraint(
                fields=("market_code",),
                condition=Q(is_active=True),
                name="one_active_snapshot_per_market",
            ),
            models.UniqueConstraint(
                fields=("market_code", "version"),
                name="unique_snapshot_version_per_market",
            ),
        ]


class FuelStation(models.Model):
    snapshot = models.ForeignKey(
        StationSnapshot,
        on_delete=models.CASCADE,
        related_name="stations",
    )
    stable_id = models.CharField(max_length=120)
    source_id = models.CharField(max_length=120)
    name = models.CharField(max_length=300)
    brand = models.CharField(max_length=150, blank=True)
    address = models.CharField(max_length=500, blank=True)
    city = models.CharField(max_length=120, blank=True)
    district = models.CharField(max_length=120, blank=True)
    state = models.CharField(max_length=120, blank=True)
    postcode = models.CharField(max_length=20, blank=True)
    latitude = models.DecimalField(max_digits=9, decimal_places=6)
    longitude = models.DecimalField(max_digits=9, decimal_places=6)
    coordinate_precision = models.CharField(
        max_length=20,
        choices=_choices(GeographicPrecision),
        default=GeographicPrecision.STATION,
    )
    operating_status = models.CharField(
        max_length=20,
        choices=_choices(OperatingStatus),
        default=OperatingStatus.UNKNOWN,
    )
    source_tags = models.JSONField(default=dict)
    last_seen_at = models.DateTimeField()

    class Meta:
        ordering = ("stable_id",)
        constraints = [
            models.UniqueConstraint(
                fields=("snapshot", "stable_id"),
                name="unique_station_per_snapshot",
            ),
            models.UniqueConstraint(
                fields=("snapshot", "source_id"),
                name="unique_station_source_per_snapshot",
            ),
        ]
        indexes = [
            models.Index(fields=("snapshot", "state", "city")),
            models.Index(fields=("snapshot", "latitude", "longitude")),
        ]


class StationFuel(models.Model):
    station = models.ForeignKey(
        FuelStation,
        on_delete=models.CASCADE,
        related_name="fuels",
    )
    fuel_type = models.CharField(max_length=20, choices=_choices(FuelType))
    grade = models.CharField(max_length=50, blank=True)
    is_available = models.BooleanField(default=True)
    is_inferred = models.BooleanField(default=False)

    class Meta:
        ordering = ("station_id", "fuel_type", "grade")
        constraints = [
            models.UniqueConstraint(
                fields=("station", "fuel_type", "grade"),
                name="unique_station_fuel_grade",
            )
        ]


class PriceImportBatch(models.Model):
    market_code = models.CharField(max_length=2)
    source = models.ForeignKey(SourceRegistry, on_delete=models.PROTECT)
    source_url = models.URLField(max_length=1000)
    checksum_sha256 = models.CharField(max_length=64)
    source_generated_at = models.DateTimeField()
    imported_at = models.DateTimeField(auto_now_add=True)
    observation_count = models.PositiveIntegerField(default=0)
    accepted_count = models.PositiveIntegerField(default=0)
    quarantined_count = models.PositiveIntegerField(default=0)
    rejected_count = models.PositiveIntegerField(default=0)

    class Meta:
        ordering = ("-imported_at", "-id")
        constraints = [
            models.UniqueConstraint(
                fields=("market_code", "source", "checksum_sha256"),
                name="unique_price_import_checksum",
            )
        ]


class PriceObservation(models.Model):
    market_code = models.CharField(max_length=2)
    station = models.ForeignKey(
        FuelStation,
        on_delete=models.PROTECT,
        related_name="price_observations",
        null=True,
        blank=True,
    )
    import_batch = models.ForeignKey(
        PriceImportBatch,
        on_delete=models.PROTECT,
        related_name="observations",
        null=True,
        blank=True,
    )
    supersedes = models.ForeignKey(
        "self",
        on_delete=models.PROTECT,
        related_name="superseding_observations",
        null=True,
        blank=True,
    )
    geography_precision = models.CharField(
        max_length=20,
        choices=_choices(GeographicPrecision),
    )
    geography_id = models.CharField(max_length=160)
    fuel_type = models.CharField(max_length=20, choices=_choices(FuelType))
    fuel_grade = models.CharField(max_length=50, blank=True)
    unit_price = models.DecimalField(
        max_digits=8,
        decimal_places=3,
        validators=[
            MinValueValidator(Decimal("0.001")),
            MaxValueValidator(Decimal("99999")),
        ],
    )
    source = models.ForeignKey(SourceRegistry, on_delete=models.PROTECT)
    source_type = models.CharField(max_length=30, choices=_choices(SourceType))
    observed_at = models.DateTimeField()
    effective_at = models.DateTimeField()
    received_at = models.DateTimeField(auto_now_add=True)
    expires_at = models.DateTimeField()
    state = models.CharField(
        max_length=20,
        choices=_choices(ObservationState),
        default=ObservationState.PENDING,
    )
    contributor_id = models.CharField(max_length=128, blank=True)
    evidence = models.JSONField(default=dict)
    validation_reason = models.CharField(max_length=200, blank=True)

    class Meta:
        ordering = ("-observed_at", "-id")
        constraints = [
            models.CheckConstraint(
                condition=Q(unit_price__gt=0),
                name="price_observation_positive",
            ),
            models.CheckConstraint(
                condition=Q(expires_at__gt=F("observed_at")),
                name="price_observation_expiry_after_observation",
            ),
        ]
        indexes = [
            models.Index(
                fields=(
                    "market_code",
                    "station",
                    "fuel_type",
                    "fuel_grade",
                    "state",
                ),
                name="price_station_fuel_state_idx",
            ),
            models.Index(
                fields=(
                    "market_code",
                    "geography_precision",
                    "geography_id",
                    "fuel_type",
                ),
                name="price_geography_fuel_idx",
            ),
            models.Index(fields=("expires_at", "state")),
        ]


class PriceModerationEvent(models.Model):
    observation = models.ForeignKey(
        PriceObservation,
        on_delete=models.PROTECT,
        related_name="moderation_events",
    )
    actor_id = models.CharField(max_length=128)
    action = models.CharField(max_length=30)
    reason_code = models.CharField(max_length=80)
    previous_state = models.CharField(
        max_length=20,
        choices=_choices(ObservationState),
    )
    new_state = models.CharField(
        max_length=20,
        choices=_choices(ObservationState),
    )
    created_at = models.DateTimeField(auto_now_add=True)
    metadata = models.JSONField(default=dict)

    class Meta:
        ordering = ("created_at", "id")


class ContributionReceipt(models.Model):
    observation = models.OneToOneField(
        PriceObservation,
        on_delete=models.PROTECT,
        related_name="contribution_receipt",
    )
    receipt_hash = models.CharField(max_length=64, unique=True)
    idempotency_hash = models.CharField(max_length=64, unique=True)
    payload_hash = models.CharField(max_length=64, default="")
    contributor_id = models.CharField(max_length=128)
    created_at = models.DateTimeField(auto_now_add=True)
    expires_at = models.DateTimeField()

    class Meta:
        ordering = ("-created_at", "-id")
        indexes = [models.Index(fields=("expires_at",))]


class ObservationWatermark(models.Model):
    scope = models.CharField(primary_key=True, max_length=80, default="global")
    version = models.PositiveBigIntegerField(default=0)
    updated_at = models.DateTimeField(auto_now=True)
