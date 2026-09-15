"""suite-seal: Hash-lock a dated evaluation suite freeze with optional Ed25519 attestation."""

from suite_seal.core import (
    create_seal,
    verify_seal,
    attest_seal,
    verify_attestation,
    canonicalize_suite,
    compute_suite_hash,
)

__version__ = "0.1.0"

__all__ = [
    "create_seal",
    "verify_seal",
    "attest_seal",
    "verify_attestation",
    "canonicalize_suite",
    "compute_suite_hash",
]
