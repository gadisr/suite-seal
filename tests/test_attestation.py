"""Tests for Ed25519 attestation functionality."""

import pytest

pytest.importorskip("nacl")

from suite_seal.core import (
    create_seal,
    attest_seal,
    verify_attestation,
)


@pytest.fixture
def ephemeral_keypair():
    """Generate ephemeral Ed25519 keypair for testing."""
    import nacl.signing
    import nacl.encoding
    
    signing_key = nacl.signing.SigningKey.generate()
    verify_key = signing_key.verify_key
    
    return {
        "private_seed": bytes(signing_key),
        "public_hex": verify_key.encode(encoder=nacl.encoding.HexEncoder).decode('ascii'),
    }


def test_attest_seal_basic(ephemeral_keypair):
    """Test basic seal attestation."""
    suite = {"task_ids": ["task-1", "task-2"]}
    seal = create_seal(suite)
    
    attested = attest_seal(seal, ephemeral_keypair["private_seed"])
    
    assert "attestation" in attested
    assert "signature" in attested["attestation"]
    assert "public_key" in attested["attestation"]
    assert attested["attestation"]["public_key"] == ephemeral_keypair["public_hex"]


def test_attest_seal_with_64_byte_keypair(ephemeral_keypair):
    """Test attestation with 64-byte keypair format."""
    suite = {"task_ids": ["task-1"]}
    seal = create_seal(suite)
    
    keypair_64 = ephemeral_keypair["private_seed"] + bytes(32)
    attested = attest_seal(seal, keypair_64)
    
    assert "attestation" in attested


def test_attest_seal_invalid_key_length():
    """Test that invalid key length raises ValueError."""
    suite = {"task_ids": ["task-1"]}
    seal = create_seal(suite)
    
    with pytest.raises(ValueError, match="must be 32 bytes"):
        attest_seal(seal, b"short")


def test_attest_seal_missing_hash():
    """Test that attestation fails when seal has no hash."""
    seal = {"version": 1, "payload": {}}
    
    with pytest.raises(ValueError, match="missing hash"):
        attest_seal(seal, b"x" * 32)


def test_verify_attestation_basic(ephemeral_keypair):
    """Test basic attestation verification."""
    suite = {"task_ids": ["task-1"]}
    seal = create_seal(suite)
    attested = attest_seal(seal, ephemeral_keypair["private_seed"])
    
    is_valid, message = verify_attestation(attested)
    assert is_valid
    assert "successfully" in message


def test_verify_attestation_with_explicit_key(ephemeral_keypair):
    """Test attestation verification with explicit public key."""
    suite = {"task_ids": ["task-1"]}
    seal = create_seal(suite)
    attested = attest_seal(seal, ephemeral_keypair["private_seed"])
    
    is_valid, message = verify_attestation(attested, ephemeral_keypair["public_hex"])
    assert is_valid


def test_verify_attestation_wrong_public_key(ephemeral_keypair):
    """Test that verification fails with wrong public key."""
    import nacl.signing
    import nacl.encoding
    
    suite = {"task_ids": ["task-1"]}
    seal = create_seal(suite)
    attested = attest_seal(seal, ephemeral_keypair["private_seed"])
    
    wrong_key = nacl.signing.SigningKey.generate()
    wrong_public = wrong_key.verify_key.encode(encoder=nacl.encoding.HexEncoder).decode('ascii')
    
    is_valid, message = verify_attestation(attested, wrong_public)
    assert not is_valid
    assert "public key mismatch" in message or "invalid signature" in message


def test_verify_attestation_tampered_signature(ephemeral_keypair):
    """Test that verification fails with tampered signature."""
    suite = {"task_ids": ["task-1"]}
    seal = create_seal(suite)
    attested = attest_seal(seal, ephemeral_keypair["private_seed"])
    
    attested["attestation"]["signature"] = "0" * 128
    
    is_valid, message = verify_attestation(attested)
    assert not is_valid
    assert "invalid signature" in message


def test_verify_attestation_tampered_hash(ephemeral_keypair):
    """Test that verification fails when hash is changed after attestation."""
    suite = {"task_ids": ["task-1"]}
    seal = create_seal(suite)
    attested = attest_seal(seal, ephemeral_keypair["private_seed"])
    
    attested["hash"] = "0" * 64
    
    is_valid, message = verify_attestation(attested)
    assert not is_valid
    assert "invalid signature" in message


def test_verify_attestation_missing_attestation():
    """Test that verification fails when seal has no attestation."""
    suite = {"task_ids": ["task-1"]}
    seal = create_seal(suite)
    
    is_valid, message = verify_attestation(seal)
    assert not is_valid
    assert "no attestation" in message


def test_verify_attestation_incomplete_attestation():
    """Test that verification fails with incomplete attestation."""
    suite = {"task_ids": ["task-1"]}
    seal = create_seal(suite)
    seal["attestation"] = {"signature": "abc"}
    
    is_valid, message = verify_attestation(seal)
    assert not is_valid
    assert "missing" in message
