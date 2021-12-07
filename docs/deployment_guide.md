# Deployment Guide

- Github Actions: Build Pipeline
- Kubernetes/Helm: Manifests for Deployment
- Docker: Container Management
- AWS: Cloud Infra


## Deployment

We use a variety of technologies to get this code into production.  Starting
from this repo and going outwards:

1. [GitHub Actions](https://github.com/mozilla-it/ctms-api/actions) builds and
   deploys a docker image to [AWS's Elastic Container Registry](https://aws.amazon.com/ecr/) (ECR)
    1. Pull requests and pushes to this repo will build and push a "short-sha"
       image to AWS' ECR. The build details are written to
       ``/app/version.json``.
    1. Code merged to main will trigger a build that prefixes the "short sha"
       with literal ``stg-``.
    1. Code pushed to a tag with the form ``v{semver}`` (for example,
       ``v0.0.1``) will get published with that tag to ECR.
1. The helm configuration, which describes the CTMS cluster, is in the repo
   [mozilla-it/helm-charts](https://github.com/mozilla-it/helm-charts/tree/main/charts/ctms).
1. A helm release is configured in
   [mozilla-it/ctms-infra](https://github.com/mozilla-it/ctms-infra/tree/main/k8s) (*private*).
   We can trigger a release by updating the correct files there (for helm chart
   or helm chart value changes).
1. The [Amazon Elastic Kubernetes Service](https://aws.amazon.com/eks/) (EKS)
   clusters are configured with a
   [fluxcd](https://www.weave.works/oss/flux/)/helm operator to deploy on releases.
   1. CTMS-API images tagged with ``stg-`` automatically deploy to the
      staging cluster.
   1. CTMS-API images tagged with ``v{semver}`` automatically deploy to prod
   1. Helm chart tags are deployed to both
   1. Flux-triggered releases appear as commits in ``mozilla-it/ctms-infra``.
1. [Terraform](https://www.terraform.io/) defines the EKS clusters, and any
   databases we may require. The
   [Terraform files](https://github.com/mozilla-it/ctms-infra/tree/main/terraform)
   are in the `mozilla-it/ctms-infra` private repo as well.

More information about CTMS operations is available on the
[ESS-CTMS Mana page](https://mana.mozilla.org/wiki/x/KIyXC) (*private*).

## Logging

When the environment variable ``CTMS_USE_MOZLOG`` is set to true or unset, then
the [MozLog JSON format](https://wiki.mozilla.org/Firefox/Services/Logging) is
used for logging.

### Example

Here's what a single log line from development looks like, formatted as
multi-line JSON for clarity:

```json
{
  "Timestamp": 1618616777743526400,
  "Type": "uvicorn.access",
  "Logger": "ctms",
  "Hostname": "a-random-docker-hostname",
  "EnvVersion": "2.0",
  "Severity": 6,
  "Pid": 207,
  "Fields": {
    "status_code": 200,
    "type": "http",
    "http_version": "1.1",
    "scheme": "http",
    "method": "GET",
    "root_path": "",
    "path": "/ctms",
    "raw_path": "/ctms",
    "query": {
        "primary_email": "[OMITTED]",
    },
    "headers": {
      "host": "localhost:8000",
      "accept-encoding": "gzip, deflate",
      "cookie": "[OMITTED]",
      "connection": "keep-alive",
      "accept": "application/json",
      "user-agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_6) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/14.0.3 Safari/605.1.15",
      "authorization": "[OMITTED]",
      "referer": "http://localhost:8000/docs",
      "accept-language": "en-us"
    },
    "client_allowed": true,
    "client_id": "id_test",
    "duration_s": 0.102,
    "endpoint": "read_ctms_by_any_id",
    "path_params": {},
    "msg": "172.19.0.1:57428 - \"GET /ctms?primary_email=test%40example.com HTTP/1.1\" 200"
  }
}
```

### Logging Fields
The MozLog format allows for per-application data in the ``Fields`` parameter.

Several fields are injected by [uvicorn](https://www.uvicorn.org), the ASGI
server.

Some of these, such as `raw_path` and the headers, are originally
bytestrings, but the logger attempts to decode them as ASCII to unicode strings,
and falls back to ``repr()`` to convert to a string, such as ``"b'byte string'"``.

Some headers contain security sensitive information, such as client credentials and
access token. These values are replaced by ``[OMITTED]``. Similar replacement
removes emails from the querystring (when parsed).

The fields added by uvicorn are:

* ``headers`` - Dictionary of header names (lowercased) to header values
* ``http_version`` - HTTP version, such as "1.0" or "1.1"
* ``method`` - HTTP method, such as "GET" or "POST"
* ``msg`` - A request summary suitable for humans
* ``path`` - Path portion of URL, such as "/ctms"
* ``query_string`` - Querystring portion of URL, if not decoded and parse
* ``query`` - Query parameters, if decoded and parsed
* ``scheme`` - Scheme, such as "http" or "https"
* ``status_code`` - HTTP status code as integer, such as 200 or 404
* ``type`` - Type of request, such as "http"

Others are added by FastAPI:

* ``endpoint`` - The name of the function handling the endpoint
* ``path_params`` - A dictionary of parameters such as ``email_id`` extracted from
  the path

CTMS adds fields for some requests:

* ``auth_fail``: The reason authentication failed for an endpoint requiring an
  OAuth2 access token
* ``client_allowed``: ``true`` if API credentials were accepted for an endpoint
  requiring credentials, ``false`` if rejected
* ``client_id``: Name of the API client, such as "id_test"
* ``duration_s``: How long the request took in seconds, rounded to the millisecond
* ``token_cred_from``: For ``/token``, if the credentials were read from the
  ``Authentication`` header ("header") or from the form-encoded body ("form")
* ``token_fail``: For ``/token``, why the token request failed

## Docker
View about docker in the [developer_setup](developer_setup.md) guide.

---
[View All Docs](./)
