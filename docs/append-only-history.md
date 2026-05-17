# Append-Only History Format

## Overview

The history store is an append-only chain of manifest entries. Each entry links to the previous one via its hash, creating a tamper-evident log of every constitutional change.

## Storage

The history is stored as a directory of JSON files, one per entry:

```
history/
  chain.jsonl          # Append-only log, one JSON object per line
  entries/
    0001.json          # Full manifest snapshot at this point
    0002.json
    ...
```

`chain.jsonl` is the primary structure. Each line is a chain entry:

```json
{
  "sequence": 1,
  "timestamp": "2026-05-17T12:00:00-07:00",
  "type": "baseline",
  "manifest_hash": "76e1750f...",
  "previous_hash": null,
  "entry_hash": "sha256:abc123...",
  "signatures": {
    "ellie": { "key_id": "...", "signature": "ed25519:...", "signed": "..." },
    "alexander": { "key_id": "...", "signature": "ed25519:...", "signed": "..." }
  },
  "description": "Initial baseline — bootstrap ceremony"
}
```

## Entry Types

- `baseline` — Initial trusted state or recovery event
- `amendment` — Constitutional file changed via signing ceremony
- `verification` — Periodic check confirming current state matches (heartbeat)
- `recovery` — Emergency re-establishment after compromise

## Chain Integrity

Each entry's `entry_hash` is computed over:
- sequence number
- timestamp
- type
- manifest_hash
- previous_hash
- description

Sorted canonical JSON, SHA-256.

To verify the chain:
1. Start at entry 1 (previous_hash must be null)
2. For each subsequent entry, verify previous_hash matches the entry_hash of entry N-1
3. Verify entry_hash matches recomputation from entry contents
4. Verify manifest_hash matches actual manifest file (if present in entries/)
5. Verify signatures

Any modification to an entry invalidates all subsequent entries.

## Operations

### Init
Creates entry #1 with type `baseline`. No previous_hash. Requires both signatures.

### Append
Creates next entry. Must reference previous entry_hash. Can optionally include full manifest snapshot in entries/.

### Verify Chain
Walks entire chain, checks hash linkage, recomputes entry hashes, verifies signatures.

### Diff
Given two sequence numbers, compares the manifest snapshots. Shows what changed between any two points in history.

## Design Decisions

- **JSONL format**: One entry per line makes appending safe (no need to parse/rewrite a full JSON file). `tail` shows latest entry. Easy to inspect manually.
- **Separate entries/ directory**: Full manifest snapshots are stored separately to keep chain.jsonl compact. Chain entries reference manifests by hash.
- **entry_hash links the chain**: Not the manifest_hash. The chain records *events*, not just file states. A verification event has the same manifest_hash as the previous entry but a different entry_hash.
