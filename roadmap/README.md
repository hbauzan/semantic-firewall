# Roadmap Directory — Three-Headed Semantic Firewall

> **Operational Hub for Autonomous AI Coding Agents**  
> **Master Specification:** [`../roadmap.md`](../roadmap.md)  
> **Legacy Archive:** [`./archive_v2.34.0/`](./archive_v2.34.0/README.md)

---

## Directory Organization

```
roadmap/
├── README.md                      <- You are here (AI Agent dispatch guide)
├── tickets/                       <- Atomic actionable implementation tickets (TK-01 to TK-06)
│   ├── README.md                  <- Ticket index & execution protocol
│   ├── TK01-numerical-purity-enforcement.md
│   ├── TK02-head1-cosine-difference-gate.md
│   ├── TK03-head2-excited-dimensions-counter.md
│   ├── TK04-head3-fine-harmonic-resonance.md
│   ├── TK05-config-state-and-telemetry-parity.md
│   └── TK06-empirical-benchmark-validation.md
└── archive_v2.34.0/               <- Complete historical archive of all pre-v2.34.0 work
```

---

## Instructions for AI Agents Taking a Ticket

When you (an autonomous AI coding assistant) are instructed to implement a step from this roadmap:

1. **Claim Exactly One Ticket:**
   Read the target ticket in `tickets/` in full before modifying any source code.
2. **Review the Mathematical Axioms:**
   Consult [`../ddi-fw/rfc-numerical-purity-catastrophe.md`](../ddi-fw/rfc-numerical-purity-catastrophe.md) and [`../ddi-fw/universal-remediation-directive.md`](../ddi-fw/universal-remediation-directive.md). Absolute precision without rounding is the law of this repository.
3. **Follow Strict TDD:**
   Write failing unit tests first under `backend/tests/`, implement the minimal clean code to make them pass, and ensure no regressions occur across the existing 118 unit tests.
4. **Enforce DoD:**
   Each ticket specifies explicit Definition of Done checklists. Never mark a ticket complete unless all automated tests pass.
