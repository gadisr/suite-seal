"""Tests for CLI functionality."""

import json
import subprocess
import sys
from pathlib import Path

import pytest


@pytest.fixture
def tmp_suite(tmp_path):
    """Create a temporary suite file."""
    suite_file = tmp_path / "suite.json"
    suite_data = {
        "task_ids": ["task-1", "task-2", "task-3"],
        "metadata": {"version": "1.0"}
    }
    suite_file.write_text(json.dumps(suite_data))
    return suite_file


def test_cli_seal_and_verify(tmp_suite, tmp_path):
    """Test seal creation and verification via CLI."""
    seal_file = tmp_path / "seal.json"
    
    result = subprocess.run(
        [sys.executable, "-m", "suite_seal", "seal", str(tmp_suite), "-o", str(seal_file)],
        capture_output=True,
        text=True
    )
    assert result.returncode == 0
    assert "Seal created" in result.stdout
    assert seal_file.exists()
    
    seal_data = json.loads(seal_file.read_text())
    assert "hash" in seal_data
    assert "freeze_date" in seal_data
    
    result = subprocess.run(
        [sys.executable, "-m", "suite_seal", "verify", str(tmp_suite), str(seal_file)],
        capture_output=True,
        text=True
    )
    assert result.returncode == 0
    assert "✓" in result.stdout


def test_cli_seal_with_label(tmp_suite, tmp_path):
    """Test seal creation with label."""
    seal_file = tmp_path / "seal.json"
    
    result = subprocess.run(
        [sys.executable, "-m", "suite_seal", "seal", str(tmp_suite), 
         "-o", str(seal_file), "-l", "v1.0-release"],
        capture_output=True,
        text=True
    )
    assert result.returncode == 0
    
    seal_data = json.loads(seal_file.read_text())
    assert seal_data["label"] == "v1.0-release"


def test_cli_verify_fails_on_mismatch(tmp_suite, tmp_path):
    """Test that verification fails with mismatched suite."""
    seal_file = tmp_path / "seal.json"
    
    subprocess.run(
        [sys.executable, "-m", "suite_seal", "seal", str(tmp_suite), "-o", str(seal_file)],
        check=True
    )
    
    modified_suite = tmp_path / "modified.json"
    modified_data = {
        "task_ids": ["task-1", "task-2", "task-4"]
    }
    modified_suite.write_text(json.dumps(modified_data))
    
    result = subprocess.run(
        [sys.executable, "-m", "suite_seal", "verify", str(modified_suite), str(seal_file)],
        capture_output=True,
        text=True
    )
    assert result.returncode == 2
    assert "✗" in result.stderr


def test_cli_missing_file(tmp_path):
    """Test CLI handles missing files gracefully."""
    result = subprocess.run(
        [sys.executable, "-m", "suite_seal", "seal", "nonexistent.json", 
         "-o", str(tmp_path / "seal.json")],
        capture_output=True,
        text=True
    )
    assert result.returncode == 1
    assert "not found" in result.stderr
