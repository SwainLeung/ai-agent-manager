# 02 — Dynamic skill governance

Do not load every skill into every task. Keep a compact registry containing
identity, description, triggers, version, lifecycle state, and usage signals.
Use that metadata for lightweight routing; load the full implementation only
after selection.

Usage counts, success rates, and recent activity support hot/warm/cold
classification. Failed executions should produce a repair proposal that is
tested as a new version, reviewed, and kept rollbackable. Canary or staged
release is safer than silently replacing a working skill.
