import os

from opentelemetry import metrics, trace
from opentelemetry.exporter.otlp.proto.http.trace_exporter import OTLPSpanExporter
from opentelemetry.exporter.prometheus import PrometheusMetricReader
from opentelemetry.instrumentation.fastapi import FastAPIInstrumentor
from opentelemetry.sdk.metrics import MeterProvider
from opentelemetry.sdk.resources import SERVICE_NAME, Resource
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor


def init_otel(app=None, service_name: str = "hookcli-mcp"):
    env = os.getenv("DEPLOY_ENV", "dev")
    otlp_endpoint = os.getenv("OTEL_EXPORTER_OTLP_ENDPOINT", "http://localhost:4318")

    resource = Resource.create(
        {
            SERVICE_NAME: service_name,
            "deployment.environment": env,
            "service.version": "0.1.0",
        }
    )

    trace_provider = TracerProvider(resource=resource)
    trace_provider.add_span_processor(BatchSpanProcessor(OTLPSpanExporter(endpoint=otlp_endpoint)))
    trace.set_tracer_provider(trace_provider)

    prom_reader = PrometheusMetricReader()
    meter_provider = MeterProvider(resource=resource, metric_readers=[prom_reader])
    metrics.set_meter_provider(meter_provider)

    if app is not None:
        FastAPIInstrumentor.instrument_app(app, tracer_provider=trace_provider)

    return trace.get_tracer(service_name)
