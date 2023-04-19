from prometheus_client import CollectorRegistry, Counter, Gauge, push_to_gateway
from prometheus_client.metrics import Histogram
from prometheus_client.utils import INF


class BackgroundMetricService:  # pylint: disable=too-many-instance-attributes
    def __init__(
        self,
        registry: CollectorRegistry,
        pushgateway_url: str,
        metric_prefix="ctms_background_",
    ):
        self.registry = registry
        self.app_kubernetes_io_component = "background"
        self.app_kubernetes_io_instance = "ctms"
        self.app_kubernetes_io_name = "ctms"

        self.requests = Counter(
            registry=registry,
            name=metric_prefix + "acoustic_request_total",
            documentation="Total count of acoustic requests by method, and status.",
            labelnames=[
                "method",
                "status",
                "table",
                "app_kubernetes_io_component",
                "app_kubernetes_io_instance",
                "app_kubernetes_io_name",
            ],
        )

        self.requests_duration = Histogram(
            registry=registry,
            name=metric_prefix + "acoustic_requests_duration",
            documentation="Histogram of requests processing time by method (in seconds)",
            labelnames=[
                "method",
                "status",
                "table",
                "app_kubernetes_io_component",
                "app_kubernetes_io_instance",
                "app_kubernetes_io_name",
            ],
            buckets=(0.01, 0.05, 0.1, 0.5, 1, 5, 10, INF),
        )
        self.sync_requests = Counter(
            registry=registry,
            name=metric_prefix + "acoustic_sync_total",
            labelnames=[
                "app_kubernetes_io_component",
                "app_kubernetes_io_instance",
                "app_kubernetes_io_name",
            ],
            documentation="Total count of contacts synced to acoustic.",
        )

        self.retry_gauge = Gauge(
            registry=registry,
            name=metric_prefix + "acoustic_sync_retries",
            labelnames=[
                "app_kubernetes_io_component",
                "app_kubernetes_io_instance",
                "app_kubernetes_io_name",
            ],
            documentation="Gauge of pending records with >0 retries to acoustic.",
        )

        self.backlog_gauge = Gauge(
            registry=registry,
            name=metric_prefix + "acoustic_sync_backlog",
            labelnames=[
                "app_kubernetes_io_component",
                "app_kubernetes_io_instance",
                "app_kubernetes_io_name",
            ],
            documentation="Gauge of the number of contacts in the sync backlog. Not counting over-retried records.",
        )

        self.loop = Counter(
            registry=registry,
            name=metric_prefix + "acoustic_sync_loops",
            labelnames=[
                "app_kubernetes_io_component",
                "app_kubernetes_io_instance",
                "app_kubernetes_io_name",
            ],
            documentation="Total count of loops of the background process.",
        )

        self.age_gauge = Gauge(
            registry=registry,
            name=metric_prefix + "acoustic_sync_age_s",
            labelnames=[
                "app_kubernetes_io_component",
                "app_kubernetes_io_instance",
                "app_kubernetes_io_name",
            ],
            documentation="Age of the most recent synced, non-retry record in seconds.",
        )

        self.pushgateway_url = pushgateway_url
        self.job_name = "prometheus-pushgateway"

        self.sync_loop_duration_seconds = Gauge(
            name=metric_prefix + "acoustic_sync_loop_duration_seconds",
            documentation="Acoustic sync loop duration in seconds.",
            labelnames=[
                "app_kubernetes_io_component",
                "app_kubernetes_io_instance",
                "app_kubernetes_io_name",
            ],
            registry=registry,
        )

        self.token_rotation_gauge = Gauge(
            name=metric_prefix + "token_rotation_gauge",
            documentation="Gauge of the number of contacts to be updated.",
            labelnames=[
                "app_kubernetes_io_component",
                "app_kubernetes_io_instance",
                "app_kubernetes_io_name",
            ],
            registry=registry,
        )

    def inc_acoustic_request_total(self, method, status, table):
        self.requests.labels(
            method=method,
            status=status,
            table=table,
            app_kubernetes_io_component=self.app_kubernetes_io_component,
            app_kubernetes_io_instance=self.app_kubernetes_io_instance,
            app_kubernetes_io_name=self.app_kubernetes_io_name,
        ).inc()

    def observe_acoustic_request_duration(self, method, status, table, duration_s):
        self.requests_duration.labels(
            method=method,
            status=status,
            table=table,
            app_kubernetes_io_component=self.app_kubernetes_io_component,
            app_kubernetes_io_instance=self.app_kubernetes_io_instance,
            app_kubernetes_io_name=self.app_kubernetes_io_name,
        ).observe(duration_s)

    def inc_acoustic_sync_total(self):
        self.sync_requests.labels(
            app_kubernetes_io_component=self.app_kubernetes_io_component,
            app_kubernetes_io_instance=self.app_kubernetes_io_instance,
            app_kubernetes_io_name=self.app_kubernetes_io_name,
        ).inc()

    def gauge_acoustic_sync_backlog(self, value):
        self.backlog_gauge.labels(
            app_kubernetes_io_component=self.app_kubernetes_io_component,
            app_kubernetes_io_instance=self.app_kubernetes_io_instance,
            app_kubernetes_io_name=self.app_kubernetes_io_name,
        ).set(value)

    def gauge_acoustic_retry_backlog(self, value):
        self.retry_gauge.labels(
            app_kubernetes_io_component=self.app_kubernetes_io_component,
            app_kubernetes_io_instance=self.app_kubernetes_io_instance,
            app_kubernetes_io_name=self.app_kubernetes_io_name,
        ).set(value)

    def inc_acoustic_sync_loop(self):
        self.loop.labels(
            app_kubernetes_io_component=self.app_kubernetes_io_component,
            app_kubernetes_io_instance=self.app_kubernetes_io_instance,
            app_kubernetes_io_name=self.app_kubernetes_io_name,
        ).inc()

    def gauge_acoustic_record_age(self, age_s):
        self.age_gauge.labels(
            app_kubernetes_io_component=self.app_kubernetes_io_component,
            app_kubernetes_io_instance=self.app_kubernetes_io_instance,
            app_kubernetes_io_name=self.app_kubernetes_io_name,
        ).set(age_s)

    def push_to_gateway(self):
        push_to_gateway(self.pushgateway_url, job=self.job_name, registry=self.registry)

    def set_sync_loop_duration_seconds(self, duration_seconds):
        self.sync_loop_duration_seconds.labels(
            app_kubernetes_io_component=self.app_kubernetes_io_component,
            app_kubernetes_io_instance=self.app_kubernetes_io_instance,
            app_kubernetes_io_name=self.app_kubernetes_io_name,
        ).set(duration_seconds)

    def gauge_token_rotation(self, value):
        self.token_rotation_gauge.labels(
            app_kubernetes_io_component=self.app_kubernetes_io_component,
            app_kubernetes_io_instance=self.app_kubernetes_io_instance,
            app_kubernetes_io_name=self.app_kubernetes_io_name,
        ).set(value)
