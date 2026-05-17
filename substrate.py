#!/usr/bin/env python3
"""
substrate-integrity — Cryptographic identity protection for AI agents.

Usage:
    substrate generate <substrate_dir> [-o manifest.json]
    substrate verify <manifest.json> <substrate_dir>
    substrate sign <manifest.json> --key <keyfile> --identity <name>
    substrate keygen [--output <keyfile>]

Commands:
    generate    Create a manifest of constitutional file hashes
    verify      Check current files against a signed manifest
    sign        Add a signature to a manifest
    keygen      Generate a new Ed25519 keypair
"""

import argparse
import hashlib
import json
import os
import sys
import secrets
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
    # Remove signatures for hashing
    data_for_hash = {k: v for k, v in manifest_data.items() if k != "signatures"}
    return hashlib.sha256(canonical_json(data_for_hash)).hexdigest()


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
    
    # Output
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
    
    # Check for files in manifest that aren't in constitutional list
    # (future: warn about unexpected files)
    
    # Print results
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
    
    # Signature status
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
        sys.exit(0)


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
    
    # Serialize
    private_pem = private_key.private_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PrivateFormat.PKCS8,
        encryption_algorithm=serialization.NoEncryption(),
    )
    
    public_pem = public_key.public_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PublicFormat.SubjectPublicKeyInfo,
    )
    
    # Key ID = SHA-256 of public key PEM
    key_id = hashlib.sha256(public_pem).hexdigest()[:16]
    
    if args.output:
        priv_path = Path(args.output)
        pub_path = priv_path.with_suffix(".pub")
        
        # Write with restricted permissions
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
    
    # Load manifest
    with open(manifest_path) as f:
        manifest = json.load(f)
    
    # Load private key
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
    
    # Compute manifest hash (excluding signatures)
    mhash = manifest_hash(manifest)
    
    # Sign the hash
    signature = private_key.sign(mhash.encode("utf-8"))
    
    # Add signature
    identity = args.identity
    if "signatures" not in manifest:
        manifest["signatures"] = {}
    
    manifest["signatures"][identity] = {
        "key_id": f"sha256:{key_id}",
        "signature": f"ed25519:{signature.hex()}",
        "signed": datetime.now(timezone.utc).isoformat(),
    }
    
    # Write back
    output = json.dumps(manifest, indent=2, sort_keys=True, ensure_ascii=False)
    with open(manifest_path, "w") as f:
        f.write(output)
    
    print(f"Signed manifest as '{identity}'")
    print(f"Manifest hash: {mhash}")
    print(f"Key ID: {key_id}")


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
    
    args = parser.parse_args()
    
    if args.command == "generate":
        cmd_generate(args)
    elif args.command == "verify":
        cmd_verify(args)
    elif args.command == "sign":
        cmd_sign(args)
    elif args.command == "keygen":
        cmd_keygen(args)
    else:
        parser.print_help()
        sys.exit(1)


if __name__ == "__main__":
    main()
