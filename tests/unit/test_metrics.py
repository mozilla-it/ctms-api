# Test for metrics
from unittest import mock

import pytest
from prometheus_client import CollectorRegistry, generate_latest
from prometheus_client.parser import text_string_to_metric_families

from ctms import metrics as metrics_module
from ctms.app import app

# Metric cardinatility numbers
# These numbers change as routes are added or changed
# Higher numbers = more ways to slice data, more storage, more processing time for summaries

# Cardinality of ctms_requests_total counter
METHOD_PATH_CODE_COMBINATIONS = 50

# Cardinality of ctms_requests_duration_seconds histogram
METHOD_PATH_CODEFAM_COMBOS = 35
DURATION_BUCKETS = 8
DURATION_COMBINATIONS = METHOD_PATH_CODEFAM_COMBOS * (DURATION_BUCKETS + 2)

# Base cardinatility of ctms_api_requests_total
# Actual is multiplied by the number of API clients
METHOD_API_PATH_COMBINATIONS = 18


def test_init_metrics_labels(dbsession, client_id_and_secret, registry, metrics):
    """Test that init_metric_labels populates variants"""
    metrics_module.init_metrics_labels(dbsession, app, metrics)

    metrics_text = generate_latest(registry).decode()
    families = list(text_string_to_metric_families(metrics_text))
    metrics_by_name = {
        "ctms_requests": None,
        "ctms_requests_created": None,
        "ctms_requests_duration_seconds": None,
        "ctms_requests_duration_seconds_created": None,
        "ctms_api_requests": None,
        "ctms_api_requests_created": None,
    }
    for metric in families:
        if metric.name in metrics_by_name:
            metrics_by_name[metric.name] = metric
    not_found = [name for name, metric in metrics_by_name.items() if metric is None]
    assert not_found == []

    def get_labels(metric_name, label_names):
        labels = []
        for sample in metrics_by_name[metric_name].samples:
            sample_label = sample[1]
            label = tuple(sample_label[name] for name in label_names)
            labels.append(label)
        return sorted(labels)

    # ctms_requests has a metric for every method / path / status code combo
    req_label_names = ("method", "path_template", "status_code")
    req_labels = get_labels("ctms_requests", req_label_names)
    reqc_labels = get_labels("ctms_requests_created", req_label_names)
    assert len(req_labels) == METHOD_PATH_CODE_COMBINATIONS
    assert req_labels == reqc_labels
    assert ("GET", "/", "307") in req_labels
    assert ("GET", "/openapi.json", "200") in req_labels
    assert ("GET", "/ctms/{email_id}", "200") in req_labels
    assert ("GET", "/ctms/{email_id}", "401") in req_labels
    assert ("GET", "/ctms/{email_id}", "404") in req_labels
    assert ("GET", "/ctms/{email_id}", "422") in req_labels
    assert ("GET", "/ctms/{email_id}", "422") in req_labels
    assert ("PATCH", "/ctms/{email_id}", "200") in req_labels
    assert ("PUT", "/ctms/{email_id}", "200") in req_labels

    # ctms_requests_duration_seconds has a metric for each
    # method / path / status code family combo
    dur_label_names = ("method", "path_template", "status_code_family")
    dur_labels = get_labels("ctms_requests_duration_seconds", dur_label_names)
    assert len(dur_labels) == DURATION_COMBINATIONS
    assert ("GET", "/", "3xx") in dur_labels

    # ctms_api_requests has a metric for each
    # (method / path / client_id / status code family) combo for API paths
    # where API paths are those requiring authentication
    api_label_names = ("method", "path_template", "client_id", "status_code_family")
    api_labels = get_labels("ctms_api_requests", api_label_names)
    apic_labels = get_labels("ctms_api_requests_created", api_label_names)
    assert len(api_labels) == METHOD_API_PATH_COMBINATIONS
    assert api_labels == apic_labels
    client_id, _ = client_id_and_secret
    assert ("GET", "/ctms/{email_id}", client_id, "2xx") in api_labels
    assert ("GET", "/ctms/{email_id}", client_id, "4xx") in api_labels


def assert_request_metric_inc(
    metrics_registry: CollectorRegistry,
    method: str,
    path_template: str,
    status_code: int,
    count: int = 1,
):
    """Assert ctms_requests_total with given labels was incremented"""
    labels = {
        "method": method,
        "path_template": path_template,
        "status_code": str(status_code),
        "status_code_family": str(status_code)[0] + "xx",
    }
    assert metrics_registry.get_sample_value("ctms_requests_total", labels) == count


def assert_duration_metric_obs(
    metrics_registry: CollectorRegistry,
    method: str,
    path_template: str,
    status_code_family: str,
    limit: float = 0.1,
    count: int = 1,
):
    """Assert ctms_requests_duration_seconds with given labels was observed"""
    base_name = "ctms_requests_duration_seconds"
    labels = {
        "method": method,
        "path_template": path_template,
        "status_code_family": status_code_family,
    }
    bucket_labels = labels.copy()
    bucket_labels["le"] = str(limit)
    assert (
        metrics_registry.get_sample_value(f"{base_name}_bucket", bucket_labels) == count
    )
    assert metrics_registry.get_sample_value(f"{base_name}_count", labels) == count
    assert metrics_registry.get_sample_value(f"{base_name}_sum", labels) < limit


