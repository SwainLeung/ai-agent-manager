# Changelog

## [Unreleased]

- Reserved for future changes after public review.

## [0.2.0] - 2026-07-29

- Added a provider-neutral Graph Scheduler with checkpoints and max-step protection.
- Added retry and error-edge fallback handling for graph nodes.
- Added JSON execution traces with run, node, failure, checkpoint, and completion events.
- Added `graph run` and `trace show` CLI commands.
- Added scheduler, retry, fallback, resume, and trace persistence tests.

## [0.1.0] - 2026-07-29

- Added registry-driven skill descriptors and lazy keyword routing.
- Added Skills-versus-Scripts decision scoring.
- Added lifecycle health proposals and hot/warm/cold tiers.
- Added feedback events for undo, redo, pitfalls, fallbacks, and corrections.
- Added graph validation and anti-entropy auditing.
- Added theory distillations, tests, and GitHub Actions CI.
