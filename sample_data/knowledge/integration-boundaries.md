# Integration Boundaries

- CRM, meeting, and messaging integrations are accessed through typed adapter interfaces.
- Local replay adapters are the default and are the only adapters enabled in this portfolio project.
- A production adapter would require separate credentials, rate-limit handling, audit review, and data-processing approval.
- Approval is a workflow boundary; an adapter cannot send a message before the approved state is durably recorded.

