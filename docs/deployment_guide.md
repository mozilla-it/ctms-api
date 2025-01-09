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

Set ``CTMS_USE_MOZLOG`` to ``false`` to disable the [MozLog JSON format](https://wiki.mozilla.org/Firefox/Services/Logging) used for logging.

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
