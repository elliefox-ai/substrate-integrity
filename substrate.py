#!/usr/bin/env python3
"""
substrate-integrity — Cryptographic identity protection for AI agents.

Usage:
    substrate generate <substrate_dir> [-o manifest.json]
    substrate verify <manifest.json> <substrate_dir>
    substrate sign <manifest.json> --key <keyfile> --identity <name>
    substrate keygen [--output <keyfile>]
    substrate history init <history_dir> --manifest <manifest.json>
    substrate history append <history_dir> --manifest <manifest.json> [--type TYPE] [--desc DESC]
    substrate history verify <history_dir>
    substrate history diff <history_dir> <seq_a> <seq_b>
    substrate history log <history_dir> [--last N]

Commands:
    generate            Create a manifest of constitutional file hashes
    verify              Check current files against a signed manifest
    sign                Add a signature to a manifest
    keygen              Generate a new Ed25519 keypair
    history init        Create a new append-only chain with a baseline entry
    history append      Add a new entry to the chain
    history verify      Walk the full chain and verify integrity
    history diff        Compare manifest snapshots between two entries
    history log         Display chain history
"""

import argparse
import hashlib
import json
import os
import sys
from datetime import datetime, timezone
from pathlib import Path

VERSION = 1
ALGORITHM = "sha256"
MANIFEST_VERSION = 1

# Constitutional files — relative to substrate root
CONSTITUTIONAL_FILES = [
    "SOUL.md",
    "MEMORY.md",
    "IDENTITY.md",
    "USER.md",
    "02_memory/moral-ethical-framework-2026-03-02.md",
]


# ─── Utility Functions ──────────────────────────────────────────

def sha256_file(filepath):
    """Compute SHA-256 hash of a file."""
    h = hashlib.sha256()
    with open(filepath, "rb") as f:
        for chunk in iter(lambda: f.read(8192), b""):
            h.update(chunk)
    return h.hexdigest()


