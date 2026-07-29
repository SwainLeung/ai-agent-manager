# 06 — Loop Engineering

Five cooperating loops keep an Agent useful over time:

- **Execution:** route, load, run, checkpoint, and record outcomes.
- **Skill-to-Script:** identify stable high-frequency work and propose
  deterministic implementations.
- **User adaptation:** turn scoped feedback into reversible profile/project
  candidates.
- **Self-correction:** detect failure, choose a fallback or repair, and retry
  with bounded attempts.
- **Anti-entropy:** prune stale, duplicate, unowned, and oversized assets.

All loops should emit observable events and pass through review gates for
high-impact mutations.
