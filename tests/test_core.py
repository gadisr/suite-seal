"""Tests for core seal and verify functionality."""

import pytest
from suite_seal.core import (
    create_seal,
    verify_seal,
    canonicalize_suite,
    compute_suite_hash,
)


def test_canonicalize_suite_sorts_ids():
    """Test that task IDs are sorted and deduplicated."""
    suite = {
        "task_ids": ["task-3", "task-1", "task-2", "task-1"]
    }
    canonical = canonicalize_suite(suite)
    assert '"task_ids":["task-1","task-2","task-3"]' in canonical


def test_canonicalize_suite_preserves_metadata():
    """Test that metadata is preserved in canonical form."""
    suite = {
        "task_ids": ["task-1"],
        "metadata": {"author": "test", "version": "1.0"}
    }
    canonical = canonicalize_suite(suite)
    assert '"metadata"' in canonical
    assert '"author":"test"' in canonical


def test_canonicalize_suite_empty_ids_raises():
    """Test that empty task_ids raises ValueError."""
    with pytest.raises(ValueError, match="task_ids cannot be empty"):
        canonicalize_suite({"task_ids": []})


def test_canonicalize_suite_missing_ids_raises():
    """Test that missing task_ids raises ValueError."""
    with pytest.raises(ValueError, match="task_ids cannot be empty"):
        canonicalize_suite({"foo": "bar"})


def test_create_seal_basic():
    """Test basic seal creation."""
    suite = {
        "task_ids": ["task-1", "task-2", "task-3"]
    }
    seal = create_seal(suite)
    
    assert seal["version"] == 1
    assert "hash" in seal
    assert "freeze_date" in seal
    assert "payload" in seal
    assert seal["payload"]["task_ids"] == ["task-1", "task-2", "task-3"]


def test_create_seal_with_label():
    """Test seal creation with label."""
    suite = {"task_ids": ["task-1"]}
    seal = create_seal(suite, label="test-suite-v1")
    
    assert seal["label"] == "test-suite-v1"


def test_create_seal_with_freeze_date():
    """Test seal creation with custom freeze date."""
    suite = {"task_ids": ["task-1"]}
    freeze_date = "2026-09-15T00:00:00Z"
    seal = create_seal(suite, freeze_date=freeze_date)
    
    assert seal["freeze_date"] == freeze_date


def test_verify_seal_happy_path():
    """Test successful seal verification."""
    suite = {
        "task_ids": ["task-1", "task-2", "task-3"],
        "metadata": {"version": "1.0"}
    }
    seal = create_seal(suite)
    
    is_valid, message = verify_seal(suite, seal)
    assert is_valid
    assert "successfully" in message


def test_verify_seal_reordered_ids():
    """Test that verification succeeds with reordered task IDs."""
    suite = {"task_ids": ["task-3", "task-1", "task-2"]}
    seal = create_seal(suite)
    
    suite_reordered = {"task_ids": ["task-1", "task-2", "task-3"]}
    is_valid, message = verify_seal(suite_reordered, seal)
    assert is_valid


def test_verify_seal_missing_ids():
    """Test verification fails when suite is missing task IDs."""
    suite = {"task_ids": ["task-1", "task-2", "task-3"]}
    seal = create_seal(suite)
    
    suite_missing = {"task_ids": ["task-1", "task-2"]}
    is_valid, message = verify_seal(suite_missing, seal)
    assert not is_valid
    assert "missing ids" in message
    assert "task-3" in message


def test_verify_seal_extra_ids():
    """Test verification fails when suite has extra task IDs."""
    suite = {"task_ids": ["task-1", "task-2"]}
    seal = create_seal(suite)
    
    suite_extra = {"task_ids": ["task-1", "task-2", "task-3"]}
    is_valid, message = verify_seal(suite_extra, seal)
    assert not is_valid
    assert "extra ids" in message
    assert "task-3" in message


def test_verify_seal_tampered_hash():
    """Test verification fails when seal hash is tampered."""
    suite = {"task_ids": ["task-1"]}
    seal = create_seal(suite)
    
    seal["hash"] = "0" * 64
    is_valid, message = verify_seal(suite, seal)
    assert not is_valid


def test_verify_seal_tampered_payload():
    """Test verification fails when sealed payload is tampered."""
    suite = {"task_ids": ["task-1"]}
    seal = create_seal(suite)
    
    seal["payload"]["task_ids"] = ["task-2"]
    is_valid, message = verify_seal(suite, seal)
    assert not is_valid
    assert "does not match sealed payload" in message


def test_verify_seal_missing_hash():
    """Test verification fails when seal is missing hash."""
    suite = {"task_ids": ["task-1"]}
    seal = create_seal(suite)
    
    del seal["hash"]
    is_valid, message = verify_seal(suite, seal)
    assert not is_valid
    assert "missing hash" in message


def test_verify_seal_unsupported_version():
    """Test verification fails for unsupported seal version."""
    suite = {"task_ids": ["task-1"]}
    seal = create_seal(suite)
    
    seal["version"] = 999
    is_valid, message = verify_seal(suite, seal)
    assert not is_valid
    assert "unsupported seal version" in message


def test_compute_suite_hash_deterministic():
    """Test that hash computation is deterministic."""
    canonical = '{"task_ids":["task-1","task-2"]}'
    hash1 = compute_suite_hash(canonical)
    hash2 = compute_suite_hash(canonical)
    assert hash1 == hash2
    assert len(hash1) == 64
