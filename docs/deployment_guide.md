# Deployment Guide

- Github Actions: Build Pipeline
- Kubernetes/Helm: Manifests for Deployment
- Docker: Container Management
- AWS: Cloud Infra

## Overview

There are two deployed instances of CTMS:

* https://ctms.prod.mozilla-ess.mozit.cloud/ - The production instance
* https://ctms.stage.mozilla-ess.mozit.cloud/ - The staging instance

There are some useful endpoints for deployers:

* ``/__version__`` - reports the source code version used to build the images
* ``/__lbheartbeat__`` - returns a 200 response when the service is running
* ``/__heartbeat__`` - returns a 200 response when the backing services, such
  as the database, are running, as well as some additional info.

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


## Synchronized Acoustic Fields

The list of contact fields to be synchronized with Acoustic is controlled by the `acoustic_field` table
in the database.

In order to add or remove certain fields, use the `acoustic_fields.py` script:

```
python ctms/bin/acoustic_fields.py remove fxaaa_id
python ctms/bin/acoustic_fields.py add fxa_id
```

## Logging

When the environment variable ``CTMS_USE_MOZLOG`` is set to true or unset, then
the [MozLog JSON format](https://wiki.mozilla.org/Firefox/Services/Logging) is
used for logging. Logs are aggregated to [Papertrail](https://www.papertrail.com/),
and are useful for debugging issues with deployments.

### Example

Here's what a single log line may looks like, formatted as multi-line JSON for
clarity:

```json
{
  "Timestamp": 1638907127116059400,
  "Type": "ctms.web",
  "Logger": "ctms",
  "Hostname": "ctms-web-1234abcd56-asdfg",
  "EnvVersion": "2.0",
  "Severity": 6,
  "Pid": 10,
  "Fields": {
    "client_host": "172.16.255.255",
    "method": "POST",
    "path": "/ctms",
    "path_template": "/ctms",
    "headers": {
      "host": "ctms.prod.mozilla-ess.mozit.cloud",
      "content-length": "522",
      "user-agent": "python-requests/2.25.1",
      "accept-encoding": "gzip, deflate",
      "accept": "*/*",
      "authorization": "[OMITTED]",
      "content-type": "application/json"
    },
    "client_allowed": true,
    "client_id": "id_ctms-key",
    "status_code": 201,
    "duration_s": 0.063,
    "msg": "172.16.255.255:54321 id_ctms-key 'POST /ctms HTTP/1.1' 201"
  }
}
```

### Logging Fields
The MozLog format allows for per-application data in the ``Fields`` parameter.

Some headers contain security sensitive information, such as client credentials and
access token. These values are replaced by ``[OMITTED]``. Similar replacement
removes emails from the query string (when parsed).

If tracing by email is desired, a tester can trace their activity in the system
by adding the text ``+trace_me_mozilla_`` to their email, such as
``test+trace_me_mozilla_20211207@example.com``. This works with the
[plus-sign trick](https://gmail.googleblog.com/2008/03/2-hidden-ways-to-get-more-from-your.html)
in Gmail and other email providers to create a unique email address.
This causes the email to appear in logs, along with further request context
for some endpoints.

### API Logging Fields

Requests to the API are logged with Type `ctms.web`. Most are logged at
``INFO`` level (``"Severity": 6``). Application errors (the request and the
traceback) are logged at ``ERROR`` level (Severity 3). Some of the fields are:

* ``auth_fail``: The reason authentication failed for an endpoint requiring an
  OAuth2 access token
* ``client_allowed``: ``true`` if API credentials were accepted for an endpoint
  requiring credentials, ``false`` if rejected
* ``client_host`` - The internal IP of the ingress NGINX server. See the
  headers, such as `x-forwarded-for`, for the client's IP address.
* ``client_id``: Name of the API client, such as ``"id_test"``
* ``duration_s``: How long the request took in seconds, rounded to the
  millisecond
* ``fxa_id_conflict``: If a Stripe API ingested a Customer whose Firefox
  Account ID conflicted with an existing Customer, this is the conflicting
  FxA ID (or list of comma-separated IDs). The existing customer will be
  deleted, and will appears in ``ingest_actions``.
* ``headers`` - Dictionary of header names (lower-cased) to header values
* ``ingest_actions`` - For Stripe APIs, a dictionary of actions (`"created"`,
  `"updated"`, `"deleted"`, `"skipped"`, `"no_change"`) to a list of objects
  (formatted as `"object_type:ID"`, like `"customer:cust_abc123"`).
* ``method`` - HTTP method, such as `"GET"`, `"POST"`, or `"PATCH"`.
* ``msg`` - A summary line for the request, modelled after the uvicorn log
  message format.
* ``path_params`` - A dictionary of URL parameters, if the endpoint is
  parametrized.
* ``path_template`` - A standardized path, such as `"/ctms/{email_id}"`, to
  identify endpoints that take URL parameters.
* ``path`` - Path portion of URL, such as `"/ctms"`.
* ``pubsub_*``: Values parsed from the Javascript Web Token (JWT) claim set for
  ``POST``s to ``/stripe_from_pubsub`` from a Google Pub/Sub push subscription.
* ``status_code``: The returned HTTP status code
* ``token_creds_from``: For ``/token``, if the credentials were read from the
  ``Authentication`` header ("header") or from the form-encoded body ("form")
* ``token_fail``: For ``/token``, why the token request failed
* ``trace_json``: The request payload if tracing via the email address is
  requested.
* ``trace``: An email matching the trace pattern, such as
  ``test+trace_me_mozilla_2021@example.com``
* ``trivial``: `true` if a request is a monitoring request, such as
  ``GET /__lbheartbeat__``. These can be excluded to focus on the "non-trivial"
  requests.

### Acoustic Sync Process Logging Fields

The Acoustic Sync Process is a long-running process that processes a batch of
contacts from a queue in the database, and then sleeps for a bit if it detects
the queue was fully processed. The queue is populated by requests to the API
that update contacts.

On process start, a log message at ``INFO`` level (Severity 6) is emitted, with
type ``"ctms.bin.acoustic_sync"`` and these fields:

* ``sync_feature_flag``: ``true`` if syncing is enabled. If ``false``, the
  database will be cleared without sending to Acoustic.
* ``msg``: The message ``"Setting up sync_service."``

One per batch, a log message at ``INFO`` level (Severity 6) is emitted, with
type ``"ctms.bin.acoustic_sync"`` and these fields:

* ``batch_limit``: The current batch size.
* ``count_exception``: The number of contacts failed due to an exception (omitted if 0).
* ``count_retry``: The number of contacts queued to retry (omitted if 0).
* ``count_skipped``: The number of contacts skipped due to ``sync_feature_flag==false`` (omitted if 0).
* ``count_synced``: The number of contacts successfully synced (omitted if 0).
* ``count_total``: The number of contacts processed.
* ``end_time``: A time stamp for the latest contact update time to sync, or ``"now"`` to get the latest.
* ``loop_duration_s``: The time to sync records, in seconds rounded to milliseconds.
* ``loop_sleep_s``: The planned time to sleep, in seconds rounded to milliseconds.
* ``msg``: The message ``"sync_service cycle complete"``
* ``retry_backlog``: The number of contacts in the retry backlog, including those past the ``retry_limit``.
* ``retry_limit``: The number of times to retry syncing a contact before giving up.
* ``sync_backlog``: The number of contacts in the backlog before syncing.
* ``trivial``: ``true`` if no contacts processed, omitted if some processed.

For each contact, a log message at ``DEBUG`` level (Severity 7) is emitted, or
at ``ERROR`` level (Severity 3) on exceptions, with type
``"ctms.acoustic_service"`` and these fields:

* ``email_id``: The email_id of the contact
* ``exception``: The traceback, if an exception was raised, or omitted on
  success.
* ``fxa_created_date_converted``: ``"success"`` if the FxA creation date was
  parsed as a ``datetime``, ``"failure"`` if not, and ``"skipped"`` if not a
  string.
* ``fxa_created_date_type``: The type of the FxA creation date if not a string.
* ``main_duration_s``: The time to sync to the main contact table, in seconds
  rounded to the millisecond.
* ``main_status``: ``"success"`` if sync to main contact table succeeded, or
  ``"failure"``.
* ``newsletter_count``: The number of newsletter subscriptions synced.
* ``newsletter_duration_s``: The time to sync to the newsletter relational
  table, in seconds rounded to the millisecond.
* ``newsletter_status``: ``"success"`` if sync to the newsletter relational
  table succeeded, or ``"failure"``.
* ``newsletters_skipped``: A list of newsletter slugs not synced to Acoustic.
* ``product_count``: The number of product subscriptions synced.
* ``product_duration_s``: The time to sync to the product relational table, in
  seconds rounded to the millisecond (omitted if no products synced).
* ``product_status``: ``"success"`` if sync to the product relational table
  succeeded, or ``"failure"`` (omitted if no products synced).
* ``skipped_fields``: A list of unexpected contact fields not synced to
  Acoustic.
* ``success``: ``true`` if successfully synced, ``false`` if not
* ``trace``: The email, if the contact email has the ``+trace_me_mozilla_``
  pattern.

## Metrics

[Prometheus](https://prometheus.io/) is used for publishing metrics for the API
and the backend service. These are exported to [InfluxDB](https://www.influxdata.com/)
for further processing and display on dashboards.

The API metrics are fetched from ``/metrics``, and each API instance publishes
and keeps track of its own metrics. This means the same counter should be "summed"
across instances to get a deployment-wide counter. It also means that counters
reset when instances reset, such as during a deployment.

The Acoustic Sync service pushes its metrics to a gateway service, once per
batch cycle. There is a single instance of the sync service, so summing is not
needed, but the counts do reset when the service is restarted or deployed.

### API metrics

The API metrics are:

* ``ctms_requests_duration_seconds_*`` - A
  [histogram](https://prometheus.io/docs/practices/histograms/) of request
  timings, with the labels ``method``, ``path_template``, and
  ``status_code_family``. The histogram parts are:
  - ``ctms_requests_duration_seconds_sum`` - the running total of durations.
  - ``ctms_requests_duration_seconds_bucket`` - the histogram buckets, adding
    the tag ``le``.
  - ``ctms_requests_duration_seconds_count`` - the count of requests.
* ``ctms_api_requests_total`` - A counter of API endpoint requests, with the
  labels ``client_id``, ``method``, ``path_template``, and
  ``status_code_family``.
* ``ctms_requests_total`` - A counter of requests, with the labels ``method``,
  ``path_template``, ``status_code``, and ``status_code_family``.

The API metrics labels are:

* ``client_id``: The client_id of the API key used to make the request.
* ``le``: For histograms, the "less than or equal to" value of the bucket,
  such as `"5.0"` for the count of requests less than 5 seconds.
* ``method``: The HTTP method, uppercase, like ``GET`` and ``POST``.
* ``path_template``: The path, such as ``/__version__`` or A standardized path,
  such as ``/ctms/{email_id}``.
* ``status_code_family``: A string like `2xx` and `4xx`, representing the first
  digit of the HTTP status code.
* ``status_code``: The HTTP status code.

### Acoustic Sync Service Metrics

The Acoustic Sync service metrics are:

* ``ctms_background_acoustic_requests_duration_*`` - A
  [histogram](https://prometheus.io/docs/practices/histograms/) of Acoustic
  request timing, with labels ``method``, ``status``, ``table``.
  The histogram parts are:
  - ``ctms_background_acoustic_requests_duration_sum`` - The running total of durations.
  - ``ctms_background_acoustic_requests_duration_bucket`` - The histogram buckets, adding
    the tag ``le``.
  - ``ctms_background_acoustic_requests_duration_count`` - The count of requests.
* ``ctms_background_acoustic_request_total`` - A counter of Acoustic requests,
  with labels ``method``, ``status``, ``table``.
* ``ctms_background_acoustic_sync_total`` - A counter of contacts synced to Acoustic.
* ``ctms_background_acoustic_sync_retries`` - A gauge of pending records that have
  been tried once already. Some have reached maximum retries, so the gauge will
  remain high.
* ``ctms_background_acoustic_sync_backlog`` - A gauge of pending records to sync,
  excluding those that have reached maximum retries.
* ``ctms_background_acoustic_sync_loops`` - A counter that increments with each batch,
  including empty batches.
* ``ctms_background_acoustic_sync_age_s`` - A gauge of the age of the most recently
  synced contact, in seconds rounded to milliseconds. This measures the time from
  requesting a contact sync until it is synced.

The sync service labels are:

* ``method`` - The Acoustic method called, such as ``"add_recipient"`` for the
  main contact table, or TKTK
* ``status`` - The Acoustic request result, ``"success"`` or ``"failure"``.
* ``table`` - The Acoustic database table updated, ``"main"``,
  ``"newsletter"``, or ``"product"``.
* ``le`` - The histogram bucket, such as ``"1.0"`` for requests taking a second
  or less.

There are additional shared labels for all sync service metrics:

* ``app_kubernetes_io_component`` - set to ``"background"``
* ``app_kubernetes_io_instance`` - set to ``"ctms"``
* ``app_kubernetes_io_name`` - set to ``"ctms"``

## Dashboards

CTMS metrics are presented on two dashboards:

* [CTMS - dashboard](https://earthangel-b40313e5.influxcloud.net/d/UFbHzGCMz/ctms-dashboard?orgId=1):
  Operational metrics for production and staging.
* [CTMS Alerts](https://earthangel-b40313e5.influxcloud.net/d/UqluYyc7k/ctms-alerts?orgId=1):
  Operational metrics with triggers to alert on-call staff.

## Docker
See the [developer_setup_guide](developer_setup.md#docker) for more information about Docker.

## SRE Related Doc
See the [SRE mana page](https://mana.mozilla.org/wiki/pages/viewpage.action?spaceKey=SRE&title=ESS+-+CTMS) for more information and additional technical diagrams for deployment.

---
[View All Docs](./)
