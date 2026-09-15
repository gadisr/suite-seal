# Examples

This directory contains example files for using suite-seal.

## Files

- `example_suite.json` - Example suite manifest with task IDs and metadata
- `example_seal.json` - Example seal file (generated, see commands below)

## Usage Examples

### Create a seal

```bash
suite-seal seal example_suite.json -o example_seal.json -l "Q3-2026-v1"
```

### Verify a suite against a seal

```bash
suite-seal verify example_suite.json example_seal.json
```

### Attestation (requires PyNaCl)

Generate an ephemeral key for testing:

```bash
python -c "import nacl.signing, nacl.encoding; k = nacl.signing.SigningKey.generate(); open('private.key', 'wb').write(bytes(k)); print('Public key:', k.verify_key.encode(encoder=nacl.encoding.HexEncoder).decode())"
```

Add attestation to a seal:

```bash
suite-seal attest example_seal.json -k private.key -o example_seal_attested.json
```

Verify attestation:

```bash
suite-seal verify-attest example_seal_attested.json
```

## Expected Outputs

A seal file will look like:

```json
{
  "freeze_date": "2026-09-15T07:36:00.000000+00:00",
  "hash": "a1b2c3...",
  "label": "Q3-2026-v1",
  "payload": {
    "metadata": {
      "description": "Private evaluation suite for Q3 2026",
      "name": "Q3 2026 Benchmark Suite",
      "task_count": 5,
      "version": "1.0"
    },
    "task_ids": [
      "coding-task-001",
      "coding-task-002",
      "coding-task-003",
      "reasoning-task-001",
      "reasoning-task-002"
    ]
  },
  "version": 1
}
```

An attested seal adds an `attestation` field with signature and public key.
