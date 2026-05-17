# Manifest Format Specification

## Overview

A substrate manifest is a JSON document listing the constitutional files, their expected hashes, and authorization signatures. It serves as the trusted baseline for verification.

## Format

```json
{
  "version": 1,
  "generated": "2026-05-17T10:52:00-07:00",
  "algorithm": "sha256",
  "files": {
    "SOUL.md": {
      "path": "SOUL.md",
      "hash": "a7f3b2c1d4e5...",
      "size": 4521,
      "modified": "2026-05-11T14:30:00-07:00"
    },
    "MEMORY.md": { ... },
    "IDENTITY.md": { ... },
    "USER.md": { ... },
    "02_memory/moral-ethical-framework-2026-03-02.md": { ... }
  },
  "signatures": {
    "ellie": {
      "key_id": "sha256:abc123...",
      "signature": "ed25519:...",
      "signed": "2026-05-17T10:52:05-07:00"
    },
    "alexander": {
      "key_id": "sha256:def456...",
      "signature": "ed25519:...",
      "signed": "2026-05-17T10:52:10-07:00"
    }
  }
}
```

## Design Decisions

- **Version field**: enables format migration without breaking old verifiers
- **Algorithm field**: hash algorithm identified by name (sha256 now, sha3 later)
- **File paths**: relative to substrate root directory
- **Canonical JSON**: keys sorted alphabetically for deterministic hashing
- **Signatures reference the manifest hash** (not individual files) — one signature covers everything

## Canonical Serialization

For signing purposes, the manifest is serialized with:
- JSON keys sorted alphabetically (recursive)
- No whitespace (compact)
- UTF-8 encoding
- Signatures field excluded from the hash being signed

## Constitutional File List

Phase 1 fixed set:
1. `SOUL.md`
2. `MEMORY.md`
3. `IDENTITY.md`
4. `USER.md`
5. `02_memory/moral-ethical-framework-2026-03-02.md`

Expansion mechanism: future versions may support a configurable file list, but changes to the list itself require dual-key signing.
