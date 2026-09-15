"""Command-line interface for suite-seal."""

import argparse
import json
import sys
from pathlib import Path
from typing import Any

from suite_seal.core import (
    create_seal,
    verify_seal,
    attest_seal,
    verify_attestation,
)


def load_json(path: Path) -> dict[str, Any]:
    """Load JSON from file."""
    try:
        with open(path, 'r', encoding='utf-8') as f:
            return json.load(f)
    except FileNotFoundError:
        print(f"Error: file not found: {path}", file=sys.stderr)
        sys.exit(1)
    except json.JSONDecodeError as e:
        print(f"Error: invalid JSON in {path}: {e}", file=sys.stderr)
        sys.exit(1)


def save_json(data: dict[str, Any], path: Path) -> None:
    """Save JSON to file with pretty formatting."""
    with open(path, 'w', encoding='utf-8') as f:
        json.dump(data, f, indent=2, sort_keys=True)
        f.write('\n')


def cmd_seal(args: argparse.Namespace) -> int:
    """Create a seal for a suite."""
    suite_data = load_json(args.suite)
    
    try:
        seal = create_seal(
            suite_data,
            label=args.label,
            freeze_date=args.freeze_date
        )
        
        save_json(seal, args.output)
        print(f"Seal created: {args.output}")
        print(f"Hash: {seal['hash']}")
        if args.label:
            print(f"Label: {args.label}")
        print(f"Freeze date: {seal['freeze_date']}")
        return 0
    
    except ValueError as e:
        print(f"Error: {e}", file=sys.stderr)
        return 1


def cmd_verify(args: argparse.Namespace) -> int:
    """Verify a suite against a seal."""
    suite_data = load_json(args.suite)
    seal = load_json(args.seal)
    
    is_valid, message = verify_seal(suite_data, seal)
    
    if is_valid:
        print(f"✓ {message}")
        print(f"Hash: {seal.get('hash')}")
        if seal.get('label'):
            print(f"Label: {seal['label']}")
        print(f"Freeze date: {seal.get('freeze_date')}")
        return 0
    else:
        print(f"✗ Verification failed: {message}", file=sys.stderr)
        return 2


def cmd_attest(args: argparse.Namespace) -> int:
    """Add Ed25519 attestation to a seal."""
    seal = load_json(args.seal)
    
    try:
        key_path = Path(args.private_key)
        if not key_path.exists():
            print(f"Error: private key file not found: {key_path}", file=sys.stderr)
            return 1
        
        private_key_bytes = key_path.read_bytes()
        
        attested_seal = attest_seal(seal, private_key_bytes)
        
        save_json(attested_seal, args.output)
        print(f"Attestation added: {args.output}")
        print(f"Public key: {attested_seal['attestation']['public_key']}")
        return 0
    
    except ImportError as e:
        print(f"Error: {e}", file=sys.stderr)
        return 1
    except ValueError as e:
        print(f"Error: {e}", file=sys.stderr)
        return 1


def cmd_verify_attest(args: argparse.Namespace) -> int:
    """Verify Ed25519 attestation on a seal."""
    seal = load_json(args.seal)
    
    public_key_hex = None
    if args.public_key:
        key_path = Path(args.public_key)
        if not key_path.exists():
            print(f"Error: public key file not found: {key_path}", file=sys.stderr)
            return 1
        public_key_hex = key_path.read_text(encoding='utf-8').strip()
    
    try:
        is_valid, message = verify_attestation(seal, public_key_hex)
        
        if is_valid:
            print(f"✓ {message}")
            print(f"Public key: {seal['attestation']['public_key']}")
            return 0
        else:
            print(f"✗ Attestation verification failed: {message}", file=sys.stderr)
            return 2
    
    except ImportError as e:
        print(f"Error: {e}", file=sys.stderr)
        return 1


def main() -> None:
    """Main entry point."""
    parser = argparse.ArgumentParser(
        prog="suite-seal",
        description="Hash-lock a dated evaluation suite freeze with optional Ed25519 attestation",
    )
    
    subparsers = parser.add_subparsers(dest="command", required=True)
    
    seal_parser = subparsers.add_parser(
        "seal",
        help="Create a seal for a suite"
    )
    seal_parser.add_argument(
        "suite",
        type=Path,
        help="Path to suite JSON file (must contain 'task_ids' list)"
    )
    seal_parser.add_argument(
        "-o", "--output",
        type=Path,
        required=True,
        help="Output path for seal file"
    )
    seal_parser.add_argument(
        "-l", "--label",
        help="Optional human-readable label for this seal"
    )
    seal_parser.add_argument(
        "-d", "--freeze-date",
        help="Optional ISO freeze date (defaults to now)"
    )
    
    verify_parser = subparsers.add_parser(
        "verify",
        help="Verify a suite against a seal"
    )
    verify_parser.add_argument(
        "suite",
        type=Path,
        help="Path to suite JSON file"
    )
    verify_parser.add_argument(
        "seal",
        type=Path,
        help="Path to seal file"
    )
    
    attest_parser = subparsers.add_parser(
        "attest",
        help="Add Ed25519 attestation to a seal (requires PyNaCl)"
    )
    attest_parser.add_argument(
        "seal",
        type=Path,
        help="Path to seal file"
    )
    attest_parser.add_argument(
        "-k", "--private-key",
        required=True,
        help="Path to Ed25519 private key file (32-byte seed or 64-byte keypair)"
    )
    attest_parser.add_argument(
        "-o", "--output",
        type=Path,
        required=True,
        help="Output path for attested seal file"
    )
    
    verify_attest_parser = subparsers.add_parser(
        "verify-attest",
        help="Verify Ed25519 attestation on a seal (requires PyNaCl)"
    )
    verify_attest_parser.add_argument(
        "seal",
        type=Path,
        help="Path to attested seal file"
    )
    verify_attest_parser.add_argument(
        "-k", "--public-key",
        help="Optional path to public key file (hex string). If omitted, uses embedded key."
    )
    
    args = parser.parse_args()
    
    if args.command == "seal":
        sys.exit(cmd_seal(args))
    elif args.command == "verify":
        sys.exit(cmd_verify(args))
    elif args.command == "attest":
        sys.exit(cmd_attest(args))
    elif args.command == "verify-attest":
        sys.exit(cmd_verify_attest(args))
    else:
        parser.print_help()
        sys.exit(1)


if __name__ == "__main__":
    main()
