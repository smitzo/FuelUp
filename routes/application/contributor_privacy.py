import hashlib
import hmac
import ipaddress
import json
import re
from dataclasses import dataclass
from datetime import datetime

from django.conf import settings
from django.utils import timezone

DEVICE_PATTERN = re.compile(r"^[A-Za-z0-9._-]{16,128}$")
IDEMPOTENCY_PATTERN = re.compile(r"^[A-Za-z0-9._:-]{16,128}$")


@dataclass(frozen=True, slots=True)
class ContributorIdentity:
    contributor_id: str
    device_hash: str
    network_hash: str
    rotation_period: str


@dataclass(frozen=True, slots=True)
class ReceiptMaterial:
    token: str
    receipt_hash: str
    idempotency_hash: str


def derive_contributor_identity(
    *,
    market_code: str,
    device_id: str,
    network_address: str,
    at: datetime | None = None,
) -> ContributorIdentity:
    at = at or timezone.now()
    if not DEVICE_PATTERN.fullmatch(device_id):
        raise ValueError(
            "Device identifier must contain 16 to 128 letters, numbers, dots, "
            "underscores, or hyphens."
        )
    try:
        normalized_network = ipaddress.ip_address(network_address).compressed
    except ValueError as exc:
        raise ValueError("Network address is invalid.") from exc
    rotation_period = at.strftime("%Y-%m")
    network_period = at.strftime("%Y-%m-%d")
    normalized_market = market_code.strip().upper()
    return ContributorIdentity(
        contributor_id=_digest(
            "contributor",
            normalized_market,
            rotation_period,
            device_id,
        ),
        device_hash=_digest("device", normalized_market, device_id),
        network_hash=_digest(
            "network",
            normalized_market,
            network_period,
            normalized_network,
        ),
        rotation_period=rotation_period,
    )


def derive_receipt_material(
    *,
    market_code: str,
    contributor_id: str,
    idempotency_key: str,
) -> ReceiptMaterial:
    if not IDEMPOTENCY_PATTERN.fullmatch(idempotency_key):
        raise ValueError("Idempotency key must contain 16 to 128 safe characters.")
    idempotency_hash = _digest(
        "idempotency",
        market_code.strip().upper(),
        contributor_id,
        idempotency_key,
    )
    token = _digest("receipt-token", idempotency_hash)
    return ReceiptMaterial(
        token=token,
        receipt_hash=hashlib.sha256(token.encode()).hexdigest(),
        idempotency_hash=idempotency_hash,
    )


def contribution_payload_hash(payload: dict) -> str:
    encoded = json.dumps(
        payload,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=True,
    )
    return _digest("payload", encoded)


def receipt_hash(token: str) -> str:
    if not hmac.compare_digest(token, token.strip()) or len(token) != 64:
        raise ValueError("Receipt is invalid.")
    try:
        bytes.fromhex(token)
    except ValueError as exc:
        raise ValueError("Receipt is invalid.") from exc
    return hashlib.sha256(token.encode()).hexdigest()


def _digest(purpose: str, *values: str) -> str:
    secret = settings.CONTRIBUTION_HASH_SECRET.encode()
    message = "\x1f".join((purpose, *values)).encode()
    return hmac.new(secret, message, hashlib.sha256).hexdigest()
