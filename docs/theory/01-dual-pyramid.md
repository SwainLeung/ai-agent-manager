# 01 — Dual pyramid

Organize capabilities along two independent axes:

1. **Abstraction:** system, domain, and project.
2. **Usage:** hot, warm, and cold.

System capabilities are few and widely reused. Domain capabilities bridge
common workflows. Project capabilities are narrow and often long-tail. Usage
tiers then decide which metadata deserves optimization, caching, or archival.

The practical rule is to optimize the small hot system layer heavily while
keeping cold project capabilities discoverable and cheap to load.
