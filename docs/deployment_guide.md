# Deployment Guide

## Overview

There are two deployed instances of CTMS:

* https://ctms.prod.mozilla-ess.mozit.cloud/ - The production instance, deployed on version tags
* https://ctms.stage.mozilla-ess.mozit.cloud/ - The staging instance, deployed on pull-requests merges

## Deployment

The deployment code lives in https://github.com/mozilla-sre-deploy/deploy-ctms (*private*).

See the [SRE mana page](https://mana.mozilla.org/wiki/pages/viewpage.action?spaceKey=SRE&title=ESS+-+CTMS) for more information and additional technical diagrams for deployment.

## Common Operations

### Delete Contacts in Bulk

In order to delete all information about certain contacts, use the `delete_bulk.py` script.


### Validate Waitlist Extra Fields

Waitlist subscriptions can receive arbitrary fields. By default, only ``geo`` and ``platform`` are validated (eg. max length).

In order to validate a new waitlist field, the [CTMS codebase has to modified](https://github.com/mozilla-it/ctms-api/blob/ec34e7ca56fe802f78c8b65e01448e134e29b938/ctms/schemas/waitlist.py#L130).


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

## Metrics

[Prometheus](https://prometheus.io/) is used for publishing metrics for the API
and the backend service. These are exported to [InfluxDB](https://www.influxdata.com/)
for further processing and display on dashboards.

The API metrics are fetched from ``/metrics``, and each API instance publishes
and keeps track of its own metrics. This means the same counter should be "summed"
across instances to get a deployment-wide counter. It also means that counters
reset when instances reset, such as during a deployment.

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

### Dashboards

CTMS metrics are presented on two dashboards:

* [CTMS Telemetry](https://earthangel-b40313e5.influxcloud.net/d/UFbHzGCMz/ctms-dashboard?orgId=1):
  Operational metrics for production and staging.
* [CTMS Alerts](https://earthangel-b40313e5.influxcloud.net/d/UqluYyc7k/ctms-alerts?orgId=1):
  Operational metrics with triggers to alert on-call staff.

---
[View All Docs](./)