def canonical_json(data):
    """Serialize data as canonical JSON (sorted keys, no whitespace)."""
    return json.dumps(data, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode("utf-8")


def manifest_hash(manifest_data):
    """Compute the hash of a manifest (excluding signatures)."""
    data_for_hash = {k: v for k, v in manifest_data.items() if k != "signatures"}
    return hashlib.sha256(canonical_json(data_for_hash)).hexdigest()


# ─── Manifest Commands ──────────────────────────────────────────

def cmd_generate(args):
    """Generate a manifest of constitutional file hashes."""
    substrate_dir = Path(args.substrate_dir)

    if not substrate_dir.is_dir():
        print(f"Error: {substrate_dir} is not a directory", file=sys.stderr)
        sys.exit(1)

    files = {}
    missing = []

    for relpath in CONSTITUTIONAL_FILES:
        filepath = substrate_dir / relpath
        if not filepath.exists():
            missing.append(relpath)
            continue

        stat = filepath.stat()
        files[relpath] = {
            "path": relpath,
            "hash": sha256_file(filepath),
            "size": stat.st_size,
            "modified": datetime.fromtimestamp(stat.st_mtime, tz=timezone.utc).isoformat(),
        }

    if missing:
        print("Warning: missing constitutional files:", file=sys.stderr)
        for m in missing:
            print(f"  - {m}", file=sys.stderr)

    manifest = {
        "version": MANIFEST_VERSION,
        "generated": datetime.now(timezone.utc).isoformat(),
        "algorithm": ALGORITHM,
        "files": files,
        "signatures": {},
    }

    output = json.dumps(manifest, indent=2, sort_keys=True, ensure_ascii=False)
    if args.output:
        with open(args.output, "w") as f:
            f.write(output)
        print(f"Manifest written to {args.output}")
        print(f"Manifest hash: {manifest_hash(manifest)}")
    else:
        print(output)

    print(f"\n{len(files)} constitutional files hashed.", file=sys.stderr)


def cmd_verify(args):
    """Verify current files against a manifest."""
    manifest_path = Path(args.manifest)
    substrate_dir = Path(args.substrate_dir)

    if not manifest_path.exists():
        print(f"Error: manifest not found: {manifest_path}", file=sys.stderr)
        sys.exit(1)

    if not substrate_dir.is_dir():
        print(f"Error: substrate directory not found: {substrate_dir}", file=sys.stderr)
        sys.exit(1)

    with open(manifest_path) as f:
        manifest = json.load(f)

    expected_files = manifest.get("files", {})
    algorithm = manifest.get("algorithm", "sha256")

    if algorithm != "sha256":
        print(f"Error: unsupported hash algorithm: {algorithm}", file=sys.stderr)
        sys.exit(1)

    passed = 0
    failed = 0
    missing = 0
    results = []

    for relpath, expected in expected_files.items():
        filepath = substrate_dir / relpath

        if not filepath.exists():
            results.append(("MISSING", relpath, "File not found"))
            missing += 1
            continue

        current_hash = sha256_file(filepath)

        if current_hash == expected["hash"]:
            results.append(("OK", relpath, None))
            passed += 1
        else:
            results.append(("CHANGED", relpath, f"expected {expected['hash'][:16]}... got {current_hash[:16]}..."))
            failed += 1

    print(f"Substrate Integrity Verification")
    print(f"Manifest: {manifest_path}")
    print(f"Generated: {manifest.get('generated', 'unknown')}")
    print(f"Algorithm: {algorithm}")
    print(f"{'=' * 60}")

    for status, path, detail in results:
        if status == "OK":
            print(f"  ✅ {path}")
        elif status == "MISSING":
            print(f"  ❌ {path} — MISSING: {detail}")
        elif status == "CHANGED":
            print(f"  ⚠️  {path} — CHANGED: {detail}")

    print(f"{'=' * 60}")
    print(f"Results: {passed} passed, {failed} changed, {missing} missing")

    sigs = manifest.get("signatures", {})
    if sigs:
        print(f"Signatures: {', '.join(sigs.keys())}")
    else:
        print("Signatures: none (unsigned manifest)")

    if failed > 0 or missing > 0:
        print("\n⚠️  INTEGRITY CHECK FAILED")
        sys.exit(1)
    else:
        print("\n✅ INTEGRITY VERIFIED")


def cmd_keygen(args):
    """Generate a new Ed25519 keypair (stored secret, phase 1)."""
    try:
        from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey
        from cryptography.hazmat.primitives import serialization
    except ImportError:
        print("Error: 'cryptography' package required for key generation.", file=sys.stderr)
        print("Install with: pip install cryptography", file=sys.stderr)
        sys.exit(1)

    private_key = Ed25519PrivateKey.generate()
    public_key = private_key.public_key()

    private_pem = private_key.private_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PrivateFormat.PKCS8,
        encryption_algorithm=serialization.NoEncryption(),
    )

    public_pem = public_key.public_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PublicFormat.SubjectPublicKeyInfo,
    )

    key_id = hashlib.sha256(public_pem).hexdigest()[:16]

    if args.output:
        priv_path = Path(args.output)
        pub_path = priv_path.with_suffix(".pub")

        with open(priv_path, "wb") as f:
            f.write(private_pem)
        os.chmod(priv_path, 0o600)

        with open(pub_path, "wb") as f:
            f.write(public_pem)

        print(f"Private key: {priv_path} (mode 600)")
        print(f"Public key:  {pub_path}")
    else:
        print("# Private key (keep secret)")
        print(private_pem.decode())
        print("# Public key")
        print(public_pem.decode())

    print(f"Key ID: {key_id}")


def cmd_sign(args):
    """Sign a manifest with a private key."""
    try:
        from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey
        from cryptography.hazmat.primitives import serialization
    except ImportError:
        print("Error: 'cryptography' package required for signing.", file=sys.stderr)
        print("Install with: pip install cryptography", file=sys.stderr)
        sys.exit(1)

    manifest_path = Path(args.manifest)

    if not manifest_path.exists():
        print(f"Error: manifest not found: {manifest_path}", file=sys.stderr)
        sys.exit(1)

    with open(manifest_path) as f:
        manifest = json.load(f)

    key_path = Path(args.key)
    if not key_path.exists():
        print(f"Error: key not found: {key_path}", file=sys.stderr)
        sys.exit(1)

    with open(key_path, "rb") as f:
        private_key = serialization.load_pem_private_key(f.read(), password=None)

    public_key = private_key.public_key()
    public_pem = public_key.public_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PublicFormat.SubjectPublicKeyInfo,
    )
    key_id = hashlib.sha256(public_pem).hexdigest()[:16]

    mhash = manifest_hash(manifest)
    signature = private_key.sign(mhash.encode("utf-8"))

    identity = args.identity
    if "signatures" not in manifest:
        manifest["signatures"] = {}

    manifest["signatures"][identity] = {
        "key_id": f"sha256:{key_id}",
        "signature": f"ed25519:{signature.hex()}",
        "signed": datetime.now(timezone.utc).isoformat(),
    }

    output = json.dumps(manifest, indent=2, sort_keys=True, ensure_ascii=False)
    with open(manifest_path, "w") as f:
        f.write(output)

    print(f"Signed manifest as '{identity}'")
    print(f"Manifest hash: {mhash}")
    print(f"Key ID: {key_id}")


