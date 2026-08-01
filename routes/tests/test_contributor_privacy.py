from datetime import UTC, datetime

from django.test import SimpleTestCase, override_settings

from routes.application.contributor_privacy import (
    contribution_payload_hash,
    derive_contributor_identity,
    derive_receipt_material,
    receipt_hash,
)


@override_settings(CONTRIBUTION_HASH_SECRET="test-only-contribution-secret")
class ContributorPrivacyTests(SimpleTestCase):
    def test_identity_is_deterministic_without_containing_raw_identifiers(self):
        values = {
            "market_code": "GB",
            "device_id": "device-token-12345678",
            "network_address": "192.0.2.25",
            "at": datetime(2026, 8, 10, tzinfo=UTC),
        }

        first = derive_contributor_identity(**values)
        second = derive_contributor_identity(**values)

        self.assertEqual(first, second)
        self.assertNotIn(values["device_id"], first.contributor_id)
        self.assertNotIn(values["network_address"], first.network_hash)
        self.assertEqual(len(first.device_hash), 64)

    def test_contributor_and_network_pseudonyms_rotate(self):
        values = {
            "market_code": "GB",
            "device_id": "device-token-12345678",
            "network_address": "2001:db8::1",
        }

        august = derive_contributor_identity(
            **values, at=datetime(2026, 8, 31, tzinfo=UTC)
        )
        september = derive_contributor_identity(
            **values, at=datetime(2026, 9, 1, tzinfo=UTC)
        )

        self.assertNotEqual(august.contributor_id, september.contributor_id)
        self.assertNotEqual(august.network_hash, september.network_hash)
        self.assertEqual(august.device_hash, september.device_hash)

    def test_receipt_is_deterministic_and_only_its_hash_needs_storage(self):
        material = derive_receipt_material(
            market_code="GB",
            contributor_id="contributor-hash",
            idempotency_key="submission-key-123456",
        )

        self.assertEqual(receipt_hash(material.token), material.receipt_hash)
        self.assertNotEqual(material.token, material.receipt_hash)
        self.assertEqual(len(material.idempotency_hash), 64)

    def test_payload_hash_is_canonical(self):
        self.assertEqual(
            contribution_payload_hash({"price": "100", "station": "a"}),
            contribution_payload_hash({"station": "a", "price": "100"}),
        )

    def test_rejects_unsafe_device_and_receipt_values(self):
        with self.assertRaises(ValueError):
            derive_contributor_identity(
                market_code="GB",
                device_id="too-short",
                network_address="192.0.2.1",
            )
        with self.assertRaises(ValueError):
            receipt_hash("not-a-receipt")
