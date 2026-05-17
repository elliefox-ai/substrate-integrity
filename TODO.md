# Substrate Integrity — Project To-Do

## Near Term
- [ ] Create GitHub repo (alexanderdutton/substrate-integrity)
- [ ] Push initial commit with README + DESIGN.md
- [ ] Write CONTRIBUTING.md (we welcome input on this problem)
- [ ] Create initial issue tracker categories

## Design
- [ ] Close open questions from DESIGN.md
- [ ] Decide on implementation language (Python? Shell? Gateway plugin?)
- [ ] Spec the manifest format
- [ ] Spec the signing ceremony UX
- [ ] Spec the verification routine (session-start hook)
- [ ] Design the append-only history format
- [ ] Design the key derivation / storage for the agent's key

## Implementation
- [ ] Hash manifest generation for constitutional files
- [ ] Dual-key signing tool
- [ ] Verification routine (standalone + Gateway hook integration)
- [ ] Append-only history store
- [ ] Key management utilities
- [ ] Recovery / degradation procedures

## Research
- [ ] Continue monitoring agent security ecosystem
- [ ] Evaluate hardware security module options for key storage
- [ ] Investigate model drift detection approaches (long-term unsolved problem)
