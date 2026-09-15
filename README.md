# suite-seal

Hash-lock a dated evaluation suite freeze so later runs can prove they used the exact sealed task set. `suite-seal` creates cryptographically verified snapshots of evaluation task lists, preventing drift and enabling reproducible benchmark comparisons over time. Optional Ed25519 attestation lets you sign seals for external verification.

## Use Cases

### 1. Private Suite Freeze for Fair Comparisons

You maintain a private evaluation suite and want to ensure all internal experiments use the same task set, even as the suite evolves.

**Suite manifest** (`suite.json`):
```json
{
  "task_ids": [
    "coding-task-001",
    "coding-task-002",
    "coding-task-003",
    "reasoning-task-001"
  ],
  "metadata": {
    "name": "Q3 2026 Internal Benchmark",
    "version": "1.0"
  }
}
```

**Create a seal:**
```bash
suite-seal seal suite.json -o suite-q3-2026.seal.json -l "Q3-2026-freeze"
```

**Verify before running evals:**
```bash
suite-seal verify suite.json suite-q3-2026.seal.json
```

Exit code 0 means your current suite matches the frozen snapshot. Non-zero stops the eval run.

---

### 2. CI Scoreboard Reproducibility

Your CI pipeline maintains a public leaderboard. Seals prove that all submitted scores used the official frozen task set, not a cherry-picked subset.

**In CI (build step):**
```bash
# Download official seal
curl -O https://example.com/leaderboard-v2.seal.json

# Verify before scoring
suite-seal verify current_suite.json leaderboard-v2.seal.json || exit 1

# Run evaluation...
```

The seal's hash is published alongside leaderboard results. Anyone can recompute and verify.

---

### 3. Meta-Harness Evolution with Frozen Baseline

You're improving an evaluation harness. Seal the current task set, modify the harness, then verify both old and new harnesses still run the identical frozen suite for apples-to-apples comparisons.

**Initial freeze:**
```bash
suite-seal seal baseline_suite.json -o baseline-v1.seal.json -d "2026-09-01T00:00:00Z"
```

**After harness changes:**
```bash
# Verify new harness still uses baseline suite
suite-seal verify baseline_suite.json baseline-v1.seal.json
```

Any task ID drift (missing tasks, extra tasks, renames) fails verification with exit code 2.

---

## Installation

```bash
pip install suite-seal
```

For Ed25519 attestation support:
```bash
pip install suite-seal[attest]
```

Or install in editable mode for development:
```bash
git clone https://github.com/your-org/suite-seal.git
cd suite-seal
pip install -e .[dev]
```

## CLI Usage

### Commands

#### `seal` - Create a seal

```bash
suite-seal seal <suite.json> -o <output.seal.json> [-l <label>] [-d <freeze-date>]
```

- `suite.json`: Suite manifest with `task_ids` list (required) and optional `metadata`
- `-o, --output`: Output path for seal file (required)
- `-l, --label`: Optional human-readable label
- `-d, --freeze-date`: Optional ISO date (defaults to now)

#### `verify` - Verify suite against seal

```bash
suite-seal verify <suite.json> <seal.json>
```

Recomputes suite hash and checks:
- Hash matches seal
- Task IDs match exactly (no missing, no extra)
- Seal integrity (payload matches embedded hash)

#### `attest` - Add Ed25519 attestation (optional)

```bash
suite-seal attest <seal.json> -k <private.key> -o <attested.seal.json>
```

Requires `pip install suite-seal[attest]`. Signs the seal hash with an Ed25519 private key (32-byte seed or 64-byte keypair).

#### `verify-attest` - Verify attestation (optional)

```bash
suite-seal verify-attest <attested.seal.json> [-k <public.key>]
```

Verifies Ed25519 signature. If `-k` is omitted, uses the public key embedded in the seal.

### Exit Codes

- **0**: Success
- **1**: Error (invalid arguments, missing file, invalid key, etc.)
- **2**: Seal verification failed or attestation invalid

### Module Usage

```bash
python -m suite_seal <command> [args...]
```

## Seal Format

A seal is a JSON file:

```json
{
  "version": 1,
  "payload": {
    "task_ids": ["task-1", "task-2", "task-3"],
    "metadata": {"version": "1.0"}
  },
  "hash": "sha256-hex-of-canonical-payload",
  "freeze_date": "2026-09-15T07:36:00.000000+00:00",
  "label": "optional-label"
}
```

Optional `attestation` field (when signed):

```json
{
  ...,
  "attestation": {
    "signature": "ed25519-signature-hex",
    "public_key": "ed25519-public-key-hex"
  }
}
```

## Examples

See [`examples/`](./examples) for complete examples with attestation workflows.

## Testing

```bash
pytest
```

Tests cover:
- Seal creation and verification
- Tamper detection (modified hash, payload, or task IDs)
- Task ID drift (missing/extra tasks)
- Ed25519 attestation (ephemeral keys generated in tests)

## License

MIT

---

## With failstrata

If you're using [failstrata](https://github.com/cursor-team/failstrata), `suite-seal` provides hash-locked freeze points for reproducible eval runs. Reference sealed task sets in your evaluation configs to ensure consistent scoring across harness versions and team members.