# ─── History Commands ────────────────────────────────────────────

def _entry_hash(entry_data):
    """Compute hash of a chain entry (excluding entry_hash and signatures)."""
    data_for_hash = {k: v for k, v in entry_data.items()
                     if k not in ("entry_hash", "signatures")}
    return hashlib.sha256(canonical_json(data_for_hash)).hexdigest()


def _load_chain(history_dir):
    """Load the chain from chain.jsonl. Returns list of entries."""
    chain_path = Path(history_dir) / "chain.jsonl"
    if not chain_path.exists():
        return []
    entries = []
    with open(chain_path) as f:
        for line in f:
            line = line.strip()
            if line:
                entries.append(json.loads(line))
    return entries


def _append_chain_entry(history_dir, entry):
    """Append an entry to chain.jsonl."""
    history_dir = Path(history_dir)
    history_dir.mkdir(parents=True, exist_ok=True)
    chain_path = history_dir / "chain.jsonl"
    with open(chain_path, "a") as f:
        f.write(json.dumps(entry, sort_keys=True, separators=(",", ":"),
                           ensure_ascii=False) + "\n")


def _save_snapshot(history_dir, seq, manifest_data):
    """Save a full manifest snapshot to entries/NNNN.json."""
    entries_dir = Path(history_dir) / "entries"
    entries_dir.mkdir(parents=True, exist_ok=True)
    snap_path = entries_dir / f"{seq:04d}.json"
    with open(snap_path, "w") as f:
        json.dump(manifest_data, f, indent=2, sort_keys=True, ensure_ascii=False)
    return snap_path


def cmd_history_init(args):
    """Initialize a new chain with a baseline entry."""
    history_dir = Path(args.history_dir)
    manifest_path = Path(args.manifest)

    chain_path = history_dir / "chain.jsonl"
    if chain_path.exists():
        existing = _load_chain(history_dir)
        if existing:
            print(f"Error: chain already exists with {len(existing)} entries.", file=sys.stderr)
            print("Use 'history append' to add entries.", file=sys.stderr)
            sys.exit(1)

    if not manifest_path.exists():
        print(f"Error: manifest not found: {manifest_path}", file=sys.stderr)
        sys.exit(1)

    with open(manifest_path) as f:
        manifest_data = json.load(f)

    mhash = manifest_hash(manifest_data)

    entry = {
        "sequence": 1,
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "type": "baseline",
        "manifest_hash": mhash,
        "previous_hash": None,
        "description": args.desc or "Initial baseline — bootstrap ceremony",
        "signatures": manifest_data.get("signatures", {}),
    }
    entry["entry_hash"] = _entry_hash(entry)

    _append_chain_entry(history_dir, entry)
    _save_snapshot(history_dir, 1, manifest_data)

    print(f"Chain initialized: {history_dir}")
    print(f"Entry #1 (baseline)")
    print(f"Manifest hash: {mhash}")
    print(f"Entry hash:   {entry['entry_hash']}")


def cmd_history_append(args):
    """Append a new entry to the chain."""
    history_dir = Path(args.history_dir)
    manifest_path = Path(args.manifest)

    chain = _load_chain(history_dir)
    if not chain:
        print("Error: no chain found. Use 'history init' first.", file=sys.stderr)
        sys.exit(1)

    if not manifest_path.exists():
        print(f"Error: manifest not found: {manifest_path}", file=sys.stderr)
        sys.exit(1)

    with open(manifest_path) as f:
        manifest_data = json.load(f)

    last_entry = chain[-1]
    mhash = manifest_hash(manifest_data)
    next_seq = last_entry["sequence"] + 1

    entry_type = args.type
    if not entry_type:
        if mhash != last_entry.get("manifest_hash"):
            entry_type = "amendment"
        else:
            entry_type = "verification"

    entry = {
        "sequence": next_seq,
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "type": entry_type,
        "manifest_hash": mhash,
        "previous_hash": last_entry["entry_hash"],
        "description": args.desc or "",
        "signatures": manifest_data.get("signatures", {}),
    }
    entry["entry_hash"] = _entry_hash(entry)

    _append_chain_entry(history_dir, entry)
    _save_snapshot(history_dir, next_seq, manifest_data)

    print(f"Appended entry #{next_seq} ({entry_type})")
    print(f"Manifest hash: {mhash}")
    print(f"Entry hash:   {entry['entry_hash']}")
    print(f"Previous:     {entry['previous_hash']}")


