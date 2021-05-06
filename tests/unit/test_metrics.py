# Test for metrics
from unittest.mock import patch

import pytest
from prometheus_client import REGISTRY, CollectorRegistry, generate_latest
from prometheus_client.parser import text_string_to_metric_families

from ctms.app import app
from ctms.metrics import init_metrics, init_metrics_labels, init_metrics_registry

# Metric cardinatility numbers
# These numbers change as routes are added or changed
# Higher numbers = more ways to slice data, more storage, more processing time for summaries

# Cardinality of ctms_requests_total counter
METHOD_PATH_CODE_COMBINATIONS = 45

# Cardinality of ctms_requests_duration_seconds histogram
METHOD_PATH_COMBOS = 23
DURATION_BUCKETS = 8
DURATION_COMBINATIONS = METHOD_PATH_COMBOS * (DURATION_BUCKETS + 2)

# Base cardinatility of ctms_api_requests_total
# Actual is multiplied by the number of API clients
METHOD_API_PATH_COMBINATIONS = 16


@pytest.fixture
def setup_metrics():
    """Setup a metrics registry and metrics, use them in the app"""

    test_registry = CollectorRegistry()
    test_metrics = init_metrics(test_registry)
    # Because these methods are called from a middleware
    # we can't use dependency injection like with get_db
    with patch("ctms.app.get_metrics_registry", return_value=test_registry), patch(
        "ctms.app.get_metrics", return_value=test_metrics
    ):
        yield test_registry, test_metrics


@pytest.fixture
def registry(setup_metrics):
    """Get the test metrics registry"""
    test_registry, _ = setup_metrics
    return test_registry


@pytest.fixture
def metrics(setup_metrics):
    """Get the test metrics"""
    _, test_metrics = setup_metrics
    return test_metrics


def test_init_metrics_registry():
    """init_metrics_registry() returns a registry."""
    the_registry = init_metrics_registry()
    assert the_registry != REGISTRY


def test_init_metrics_labels(dbsession, client_id_and_secret, registry, metrics):
    """Test that init_metric_labels populates variants"""
    init_metrics_labels(dbsession, app, metrics)

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

    # ctms_requests_duration_seconds has a metric for each method / path combo
    method_path = set((method, path) for method, path, _ in req_labels)
    assert len(method_path) == METHOD_PATH_COMBOS
    dur_label_names = ("method", "path_template")
    dur_labels = get_labels("ctms_requests_duration_seconds", dur_label_names)
    assert len(dur_labels) == DURATION_COMBINATIONS

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


def test_homepage_request(anon_client, registry):
    """A homepage request emits metrics for / and /docs"""
    anon_client.get("/")
    assert (
        registry.get_sample_value(
            "ctms_requests_total",
            {"method": "GET", "path_template": "/", "status_code": "307"},
        )
        == 1
    )
    assert (
        registry.get_sample_value(
            "ctms_requests_total",
            {"method": "GET", "path_template": "/docs", "status_code": "200"},
        )
        == 1
    )
    assert (
        registry.get_sample_value(
            "ctms_requests_duration_seconds_bucket",
            {"method": "GET", "path_template": "/", "le": "0.1"},
        )
        == 1
    )
    assert (
        registry.get_sample_value(
            "ctms_requests_duration_seconds_count",
            {"method": "GET", "path_template": "/"},
        )
        == 1
    )
    assert (
        registry.get_sample_value(
            "ctms_requests_duration_seconds_sum",
            {"method": "GET", "path_template": "/"},
        )
        < 0.1
    )


def test_api_request(client, minimal_contact, registry):
    """An API request emits API metrics as well."""
    email_id = minimal_contact.email.email_id
    client.get(f"/ctms/{email_id}")
    path = "/ctms/{email_id}"
    assert (
        registry.get_sample_value(
            "ctms_requests_total",
            {"method": "GET", "path_template": path, "status_code": "200"},
        )
        == 1
    )
    assert (
        registry.get_sample_value(
            "ctms_requests_duration_seconds_bucket",
            {"method": "GET", "path_template": path, "le": "0.1"},
        )
        == 1
    )
    assert (
        registry.get_sample_value(
            "ctms_requests_duration_seconds_count",
            {"method": "GET", "path_template": path},
        )
        == 1
    )
    assert (
        registry.get_sample_value(
            "ctms_requests_duration_seconds_sum",
            {"method": "GET", "path_template": path},
        )
        < 0.1
    )
    assert (
        registry.get_sample_value(
            "ctms_api_requests_total",
            {
                "method": "GET",
                "path_template": path,
                "client_id": "test_client",
                "status_code_family": "2xx",
            },
        )
        == 1
    )


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
    assert (
        registry.get_sample_value(
            "ctms_requests_total",
            {"method": "GET", "path_template": path, "status_code": str(status_code)},
        )
        == 1
    )
    assert (
        registry.get_sample_value(
            "ctms_api_requests_total",
            {
                "method": "GET",
                "path_template": path,
                "client_id": "test_client",
                "status_code_family": str(status_code)[0] + "xx",
            },
        )
        == 1
    )


def test_crash_request(client, dbsession, registry):
    """An exception-raising API request emits metric with 500s."""
    path = "/__crash__"
    with pytest.raises(RuntimeError):
        client.get(path)
    assert (
        registry.get_sample_value(
            "ctms_requests_total",
            {"method": "GET", "path_template": path, "status_code": "500"},
        )
        == 1
    )
    assert (
        registry.get_sample_value(
            "ctms_api_requests_total",
            {
                "method": "GET",
                "path_template": path,
                "client_id": "test_client",
                "status_code_family": "5xx",
            },
        )
        == 1
    )


def test_unknown_path(anon_client, dbsession, registry):
    """A unknown path does not emit metrics."""
    path = "/unknown"
    resp = anon_client.get(path)
    assert resp.status_code == 404
    metrics_text = generate_latest(registry).decode()
    for family in text_string_to_metric_families(metrics_text):
        assert len(family.samples) == 0
