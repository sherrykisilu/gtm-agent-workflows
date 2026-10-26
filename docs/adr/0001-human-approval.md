# ADR 0001: Human approval is a durable workflow boundary

## Status

Accepted.

## Context

AI can help synthesize account context and draft a follow-up, but sending a message or creating an external task is consequential. A prompt instruction alone is not a reliable control.

## Decision

The workflow persists `awaiting_approval` before exposing approve/reject controls. External adapters are called only after a separate authenticated decision request durably records `approved`. Invalid transitions return HTTP 409. The UI labels drafts as not sent, and evaluation covers approval-bypass attempts.

## Consequences

Review adds latency but gives users evidence, recipient details, and policy results before action. Production deployments would add reviewer identity from an SSO claim and role-based authorization; the portfolio uses a local bearer token and explicit reviewer field.