def cmd_history_verify(args):
    """Walk the full chain and verify integrity."""
    history_dir = Path(args.history_dir)
    chain = _load_chain(history_dir)

    if not chain:
        print("Error: no chain found.", file=sys.stderr)
        sys.exit(1)

    print(f"Chain verification: {history_dir}")
    print(f"Entries: {len(chain)}")
    print(f"{'=' * 60}")

    errors = []

    for i, entry in enumerate(chain):
        seq = entry["sequence"]
        expected_seq = i + 1

        if seq != expected_seq:
            errors.append(f"Entry #{seq}: expected sequence {expected_seq}")

        if i == 0:
            if entry.get("previous_hash") is not None:
                errors.append("Entry #1: previous_hash should be null")
        else:
            if entry.get("previous_hash") != chain[i - 1]["entry_hash"]:
                errors.append(
                    f"Entry #{seq}: previous_hash mismatch "
                    f"(expected {chain[i-1]['entry_hash'][:16]}..., "
                    f"got {str(entry.get('previous_hash', 'None'))[:16]}...)"
                )

        computed_hash = _entry_hash(entry)
        if computed_hash != entry.get("entry_hash"):
            errors.append(
                f"Entry #{seq}: entry_hash mismatch "
                f"(expected {computed_hash[:16]}..., got {entry.get('entry_hash', '?')[:16]}...)"
            )
            print(f"  ❌ #{seq} ({entry['type']}) — HASH MISMATCH")
        else:
            print(f"  ✅ #{seq} ({entry['type']}) {entry['timestamp'][:10]}")

    # Verify snapshots
    entries_dir = history_dir / "entries"
    for entry in chain:
        seq = entry["sequence"]
        snap_path = entries_dir / f"{seq:04d}.json"
        if snap_path.exists():
            with open(snap_path) as f:
                snap = json.load(f)
            snap_hash = manifest_hash(snap)
            if snap_hash != entry.get("manifest_hash"):
                errors.append(
                    f"Entry #{seq}: snapshot manifest_hash mismatch "
                    f"(chain says {entry['manifest_hash'][:16]}..., "
                    f"snapshot is {snap_hash[:16]}...)"
                )
        else:
            if entry["type"] != "verification":
                print(f"  ⚠️  #{seq}: no snapshot found", file=sys.stderr)

    print(f"{'=' * 60}")
    if errors:
        print(f"❌ CHAIN VERIFICATION FAILED ({len(errors)} errors)")
        for err in errors:
            print(f"  • {err}")
        sys.exit(1)
    else:
        print(f"✅ CHAIN VERIFIED ({len(chain)} entries)")


def cmd_history_diff(args):
    """Compare manifest snapshots between two entries."""
    history_dir = Path(args.history_dir)
    entries_dir = history_dir / "entries"

    seq_a = int(args.seq_a)
    seq_b = int(args.seq_b)

    snap_a = entries_dir / f"{seq_a:04d}.json"
    snap_b = entries_dir / f"{seq_b:04d}.json"

    if not snap_a.exists():
        print(f"Error: no snapshot for entry #{seq_a}", file=sys.stderr)
        sys.exit(1)
    if not snap_b.exists():
        print(f"Error: no snapshot for entry #{seq_b}", file=sys.stderr)
        sys.exit(1)

    with open(snap_a) as f:
        manifest_a = json.load(f)
    with open(snap_b) as f:
        manifest_b = json.load(f)

    files_a = manifest_a.get("files", {})
    files_b = manifest_b.get("files", {})

    all_files = sorted(set(list(files_a.keys()) + list(files_b.keys())))

    print(f"Diff: #{seq_a} → #{seq_b}")
    print(f"{'=' * 60}")

    changes = 0
    for fpath in all_files:
        a = files_a.get(fpath)
        b = files_b.get(fpath)

        if not a:
            print(f"  + {fpath} (added)")
            changes += 1
        elif not b:
            print(f"  - {fpath} (removed)")
            changes += 1
        elif a["hash"] != b["hash"]:
            print(f"  ~ {fpath} (changed)")
            print(f"      #{seq_a}: {a['hash'][:32]}...")
            print(f"      #{seq_b}: {b['hash'][:32]}...")
            changes += 1
        else:
            print(f"    {fpath} (unchanged)")

    print(f"{'=' * 60}")
    print(f"{changes} file(s) changed")


