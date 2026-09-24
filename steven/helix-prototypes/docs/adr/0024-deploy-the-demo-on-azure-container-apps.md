# Deploy the demo on Azure Container Apps

HELIX deploys the Next.js frontend and FastAPI backend as separate Azure Container Apps, with Azure Database for PostgreSQL Flexible Server, Azure Container Registry, Key Vault, and Log Analytics. Only the authenticated frontend has public ingress. The frontend proxies same-origin API calls to the internal backend, which prevents direct public access to model-spending commands while preserving separate frontend and backend resources.

## Considered options

- Azure Static Web Apps with App Service.
- Azure Container Apps with an internal backend.
- Azure Kubernetes Service with separate workloads.

## Consequences

Bicep defines the environment and immutable image revisions. The backend reads secrets through managed identity and uses private PostgreSQL connectivity. This is a synthetic demo topology, not a claim of production availability, regulatory qualification, or multi-region recovery.
