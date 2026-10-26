# ADR 0002: External systems are behind typed adapters

## Status

Accepted.

## Context

The project must demonstrate integration engineering without requiring paid Salesforce, HubSpot, Gong, Slack, or LLM accounts and without implying those systems were used in production.

## Decision

CRM, meeting, messaging, and brief generation are expressed as typed interfaces. Local replay implementations are the default and only shipped runtime implementations. API and webhook boundaries still demonstrate authentication, HMAC verification, idempotency, lifecycle handling, and failure isolation.

## Consequences

The demo is reproducible and honest about its limits. A real adapter can be added without changing the workflow contract, but must separately address OAuth, secret storage, pagination, rate limits, provider retries, deletion, audit, and data-processing requirements.

