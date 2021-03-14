# Deployment Guide

- HTTP/S: REST-Based Service
- Port: 80
- Cloud Build: Build Pipeline
- Kubernetes: Manifests for Deployment
- Docker: Container Management

---
## Cloud Build
---
## Docker
### Details
The docker image is a multistage build image.
View more in the [developer_setup](developer_setup.md) guide.

Acknowledgments to [michael0liver's example](https://github.com/michael0liver/python-poetry-docker-example)

---
## Deployment

We use a variety of technologies to get this code into production.  Starting from this repo and going outwards:

1. github actions builds and deploys a docker container to ecr
    1. prs and pushes to this repo will build and push a 'short-sha' container to AWS' ECR. The build details are written to ``/app/version.json``.
    1. Code merged to main will trigger a build that prefixes the short sha with literal 'stg-'
    1. Code released with a good version tag should get released to prod (this is to be determined, does not work, but is plan of record)
1. A helm release is configured in ctms-infra
    1. https://github.com/mozilla-it/ctms-infra/tree/main/k8s
    1. We can trigger a release by updating the correct files there (For helm chart or helm chart value changes)
    1. by default we will also configure new images in the ECR to trigger a build
1. The eks clusters in the ess account are configured with fluxcd/helm operator to watch those helm release files
1. terraform defines the eks clusters, and any databases we may require (https://github.com/mozilla-it/ctms-infra/tree/main/terraform)
