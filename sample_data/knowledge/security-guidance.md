# Security and Privacy Guidance

- Webhook requests must use an HMAC SHA-256 signature calculated over the exact request body.
- API requests require a bearer token in local and deployed environments.
- Store only the minimum account and meeting information needed for the workflow demonstration.
- Never place secrets, credentials, or sensitive customer data in prompts, logs, fixtures, or screenshots.