def assert_api_request_metric_inc(
    metrics_registry: CollectorRegistry,
    method: str,
    path_template: str,
    client_id: str,
    status_code_family: str,
    count: int = 1,
):
    """Assert ctms_api_requests_total with given labels was incremented"""
    labels = {
        "method": method,
        "path_template": path_template,
        "client_id": client_id,
        "status_code_family": status_code_family,
    }
    assert metrics_registry.get_sample_value("ctms_api_requests_total", labels) == count


def test_homepage_request(anon_client, registry):
    """A homepage request emits metrics for / and /docs"""
    anon_client.get("/")
    assert_request_metric_inc(registry, "GET", "/", 307)
    assert_request_metric_inc(registry, "GET", "/docs", 200)
    assert_duration_metric_obs(registry, "GET", "/", "3xx")
    assert_duration_metric_obs(registry, "GET", "/docs", "2xx")


def test_contacts_total(anon_client, dbsession, registry):
    """Total number of contacts is reported in heartbeat."""
    with mock.patch("ctms.routers.platform.count_total_contacts", return_value=3):
        anon_client.get("/__heartbeat__")

    assert registry.get_sample_value("ctms_contacts_total") == 3


def test_api_request(client, dbsession, email_factory, registry):
    """An API request emits API metrics as well."""
    email = email_factory()
    dbsession.commit()

    client.get(f"/ctms/{email.email_id}")
    path = "/ctms/{email_id}"

    assert_request_metric_inc(registry, "GET", path, 200)
    assert_duration_metric_obs(registry, "GET", path, "2xx")
    assert_api_request_metric_inc(registry, "GET", path, "test_client", "2xx")


def test_patch_relay_waitlist_legacy_reports_metric(
    client, dbsession, email_factory, registry
):
    email = email_factory()
    dbsession.commit()

    patch_data = {"waitlists": [{"name": "relay", "fields": {"geo": "fr"}}]}
    resp = client.patch(
        f"/ctms/{email.email_id}", json=patch_data, allow_redirects=True
    )
    assert resp.status_code == 200
    assert registry.get_sample_value("ctms_legacy_waitlists_requests_total") == 0

    # Legacy metric isn't sent if `waitlists` is present.
    patch_data = {
        "relay_waitlist": {"geo": "fr"},
        "waitlists": [{"name": "relay", "fields": {"geo": "fr"}}],
    }
    resp = client.patch(
        f"/ctms/{email.email_id}", json=patch_data, allow_redirects=True
    )
    assert resp.status_code == 200
    assert registry.get_sample_value("ctms_legacy_waitlists_requests_total") == 0

    # Metric is sent only if legacy attributes are sent.
    patch_data = {"relay_waitlist": {"geo": "fr"}}
    resp = client.patch(
        f"/ctms/{email.email_id}", json=patch_data, allow_redirects=True
    )
    assert resp.status_code == 200
    assert registry.get_sample_value("ctms_legacy_waitlists_requests_total") == 1


@pytest.mark.parametrize(
    "email_id,status_code",
    (
        ("07259262-7902-489c-ad65-473336635a3b", 404),
        ("an-invalid-id", 422),
    ),
)
def test_bad_api_request(client, dbsession, registry, email_id, status_code):
    """An API request that returns a 404 emits metrics."""
    resp = client.get(f"/ctms/{email_id}")
    assert resp.status_code == status_code
    path = "/ctms/{email_id}"
    assert_request_metric_inc(registry, "GET", path, status_code)
    status_code_family = str(status_code)[0] + "xx"
    assert_api_request_metric_inc(
        registry, "GET", path, "test_client", status_code_family
    )


def test_crash_request(client, dbsession, registry):
    """An exception-raising API request emits metric with 500s."""
    path = "/__crash__"
    with pytest.raises(RuntimeError):
        client.get(path)
    assert_request_metric_inc(registry, "GET", path, 500)
    assert_api_request_metric_inc(registry, "GET", path, "test_client", "5xx")


def test_unknown_path(anon_client, registry):
    """A unknown path does not emit metrics with labels."""
    path = "/unknown"
    resp = anon_client.get(path)
    assert resp.status_code == 404

    without_labels = []
    for name, (_, params) in metrics_module.METRICS_PARAMS.items():
        if "labelnames" not in params:
            without_labels.append(f"ctms_{name}_total")
            without_labels.append(f"ctms_{name}_created")

    metrics_text = generate_latest(registry).decode()
    for family in text_string_to_metric_families(metrics_text):
        if len(family.samples) == 1:
            # This metric is emitted, maybe because there are no labels
            sample = family.samples[0]
            assert sample.name in without_labels
            assert sample.labels == {}
        else:
            assert len(family.samples) == 0