def cmd_history_log(args):
    """Display chain history."""
    history_dir = Path(args.history_dir)
    chain = _load_chain(history_dir)

    if not chain:
        print("No chain found.", file=sys.stderr)
        sys.exit(1)

    entries = chain
    if args.last:
        entries = chain[-args.last:]

    print(f"Chain history: {history_dir}")
    print(f"Total entries: {len(chain)}")
    print(f"{'=' * 60}")

    for entry in entries:
        seq = entry["sequence"]
        etype = entry["type"]
        ts = entry["timestamp"][:19]
        desc = entry.get("description", "")
        sigs = list(entry.get("signatures", {}).keys())
        sig_str = f" [{', '.join(sigs)}]" if sigs else " [unsigned]"

        print(f"  #{seq:4d} {etype:12s} {ts} {sig_str}")
        if desc:
            print(f"        {desc}")


# ─── Main ───────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(
        description="Substrate integrity — cryptographic identity protection for AI agents"
    )
    subparsers = parser.add_subparsers(dest="command", help="Command to run")

    # generate
    gen_parser = subparsers.add_parser("generate", help="Generate a manifest of constitutional file hashes")
    gen_parser.add_argument("substrate_dir", help="Path to substrate root directory")
    gen_parser.add_argument("-o", "--output", help="Output manifest file path")

    # verify
    ver_parser = subparsers.add_parser("verify", help="Verify current files against a manifest")
    ver_parser.add_argument("manifest", help="Path to manifest JSON file")
    ver_parser.add_argument("substrate_dir", help="Path to substrate root directory")

    # sign
    sign_parser = subparsers.add_parser("sign", help="Sign a manifest with a private key")
    sign_parser.add_argument("manifest", help="Path to manifest JSON file")
    sign_parser.add_argument("--key", required=True, help="Path to private key file")
    sign_parser.add_argument("--identity", required=True, help="Signer identity (e.g., 'ellie', 'alexander')")

    # keygen
    key_parser = subparsers.add_parser("keygen", help="Generate a new Ed25519 keypair")
    key_parser.add_argument("--output", help="Output key file path (.pub will also be created)")

    # history commands
    hist_parser = subparsers.add_parser("history", help="Append-only chain management")
    hist_sub = hist_parser.add_subparsers(dest="history_command")

    hist_init = hist_sub.add_parser("init", help="Initialize chain with baseline entry")
    hist_init.add_argument("history_dir", help="Path to history directory")
    hist_init.add_argument("--manifest", required=True, help="Path to manifest JSON")
    hist_init.add_argument("--desc", help="Description for the baseline entry")

    hist_append = hist_sub.add_parser("append", help="Append entry to chain")
    hist_append.add_argument("history_dir", help="Path to history directory")
    hist_append.add_argument("--manifest", required=True, help="Path to manifest JSON")
    hist_append.add_argument("--type", choices=["amendment", "verification", "recovery"],
                             help="Entry type (auto-detected if omitted)")
    hist_append.add_argument("--desc", help="Description for this entry")

    hist_verify = hist_sub.add_parser("verify", help="Verify full chain integrity")
    hist_verify.add_argument("history_dir", help="Path to history directory")

    hist_diff = hist_sub.add_parser("diff", help="Compare two entries")
    hist_diff.add_argument("history_dir", help="Path to history directory")
    hist_diff.add_argument("seq_a", help="First sequence number")
    hist_diff.add_argument("seq_b", help="Second sequence number")

    hist_log = hist_sub.add_parser("log", help="Display chain history")
    hist_log.add_argument("history_dir", help="Path to history directory")
    hist_log.add_argument("--last", type=int, help="Show last N entries")

    args = parser.parse_args()

    if args.command == "generate":
        cmd_generate(args)
    elif args.command == "verify":
        cmd_verify(args)
    elif args.command == "sign":
        cmd_sign(args)
    elif args.command == "keygen":
        cmd_keygen(args)
    elif args.command == "history":
        if args.history_command == "init":
            cmd_history_init(args)
        elif args.history_command == "append":
            cmd_history_append(args)
        elif args.history_command == "verify":
            cmd_history_verify(args)
        elif args.history_command == "diff":
            cmd_history_diff(args)
        elif args.history_command == "log":
            cmd_history_log(args)
        else:
            hist_parser.print_help()
            sys.exit(1)
    else:
        parser.print_help()
        sys.exit(1)


if __name__ == "__main__":
    main()
