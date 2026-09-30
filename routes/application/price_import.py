import hashlib
import json
from collections import Counter
from dataclasses import asdict

from django.conf import settings
from django.db import transaction

from routes.application.observations import (
    ObservationCreate,
    validate_and_store_observation,
)
from routes.domain.exceptions import ExternalServiceError
from routes.domain.fuel_data import ObservationState, SourceType
from routes.models import PriceImportBatch, SourceRegistry


@transaction.atomic
def import_provider_prices(source_slug, prices):
    source = SourceRegistry.objects.select_for_update().get(slug=source_slug)
    if (
        not source.can_fetch
        or not source._has_approved_terms
        or source.purpose != "third_party_price_reference"
    ):
        raise ExternalServiceError(
            "Price source is not approved for automated imports."
        )
    prices = tuple(prices)
    if not prices:
        raise ValueError("An empty price snapshot cannot be imported.")
    canonical = sorted(
        (asdict(price) for price in prices),
        key=lambda item: (item["geography_id"], item["fuel_type"]),
    )
    encoded = json.dumps(canonical, sort_keys=True, default=str).encode()
    checksum = hashlib.sha256(encoded).hexdigest()
    existing = PriceImportBatch.objects.filter(
        market_code="IN", source=source, checksum_sha256=checksum
    ).first()
    if existing:
        return existing, False
    source_url = settings.API_MITRA_BASE_URL.rstrip("/") + "/fuel"
    batch = PriceImportBatch.objects.create(
        market_code="IN",
        source=source,
        source_url=source_url,
        checksum_sha256=checksum,
        source_generated_at=max(price.observed_at for price in prices),
        observation_count=len(prices),
    )
    counts = Counter()
    for price in prices:
        stored = validate_and_store_observation(
            ObservationCreate(
                market_code="IN",
                source=source,
                source_type=SourceType.THIRD_PARTY_REFERENCE,
                geography_precision=price.precision,
                geography_id=price.geography_id,
                fuel_type=price.fuel_type,
                fuel_grade="",
                unit_price=price.unit_price,
                observed_at=price.observed_at,
                effective_at=price.effective_at,
                expires_at=price.expires_at,
                import_batch=batch,
                evidence={
                    "source_url": source_url,
                    "checksum_sha256": checksum,
                    "timestamp_semantics": "provider_row_crawl_time",
                },
            )
        )
        counts[stored.outcome.state] += 1
    batch.accepted_count = counts[ObservationState.ACCEPTED]
    batch.quarantined_count = counts[ObservationState.QUARANTINED]
    batch.rejected_count = counts[ObservationState.REJECTED]
    batch.save(update_fields=("accepted_count", "quarantined_count", "rejected_count"))
    return batch, True
