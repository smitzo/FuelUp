import json
from datetime import timedelta
from io import StringIO
from pathlib import Path
from tempfile import TemporaryDirectory

from django.core.management import call_command
from django.core.management.base import CommandError
from django.test import TestCase
from django.utils import timezone

from routes.domain.fuel_data import (
    GeographicPrecision,
    ObservationState,
    SourceType,
)
from routes.models import PriceImportBatch, PriceObservation, SourceRegistry


class ImportPriceObservationsTests(TestCase):
    def setUp(self):
        self.source = SourceRegistry.objects.create(
            slug="approved-reference",
            owner="Public reference publisher",
            purpose="official_price_reference",
            terms_url="https://example.com/reference-terms",
            permission_status="approved_for_manual_import",
            permission_evidence="Recorded permission for a local snapshot import.",
            permitted_use="Import and display dated reference prices.",
            attribution="Public reference publisher.",
            automated_access_allowed=False,
            enabled=True,
        )
        now = timezone.now()
        self.payload = {
            "schema_version": 1,
            "market_code": "GB",
            "source_slug": self.source.slug,
            "source_url": "https://example.com/reference-snapshot",
            "source_generated_at": now.isoformat(),
            "observations": [
                {
                    "source_record_id": "city-a-petrol-20260810",
                    "geography_precision": "city",
                    "geography_id": "city-a",
                    "fuel_type": "petrol",
                    "fuel_grade": "",
                    "unit_price": "100.125",
                    "observed_at": now.isoformat(),
                    "effective_at": now.isoformat(),
                    "expires_at": (now + timedelta(hours=36)).isoformat(),
                }
            ],
        }

    def test_import_is_auditable_and_checksum_idempotent(self):
        with TemporaryDirectory() as directory:
            path = Path(directory) / "price-reference.json"
            path.write_text(json.dumps(self.payload), encoding="utf-8")
            output = StringIO()
            options = {
                "source_slug": self.source.slug,
                "market_code": "GB",
                "stdout": output,
            }

            call_command("import_price_observations", str(path), **options)
            call_command("import_price_observations", str(path), **options)

        batch = PriceImportBatch.objects.get()
        observation = PriceObservation.objects.get()
        self.assertEqual(batch.accepted_count, 1)
        self.assertEqual(observation.state, ObservationState.ACCEPTED)
        self.assertEqual(observation.source_type, SourceType.OFFICIAL_REFERENCE)
        self.assertEqual(
            observation.geography_precision,
            GeographicPrecision.CITY,
        )
        self.assertIsNone(observation.station)
        self.assertEqual(
            observation.evidence["source_record_id"],
            "city-a-petrol-20260810",
        )
        self.assertIn("already exists", output.getvalue())

    def test_disabled_source_fails_before_input_is_read(self):
        self.source.enabled = False
        self.source.save(update_fields=("enabled",))

        with self.assertRaisesRegex(CommandError, "not approved"):
            call_command(
                "import_price_observations",
                "/path/that/does/not/exist.json",
                source_slug=self.source.slug,
                market_code="GB",
            )

    def test_invalid_payload_rolls_back_without_partial_batch(self):
        self.payload["observations"].append(
            {
                **self.payload["observations"][0],
                "source_record_id": "second",
                "unit_price": "NaN",
            }
        )
        with TemporaryDirectory() as directory:
            path = Path(directory) / "invalid-price-reference.json"
            path.write_text(json.dumps(self.payload), encoding="utf-8")

            with self.assertRaisesRegex(CommandError, "finite decimal"):
                call_command(
                    "import_price_observations",
                    str(path),
                    source_slug=self.source.slug,
                    market_code="GB",
                )

        self.assertFalse(PriceImportBatch.objects.exists())
        self.assertFalse(PriceObservation.objects.exists())
