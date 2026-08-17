"""Payment authorization schema — ISO 8583 / EMV / 3-D Secure 2 inspired.

All data produced against this schema is SYNTHETIC. No field ever holds a real PAN,
real PII, or production payment data (competition Rules §3a).

Card identifiers are synthetic network-style tokens, never PANs — mirroring how a real
tokenized authorization flow works, and making real-card data structurally impossible.
"""

from __future__ import annotations

from enum import StrEnum

SCHEMA_VERSION = "1.0"


class Channel(StrEnum):
    ECOM = "ECOM"          # card-not-present e-commerce
    POS = "POS"            # card-present point of sale
    ATM = "ATM"            # cash withdrawal
    MOTO = "MOTO"          # mail order / telephone order
    RECURRING = "RECURRING"


class EntryMode(StrEnum):
    """ISO 8583 DE22-style point-of-service entry mode."""
    CHIP = "CHIP"                  # 05 - contact EMV
    CONTACTLESS = "CONTACTLESS"    # 07 - contactless EMV
    MAGSTRIPE = "MAGSTRIPE"        # 90 - fallback, elevated risk
    ECOM_KEYED = "ECOM_KEYED"      # 81 - PAN keyed, e-commerce
    NETWORK_TOKEN = "NETWORK_TOKEN"  # tokenized credential
    CREDENTIAL_ON_FILE = "CREDENTIAL_ON_FILE"


class AvsResult(StrEnum):
    """Address Verification Service response."""
    FULL_MATCH = "Y"
    ZIP_ONLY = "Z"
    ADDRESS_ONLY = "A"
    NO_MATCH = "N"
    UNAVAILABLE = "U"
    NOT_REQUESTED = "X"


class CvvResult(StrEnum):
    MATCH = "M"
    NO_MATCH = "N"
    NOT_PROCESSED = "P"
    NOT_PROVIDED = "S"


class ThreeDsStatus(StrEnum):
    """3-D Secure 2.x transaction status (ARes/RReq transStatus)."""
    AUTHENTICATED = "Y"           # frictionless or successful challenge
    ATTEMPTED = "A"               # attempted, issuer not participating
    FAILED = "N"
    CHALLENGE_REQUIRED = "C"
    NOT_AUTHENTICATED = "U"
    NOT_APPLICABLE = "X"          # out of scope (e.g. MOTO, recurring)


class ScaExemption(StrEnum):
    """PSD2 strong-customer-authentication exemption claimed by the acquirer."""
    NONE = "NONE"
    LOW_VALUE = "LOW_VALUE"                  # under low-value threshold
    TRA = "TRA"                              # transaction risk analysis
    TRUSTED_BENEFICIARY = "TRUSTED_BENEFICIARY"
    RECURRING = "RECURRING"
    CORPORATE = "CORPORATE"


class AuthResponse(StrEnum):
    APPROVED = "00"
    DO_NOT_HONOR = "05"
    INSUFFICIENT_FUNDS = "51"
    INVALID_CVV = "82"
    EXPIRED_CARD = "54"
    SUSPECTED_FRAUD = "59"
    EXCEEDS_LIMIT = "61"


# Merchant category codes — realistic subset with distinct risk/behaviour profiles.
# (mcc, label, typical_ticket, is_high_risk, card_present_bias)
MCC_CATALOG: list[tuple[str, str, float, bool, float]] = [
    ("5411", "Grocery Stores", 62.0, False, 0.85),
    ("5812", "Eating Places / Restaurants", 41.0, False, 0.80),
    ("5814", "Fast Food", 14.0, False, 0.88),
    ("5541", "Service Stations", 48.0, False, 0.92),
    ("5912", "Drug Stores / Pharmacies", 31.0, False, 0.78),
    ("5691", "Clothing Stores", 88.0, False, 0.55),
    ("5732", "Electronics Stores", 310.0, True, 0.45),
    ("5999", "Misc Retail", 57.0, False, 0.50),
    ("4111", "Local Transit", 9.0, False, 0.75),
    ("4121", "Taxi / Rideshare", 22.0, False, 0.05),
    ("4511", "Airlines", 420.0, True, 0.08),
    ("7011", "Lodging / Hotels", 265.0, True, 0.35),
    ("5967", "Direct Marketing / Inbound Tele", 75.0, True, 0.00),
    ("6011", "ATM Cash Disbursement", 180.0, False, 1.00),
    ("6012", "Financial Institutions", 240.0, True, 0.10),
    ("7995", "Gambling / Betting", 130.0, True, 0.00),
    ("5816", "Digital Goods / Games", 27.0, True, 0.00),
    ("4899", "Cable / Streaming Services", 16.0, False, 0.00),
    ("5045", "Computers / Peripherals", 520.0, True, 0.20),
    ("5944", "Jewelry / Watches", 640.0, True, 0.40),
    ("7372", "Software / SaaS", 45.0, False, 0.00),
    ("4814", "Telecom / Prepaid Top-up", 25.0, True, 0.00),
]

HIGH_RISK_MCCS = frozenset(m[0] for m in MCC_CATALOG if m[3])

# Country codes (ISO 3166-1 alpha-2) with rough issuing weight for the synthetic population.
COUNTRIES: list[tuple[str, float]] = [
    ("IN", 0.34), ("US", 0.20), ("GB", 0.10), ("AE", 0.07), ("SG", 0.06),
    ("DE", 0.05), ("AU", 0.04), ("BR", 0.04), ("ZA", 0.03), ("JP", 0.03),
    ("NG", 0.02), ("PH", 0.02),
]

CURRENCY_BY_COUNTRY = {
    "IN": "INR", "US": "USD", "GB": "GBP", "AE": "AED", "SG": "SGD",
    "DE": "EUR", "AU": "AUD", "BR": "BRL", "ZA": "ZAR", "JP": "JPY",
    "NG": "NGN", "PH": "PHP",
}

# Columns emitted by the generator, in order. Kept explicit so the API contract,
# the feature layer and the UI all agree on one source of truth.
TRANSACTION_FIELDS: tuple[str, ...] = (
    # --- identity / routing ---
    "transaction_id",
    "timestamp",
    "card_token",          # synthetic network token, NEVER a PAN
    "account_id",
    "issuer_country",
    # --- money ---
    "amount",
    "currency",
    "amount_local",        # amount in the cardholder's home currency, for comparability
    # --- acceptance side ---
    "merchant_id",
    "merchant_name",
    "mcc",
    "merchant_country",
    "merchant_age_days",
    # --- how the credential was presented ---
    "channel",
    "entry_mode",
    "card_present",
    "is_recurring",
    # --- device / network telemetry ---
    "device_id",
    "ip_prefix",           # /24 only — no full synthetic IP retained
    "user_agent_hash",
    # --- verification results ---
    "avs_result",
    "cvv_result",
    "three_ds_status",
    "sca_exemption",
    "network_token_used",
    "cross_border",
    # --- outcome ---
    "auth_response",
    # --- ground truth (synthetic only; never present in a real auth message) ---
    "is_fraud",
    "attack_type",
    "scenario_id",
    "attack_strength",
    "synthetic",
)

# Fields the detector is allowed to see. Ground-truth columns are excluded by
# construction so label leakage is impossible rather than merely discouraged.
GROUND_TRUTH_FIELDS: frozenset[str] = frozenset(
    {"is_fraud", "attack_type", "scenario_id", "attack_strength", "synthetic"}
)

OBSERVABLE_FIELDS: tuple[str, ...] = tuple(
    f for f in TRANSACTION_FIELDS if f not in GROUND_TRUTH_FIELDS
)
