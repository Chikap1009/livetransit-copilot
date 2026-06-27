"""Langfuse tracing for the agent via OpenTelemetry (Phase H).

Pydantic AI emits standard OpenTelemetry spans for every model call, tool call, and
retrieval; Langfuse ingests OTel. We point an OTLP exporter at Langfuse's endpoint and
enable Pydantic AI instrumentation. No-op (returns False) if the LANGFUSE keys are absent,
so the app runs fine without tracing configured.
"""
import base64
import os


def configure_tracing() -> bool:
    """Wire Pydantic AI's OTel spans to Langfuse. Returns True if enabled."""
    public = os.environ.get("LANGFUSE_PUBLIC_KEY")
    secret = os.environ.get("LANGFUSE_SECRET_KEY")
    if not (public and secret):
        return False

    base_url = os.environ.get("LANGFUSE_BASE_URL", "https://cloud.langfuse.com").rstrip("/")
    auth = base64.b64encode(f"{public}:{secret}".encode()).decode()
    # Standard OTLP env the logfire/OTel SDK reads.
    os.environ.setdefault("OTEL_EXPORTER_OTLP_ENDPOINT", f"{base_url}/api/public/otel")
    os.environ.setdefault("OTEL_EXPORTER_OTLP_HEADERS", f"Authorization=Basic {auth}")

    import logfire

    # send_to_logfire=False -> spans go only to the OTLP endpoint (Langfuse), not Logfire cloud.
    logfire.configure(service_name="livetransit-copilot", send_to_logfire=False)
    logfire.instrument_pydantic_ai()
    return True
