import logging

from prometheus_client import CollectorRegistry, Counter, Gauge, push_to_gateway
from prometheus_client.metrics import Histogram
from prometheus_client.utils import INF


class BackgroundMetricService:  # pylint: disable=too-many-instance-attributes
    def __init__(self, registry: CollectorRegistry, pushgateway_url: str):
        self.logger = logging.getLogger(__name__)
        self.registry = registry
        self.requests = Counter(
            registry=registry,
            name="acoustic_request_total",
            documentation="Total count of acoustic requests by method, and status.",
            labelnames=[
                "method",
                "status",
                "app_kubernetes_io_component",
                "app_kubernetes_io_instance",
                "app_kubernetes_io_name",
            ],
        )
        self.app_kubernetes_io_component = "web"
        self.app_kubernetes_io_instance = "ctms"
        self.app_kubernetes_io_name = "ctms"

        self.requests_duration = Histogram(
            registry=registry,
            name="acoustic_requests_duration",
            documentation="Histogram of requests processing time by method (in seconds)",
            labelnames=[
                "method",
                "status",
                "app_kubernetes_io_component",
                "app_kubernetes_io_instance",
                "app_kubernetes_io_name",
            ],
            buckets=(0.01, 0.05, 0.1, 0.5, 1, 5, 10, INF),
        )
        self.sync_requests = Counter(
            registry=registry,
            name="acoustic_sync_total",
            labelnames=[
                "app_kubernetes_io_component",
                "app_kubernetes_io_instance",
                "app_kubernetes_io_name",
            ],
            documentation="Total count of contacts synced to acoustic.",
        )
        self.backlog_gauge = Gauge(
            registry=registry,
            name="acoustic_sync_backlog",
            labelnames=[
                "app_kubernetes_io_component",
                "app_kubernetes_io_instance",
                "app_kubernetes_io_name",
            ],
            documentation="Gauge of the number of contacts in the sync backlog. Not counting over-retried records.",
        )
        self.pushgateway_url = pushgateway_url
        self.job_name = "prometheus-pushgateway"

    def inc_acoustic_request_total(self, method, status):
        self.requests.labels(
            method=method,
            status=status,
            app_kubernetes_io_component=self.app_kubernetes_io_component,
            app_kubernetes_io_instance=self.app_kubernetes_io_instance,
            app_kubernetes_io_name=self.app_kubernetes_io_name,
        ).inc()
        self.logger.debug("Incrementing acoustic request")

    def observe_acoustic_request_duration(self, method, status, duration_s):
        self.requests_duration.labels(
            method=method,
            status=status,
            app_kubernetes_io_component=self.app_kubernetes_io_component,
            app_kubernetes_io_instance=self.app_kubernetes_io_instance,
            app_kubernetes_io_name=self.app_kubernetes_io_name,
        ).observe(duration_s)
        self.logger.debug("Observing acoustic request duration")

    def inc_acoustic_sync_total(self):
        self.sync_requests.labels(
            app_kubernetes_io_component=self.app_kubernetes_io_component,
            app_kubernetes_io_instance=self.app_kubernetes_io_instance,
            app_kubernetes_io_name=self.app_kubernetes_io_name,
        ).inc()
        self.logger.debug("Incrementing sync'd records")

    def gauge_acoustic_sync_backlog(self, value):
        self.backlog_gauge.labels(
            app_kubernetes_io_component=self.app_kubernetes_io_component,
            app_kubernetes_io_instance=self.app_kubernetes_io_instance,
            app_kubernetes_io_name=self.app_kubernetes_io_name,
        ).set(value)
        self.logger.debug("Setting backlog gauge")

    def push_to_gateway(self):
        push_to_gateway(self.pushgateway_url, job=self.job_name, registry=self.registry)
        self.logger.debug("Pushing metrics to pushgateway")
