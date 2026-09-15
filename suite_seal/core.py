"""Core seal and verify logic for suite-seal."""

import hashlib
import json
from datetime import datetime, timezone
from typing import Any


def canonicalize_suite(suite_data: dict[str, Any]) -> str:
    """
    Canonicalize suite data to ensure consistent hashing.
    
    Extracts task_ids list and optional metadata, sorts task_ids,
    and returns deterministic JSON string.
    """
    task_ids = suite_data.get("task_ids", [])
    if not isinstance(task_ids, list):
        raise ValueError("suite must contain 'task_ids' as a list")
    
    if not task_ids:
        raise ValueError("task_ids cannot be empty")
    
    sorted_ids = sorted(set(str(tid) for tid in task_ids))
    
    canonical = {
        "task_ids": sorted_ids,
    }
    
    if "metadata" in suite_data:
        canonical["metadata"] = suite_data["metadata"]
    
    return json.dumps(canonical, sort_keys=True, separators=(',', ':'))


def compute_suite_hash(canonical_payload: str) -> str:
    """Compute SHA256 hash of canonical payload."""
    return hashlib.sha256(canonical_payload.encode('utf-8')).hexdigest()


def create_seal(
    suite_data: dict[str, Any],
    label: str | None = None,
    freeze_date: str | None = None
) -> dict[str, Any]:
    """
    Create a seal for the given suite data.
    
    Args:
        suite_data: Dict with 'task_ids' list and optional 'metadata'
        label: Optional human-readable label for this seal
        freeze_date: Optional ISO freeze date (defaults to now)
    
    Returns:
        Seal dictionary with payload, hash, timestamp, and optional label
    """
    canonical = canonicalize_suite(suite_data)
    suite_hash = compute_suite_hash(canonical)
    
    if freeze_date is None:
        freeze_date = datetime.now(timezone.utc).isoformat()
    
    seal = {
        "version": 1,
        "payload": json.loads(canonical),
        "hash": suite_hash,
        "freeze_date": freeze_date,
    }
    
    if label:
        seal["label"] = label
    
    return seal


def verify_seal(suite_data: dict[str, Any], seal: dict[str, Any]) -> tuple[bool, str]:
    """
    Verify suite data against a seal.
    
    Returns:
        (is_valid, message) tuple
    """
    if seal.get("version") != 1:
        return False, f"unsupported seal version: {seal.get('version')}"
    
    expected_hash = seal.get("hash")
    if not expected_hash:
        return False, "seal missing hash field"
    
    sealed_payload = seal.get("payload")
    if not sealed_payload:
        return False, "seal missing payload field"
    
    try:
        canonical = canonicalize_suite(suite_data)
        computed_hash = compute_suite_hash(canonical)
    except ValueError as e:
        return False, f"invalid suite data: {e}"
    
    sealed_canonical = json.dumps(sealed_payload, sort_keys=True, separators=(',', ':'))
    sealed_hash = compute_suite_hash(sealed_canonical)
    
    if sealed_hash != expected_hash:
        return False, "seal hash does not match sealed payload"
    
    suite_ids = set(json.loads(canonical)["task_ids"])
    sealed_ids = set(sealed_payload.get("task_ids", []))
    
    if suite_ids != sealed_ids:
        missing = sealed_ids - suite_ids
        extra = suite_ids - sealed_ids
        msg_parts = []
        if missing:
            msg_parts.append(f"missing ids: {sorted(missing)}")
        if extra:
            msg_parts.append(f"extra ids: {sorted(extra)}")
        return False, f"task_ids mismatch - {'; '.join(msg_parts)}"
    
    if computed_hash != expected_hash:
        return False, "computed hash does not match seal hash"
    
    return True, "seal verified successfully"


def attest_seal(seal: dict[str, Any], private_key_bytes: bytes) -> dict[str, Any]:
    """
    Add Ed25519 attestation to a seal.
    
    Args:
        seal: Seal dictionary
        private_key_bytes: Ed25519 private key (32-byte seed or 64-byte keypair)
    
    Returns:
        Seal with added attestation field
    
    Requires PyNaCl to be installed.
    """
    try:
        import nacl.signing
        import nacl.encoding
    except ImportError:
        raise ImportError(
            "PyNaCl is required for attestation. Install with: pip install suite-seal[attest]"
        )
    
    seal_hash = seal.get("hash")
    if not seal_hash:
        raise ValueError("seal missing hash field")
    
    if len(private_key_bytes) == 64:
        private_key_bytes = private_key_bytes[:32]
    
    if len(private_key_bytes) != 32:
        raise ValueError(f"private key must be 32 bytes (seed) or 64 bytes (keypair), got {len(private_key_bytes)}")
    
    signing_key = nacl.signing.SigningKey(private_key_bytes)
    signed = signing_key.sign(seal_hash.encode('utf-8'))
    
    attested_seal = seal.copy()
    attested_seal["attestation"] = {
        "signature": signed.signature.hex(),
        "public_key": signing_key.verify_key.encode(encoder=nacl.encoding.HexEncoder).decode('ascii'),
    }
    
    return attested_seal


def verify_attestation(seal: dict[str, Any], public_key_hex: str | None = None) -> tuple[bool, str]:
    """
    Verify Ed25519 attestation on a seal.
    
    Args:
        seal: Seal with attestation field
        public_key_hex: Optional public key to verify against (hex string).
                       If None, uses public_key from seal's attestation.
    
    Returns:
        (is_valid, message) tuple
    
    Requires PyNaCl to be installed.
    """
    try:
        import nacl.signing
        import nacl.encoding
        import nacl.exceptions
    except ImportError:
        raise ImportError(
            "PyNaCl is required for attestation. Install with: pip install suite-seal[attest]"
        )
    
    attestation = seal.get("attestation")
    if not attestation:
        return False, "seal has no attestation"
    
    signature_hex = attestation.get("signature")
    embedded_key_hex = attestation.get("public_key")
    
    if not signature_hex or not embedded_key_hex:
        return False, "attestation missing signature or public_key"
    
    key_to_use = public_key_hex or embedded_key_hex
    
    try:
        verify_key = nacl.signing.VerifyKey(key_to_use, encoder=nacl.encoding.HexEncoder)
        signature = bytes.fromhex(signature_hex)
        seal_hash = seal.get("hash", "")
        
        verify_key.verify(seal_hash.encode('utf-8'), signature)
        
        if public_key_hex and public_key_hex != embedded_key_hex:
            return False, f"public key mismatch (expected {public_key_hex}, got {embedded_key_hex})"
        
        return True, "attestation verified successfully"
    
    except nacl.exceptions.BadSignatureError:
        return False, "invalid signature"
    except Exception as e:
        return False, f"verification error: {e}"
