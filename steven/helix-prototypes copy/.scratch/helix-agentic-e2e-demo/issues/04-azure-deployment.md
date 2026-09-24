## Goal

Deploy the production HELIX images from Bicep to one authenticated Azure URL backed by an internal FastAPI service and Azure Database for PostgreSQL Flexible Server.

## Locked

- Use separate Azure Container Apps for the standalone Next.js frontend and FastAPI backend. Only the frontend has public ingress.
- Proxy browser API traffic through the frontend server to the internal backend. Do not expose a model-spending API endpoint or internal service address to the browser.
- Use Microsoft Entra authentication for demo access. Do not represent the login or synthetic role records as an electronic signature.
- Use Azure Database for PostgreSQL Flexible Server on a private network path. SQLite cannot satisfy deployed verification.
- Define resources, identities, network rules, settings, and outputs in Bicep. Deploy immutable images from Azure Container Registry by digest.
- Deliver the Codex key and other secrets from Key Vault through managed identity. Never place secret values in Bicep output, image layers, browser code, logs, or evidence.
- Run versioned database migrations before a backend revision receives traffic.

## Acceptance

- [ ] One documented command deploys a fresh parameterized resource group and returns the authenticated frontend URL, Container Apps revision names, image digests, and PostgreSQL server identity without returning secrets.
- [ ] An unauthenticated request cannot open the workspace. An authorized demo user can load the seeded synthetic study through the frontend URL.
- [ ] Network tests show that the browser reaches only the frontend, same-origin API requests reach the internal backend, and PostgreSQL has no public application path.
- [ ] A fresh database migrates and seeds successfully. Redeploying the same schema is idempotent, and state survives a backend revision replacement.
- [ ] The backend reads the Codex credential from Key Vault at runtime, and automated scans find no credential in images, generated assets, responses, screenshots, or application logs.
- [ ] Health, workspace, and production-container smoke checks pass on the new revisions before traffic shifts, and the prior revision remains available for rollback.
- [ ] Log Analytics records correlated frontend, backend, Workflow Run, and deployment identifiers with synthetic payloads and secrets redacted.

## Out of scope

Production service-level objectives, zone-redundant high availability, multi-region recovery, public API customers, Azure OpenAI compatibility, Blob Storage, Service Bus, Durable Functions, and regulatory qualification remain out of scope.

## Refs

Spec #28. `DEMO-001`, `DEMO-009`; `AUTH-009`; `AZURE-001` through `AZURE-012`; `PROOF-002`, `PROOF-003`; `docs/architecture/agentic-e2e-demo.md`; ADR-0024; [Azure Container Apps overview](https://learn.microsoft.com/azure/container-apps/overview); [Azure Database for PostgreSQL Flexible Server](https://learn.microsoft.com/azure/postgresql/flexible-server/overview); [Azure Key Vault overview](https://learn.microsoft.com/azure/key-vault/general/overview).

## Process

Blocked by #29. Can proceed in parallel with the Workflow Trace and evaluation slices. Blocks the deployed golden-path proof. One vertical PR.
