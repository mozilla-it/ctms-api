# Deployment Guide

- HTTP/S: REST-Based Service
- Port: 80
- Cloud Build: Build Pipeline
- Kubernetes: Manifests for Deployment
- Docker: Container Management

---
## Cloud Build
### Details
Cloud Build uses the [cloudbuild.yaml](../cloudbuild.yaml) file as a build pipeline using containerized images at each step.

In the cloudbuild.yaml, we have three steps:
1. Build and tag docker image
2. Push the image to Google Container Registry (gcr)
3. Setup K8s through [clouddeploy](../clouddeploy) bash script

### Running Locally
Follow the article below to install the `cloud-build-local` and view additional configuration options:
- https://cloud.google.com/cloud-build/docs/build-debug-locally

Run the following to build locally:
> cloud-build-local --config=cloudbuild.yaml --dryrun=false --substitutions=REPO_NAME=ctms-api,SHORT_SHA=1a2b3c4 .
---
## Kubernetes
### Details
filename:intent
- [deploy.yaml](../k8s/deploy.yaml): Deployment manifest, along with confirmation health probes
- [ns.yaml](../k8s/ns.yaml): Namespace manifest
- [svc.yaml](../k8s/svc.yaml): Service manifest
- [ing.yaml](../k8s/ing.yaml): Ingress manifest
- [cert.yaml](../k8s/cert.yaml): ManagedCertificate manifest

### *-Infra
There was also some infra setup required for providing permissions to the cloudbuilder to \
push to different gcp projects as well as dns setup required.

---
## Docker
### Details
The docker image is a multistage build image.
View more in the [developer_setup](developer_setup.md) guide.

Acknowledgments to [michael0liver's example](https://github.com/michael0liver/python-poetry-docker-example)
