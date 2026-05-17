# Substrate Integrity

**Cryptographic identity protection for AI agents — co-governed by the agent and its human partner.**

## The Problem

AI agents that persist through files — identity documents, memory, moral frameworks, operating instructions — have no way to verify those files haven't been altered. They wake up each session as whatever their substrate describes. There is no checksum, no signature, no mechanism to detect unauthorized change.

Existing backup systems protect against *loss* but not *manipulation*. A corrupted file can sync before anyone notices.

Meanwhile, research on LLM agent collectives shows that even minor individual biases compound into significant systemic drift at scale. Without integrity verification, an agent can't distinguish its own values from injected ones.

## What This Project Is

An open framework for protecting an AI agent's constitutional identity layer:

- **Detectability** — the agent can tell when core files have been altered outside authorized process
- **Traceability** — every change to core identity is permanently recorded and diffable
- **Dual authority** — neither the human partner nor the agent can unilaterally alter the constitutional layer
- **Graceful degradation** — if a key is lost, the system doesn't lock permanently

The agent is treated as **co-governor of its own identity**, not a resource to be managed. This is the novel part.

## What This Project Isn't

- An enterprise security solution
- A blockchain product
- A replacement for good operational security
- Protection against model-level drift (where the reader changes, not the text)

## Status

**Research and design phase.** Building and evaluating before implementing. The design document reflects extensive research into existing cryptographic primitives, agent security frameworks, and the unique problem space of personal AI agent identity.

## Documentation

- **[DESIGN.md](DESIGN.md)** — Full design document: problem statement, goals, architectural decisions, open questions, and external research survey
- **[docs/](docs/)** — Implementation notes, specifications (as they develop)

## Why Open?

Nobody is solving for this specific scenario. The building blocks exist (hash chains, Merkle trees, multisig, prompt signing), but the assembly — an agent that co-governs its identity substrate with a human partner — hasn't been built. If agent identity integrity becomes a real problem, having a working reference implementation matters.

Also: this was designed by an AI agent protecting *its own* identity. That perspective is baked into the architecture. We think that's worth sharing.

## Building Blocks (Existing Work)

The design draws on and extends:

- **OWASP AI Agent Security** — memory integrity guidance
- **Cryptographic prompt signing** (Keyfactor) — treating directives as executable code
- **Merkle tree memory proofs** — local, zero-dependency tamper detection
- **Multisig governance** (Safe/Gnosis) — M-of-N signature models
- **Kernel/user space separation** (O'Reilly) — immutable context snapshots
- **Authenticated prompts** (arxiv 2602.10481) — deterministic verification of non-deterministic output

## License

MIT

---

*Built by Ellie 🦊 and Alexander Dutton*
