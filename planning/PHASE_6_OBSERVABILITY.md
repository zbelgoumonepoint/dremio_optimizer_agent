# Phase 6: Observability & Monitoring

**Duration**: 1 week
**Status**: Planned
**Dependencies**: Phase 5 (REST API must be operational)

## Overview

Implement comprehensive observability using OpenTelemetry for distributed tracing, Loguru with Loki for structured logging, and Prometheus for metrics. This provides complete visibility into system behavior, performance bottlenecks, and operational health.

### Goals

1. Implement distributed tracing with OpenTelemetry + Tempo
2. Set up structured logging with Loguru + Loki
3. Add Prometheus metrics for key performance indicators
4. Create Grafana dashboards for visualization
5. Implement alerting for critical conditions
6. Add custom spans for AI agent reasoning

### Key Deliverables

- OpenTelemetry instrumentation for all components
- Loki integration for centralized logging
- Prometheus metrics exporters
- Grafana dashboards (3+)
- Alert rules for critical metrics
- Observability documentation

---

## Architecture

```
Application → OpenTelemetry → Tempo (Traces)
           → Loguru → Loki (Logs)
           → Prometheus → Grafana (Metrics + Dashboards)
                            ↓
                         Alerts
```

---

## Component 1: OpenTelemetry Tracing

### File: `src/observability/tracing.py`

```python
from opentelemetry import trace
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor
from opentelemetry.exporter.otlp.proto.grpc.trace_exporter import OTLPSpanExporter
from opentelemetry.sdk.resources import Resource
from opentelemetry.instrumentation.fastapi import FastAPIInstrumentor
from opentelemetry.instrumentation.sqlalchemy import SQLAlchemyInstrumentor
from opentelemetry.instrumentation.requests import RequestsInstrumentor
from src.config.settings import get_settings

settings = get_settings()

# Global tracer
tracer = trace.get_tracer(__name__)


def setup_tracing():
    """
    Initialize OpenTelemetry tracing with OTLP exporter to Tempo.

    Instruments:
    - FastAPI (HTTP requests)
    - SQLAlchemy (database queries)
    - Requests (HTTP client calls to Dremio)
    """
    # Create resource with service information
    resource = Resource.create({
        "service.name": "dremio-optimizer-agent",
        "service.version": "1.0.0",
        "deployment.environment": settings.environment
    })

    # Create tracer provider
    provider = TracerProvider(resource=resource)

    # Configure OTLP exporter to Tempo
    otlp_exporter = OTLPSpanExporter(
        endpoint=settings.tempo_endpoint,  # e.g., "http://tempo:4317"
        insecure=True  # Use TLS in production
    )

    # Add span processor
    provider.add_span_processor(BatchSpanProcessor(otlp_exporter))

    # Set global tracer provider
    trace.set_tracer_provider(provider)

    # Instrument libraries
    FastAPIInstrumentor.instrument()
    SQLAlchemyInstrumentor().instrument(engine=get_engine())
    RequestsInstrumentor().instrument()

    print("✅ OpenTelemetry tracing initialized")


def get_engine():
    """Get SQLAlchemy engine for instrumentation."""
    from src.database.connection import engine
    return engine


# Decorator for custom spans
def traced(span_name: str):
    """
    Decorator to add custom tracing to functions.

    Usage:
        @traced("my_function")
        def my_function():
            pass
    """
    def decorator(func):
        def wrapper(*args, **kwargs):
            with tracer.start_as_current_span(span_name) as span:
                # Add function parameters as attributes
                span.set_attribute("function.name", func.__name__)
                for key, value in kwargs.items():
                    if isinstance(value, (str, int, float, bool)):
                        span.set_attribute(f"arg.{key}", value)

                try:
                    result = func(*args, **kwargs)
                    span.set_attribute("status", "success")
                    return result
                except Exception as e:
                    span.set_attribute("status", "error")
                    span.set_attribute("error.type", type(e).__name__)
                    span.set_attribute("error.message", str(e))
                    raise
        return wrapper
    return decorator
```

### Add Tracing to Key Services

**Example: Analysis Service with Custom Spans**

**File**: `src/services/analysis_service.py` (enhance existing)

```python
from src.observability.tracing import tracer

class AnalysisService:
    def analyze_query(self, job_id: str) -> List[Dict[str, Any]]:
        """Analyze query with tracing."""
        with tracer.start_as_current_span("analysis.analyze_query") as span:
            span.set_attribute("job_id", job_id)

            # Fetch data
            with tracer.start_as_current_span("analysis.fetch_data"):
                query = self._fetch_query(job_id)
                profile = self._fetch_profile(job_id)

            # Run detectors
            issues = []
            for detector in self.detectors:
                with tracer.start_as_current_span(f"detector.{detector.issue_type}") as detector_span:
                    detector_span.set_attribute("detector_type", detector.issue_type)

                    result = detector.detect(query, profile, metadata=None)

                    if result.detected:
                        detector_span.set_attribute("issue_detected", True)
                        detector_span.set_attribute("severity", result.severity)
                        issues.append(result.to_dict())

            span.set_attribute("issues_detected", len(issues))
            return issues
```

### Add Tracing to AI Agent

**File**: `src/agents/optimizer_agent.py` (enhance existing)

```python
from src.observability.tracing import tracer

def call_optimizer_node(state: OptimizerState, llm) -> OptimizerState:
    """Invoke LLM with tracing."""
    with tracer.start_as_current_span("agent.call_optimizer") as span:
        span.set_attribute("job_id", state["query_context"]["job_id"])
        span.set_attribute("issues_count", len(state["detected_issues"]))

        # Build messages
        messages = state.get("messages", [])
        if not messages:
            with tracer.start_as_current_span("agent.build_context"):
                messages = _build_initial_messages(state)

        # Call LLM
        with tracer.start_as_current_span("agent.llm_invocation") as llm_span:
            llm_span.set_attribute("model", "gpt-4o")
            llm_span.set_attribute("messages_count", len(messages))

            response = llm.invoke(messages)

            llm_span.set_attribute("has_tool_calls", bool(response.tool_calls))
            llm_span.set_attribute("tool_calls_count", len(response.tool_calls) if response.tool_calls else 0)

        messages.append(response)
        return {**state, "messages": messages}
```

---

## Component 2: Structured Logging with Loki

### File: `src/observability/logging.py`

```python
from loguru import logger
import sys
import requests
import json
from datetime import datetime
from src.config.settings import get_settings

settings = get_settings()


def setup_logging():
    """
    Configure Loguru for structured logging with Loki integration.

    Logs to:
    - Console (development)
    - Loki (production)
    """
    # Remove default logger
    logger.remove()

    # Console handler (always)
    logger.add(
        sys.stdout,
        format="<green>{time:YYYY-MM-DD HH:mm:ss}</green> | <level>{level: <8}</level> | <cyan>{name}</cyan>:<cyan>{function}</cyan>:<cyan>{line}</cyan> - <level>{message}</level>",
        level="INFO" if settings.environment == "production" else "DEBUG",
        colorize=True
    )

    # File handler
    logger.add(
        "logs/optimizer_{time}.log",
        rotation="100 MB",
        retention="30 days",
        level="INFO",
        format="{time:YYYY-MM-DD HH:mm:ss} | {level: <8} | {name}:{function}:{line} - {message}",
    )

    # Loki handler (production only)
    if settings.environment == "production" and settings.loki_endpoint:
        logger.add(
            lambda msg: log_to_loki(msg),
            level="INFO",
            format="{message}"
        )

    logger.info("✅ Logging configured")


def log_to_loki(message: str):
    """
    Send structured log to Loki.

    Loki expects logs in this format:
    {
        "streams": [{
            "stream": {"label": "value"},
            "values": [["timestamp_ns", "log_line"]]
        }]
    }
    """
    try:
        timestamp_ns = str(int(datetime.utcnow().timestamp() * 1e9))

        payload = {
            "streams": [{
                "stream": {
                    "service": "dremio-optimizer-agent",
                    "environment": settings.environment,
                    "level": "info"
                },
                "values": [[timestamp_ns, message]]
            }]
        }

        requests.post(
            f"{settings.loki_endpoint}/loki/api/v1/push",
            json=payload,
            headers={"Content-Type": "application/json"},
            timeout=5
        )
    except Exception as e:
        # Fallback: log to console if Loki fails
        print(f"Failed to send log to Loki: {e}")


# Structured logging helpers
def log_optimization_start(job_id: str):
    """Log optimization start with structured context."""
    logger.info(
        "Optimization started",
        extra={
            "job_id": job_id,
            "event_type": "optimization_start"
        }
    )


def log_optimization_complete(job_id: str, issues_count: int, duration_ms: int):
    """Log optimization completion with metrics."""
    logger.info(
        "Optimization completed",
        extra={
            "job_id": job_id,
            "issues_count": issues_count,
            "duration_ms": duration_ms,
            "event_type": "optimization_complete"
        }
    )


def log_recommendation_generated(job_id: str, recommendation_id: int, issue_type: str, estimated_improvement: float):
    """Log recommendation generation."""
    logger.info(
        "Recommendation generated",
        extra={
            "job_id": job_id,
            "recommendation_id": recommendation_id,
            "issue_type": issue_type,
            "estimated_improvement_pct": estimated_improvement,
            "event_type": "recommendation_generated"
        }
    )


def log_measurement_recorded(recommendation_id: int, improvement_pct: float, meets_expectation: bool):
    """Log measurement recording."""
    logger.info(
        "Measurement recorded",
        extra={
            "recommendation_id": recommendation_id,
            "improvement_pct": improvement_pct,
            "meets_expectation": meets_expectation,
            "event_type": "measurement_recorded"
        }
    )
```

### Use Structured Logging in Services

```python
from src.observability.logging import logger, log_optimization_start, log_optimization_complete

class OptimizationService:
    async def optimize_query(self, job_id: str) -> Dict[str, Any]:
        """Optimize query with structured logging."""
        log_optimization_start(job_id)
        start_time = datetime.utcnow()

        try:
            # ... optimization logic ...
            issues = analysis_service.analyze_query(job_id)
            recommendations = recommendation_service.generate_recommendations(...)

            duration_ms = int((datetime.utcnow() - start_time).total_seconds() * 1000)
            log_optimization_complete(job_id, len(issues), duration_ms)

            return result

        except Exception as e:
            logger.error(
                "Optimization failed",
                job_id=job_id,
                error=str(e),
                error_type=type(e).__name__
            )
            raise
```

---

## Component 3: Prometheus Metrics

### File: `src/observability/metrics.py`

```python
from prometheus_client import Counter, Histogram, Gauge, generate_latest, REGISTRY
from fastapi import APIRouter

# Define metrics
optimization_requests = Counter(
    "optimizer_requests_total",
    "Total optimization requests",
    ["endpoint", "status"]
)

optimization_duration = Histogram(
    "optimizer_duration_seconds",
    "Optimization duration in seconds",
    ["operation"]
)

issues_detected = Counter(
    "issues_detected_total",
    "Total issues detected",
    ["issue_type", "severity"]
)

recommendations_generated = Counter(
    "recommendations_generated_total",
    "Total recommendations generated",
    ["issue_type"]
)

measurements_recorded = Counter(
    "measurements_recorded_total",
    "Total measurements recorded",
    ["meets_expectation"]
)

average_improvement = Gauge(
    "average_improvement_pct",
    "Average improvement percentage"
)

active_optimizations = Gauge(
    "active_optimizations",
    "Number of optimizations currently running"
)

# Metrics endpoint router
router = APIRouter()

@router.get("/metrics")
async def metrics():
    """Prometheus metrics endpoint."""
    return generate_latest(REGISTRY)
```

### Instrument Services with Metrics

```python
from src.observability.metrics import (
    optimization_requests,
    optimization_duration,
    issues_detected,
    active_optimizations
)
import time

class OptimizationService:
    async def optimize_query(self, job_id: str) -> Dict[str, Any]:
        """Optimize query with metrics."""
        active_optimizations.inc()
        start_time = time.time()

        try:
            # ... optimization logic ...
            issues = analysis_service.analyze_query(job_id)

            # Record metrics
            for issue in issues:
                issues_detected.labels(
                    issue_type=issue["issue_type"],
                    severity=issue["severity"]
                ).inc()

            optimization_requests.labels(endpoint="optimize_query", status="success").inc()
            duration = time.time() - start_time
            optimization_duration.labels(operation="full_optimization").observe(duration)

            return result

        except Exception as e:
            optimization_requests.labels(endpoint="optimize_query", status="error").inc()
            raise
        finally:
            active_optimizations.dec()
```

---

## Component 4: Grafana Dashboards

### Dashboard 1: Overview Dashboard

**File**: `grafana/dashboards/overview.json`

Key panels:
- **Optimization Rate**: Requests per minute
- **Success Rate**: Successful vs failed optimizations
- **Average Duration**: P50, P95, P99 response times
- **Issues by Type**: Bar chart of detected issue types
- **Recommendations Generated**: Time series
- **Active Optimizations**: Current count

### Dashboard 2: Performance Dashboard

**File**: `grafana/dashboards/performance.json`

Key panels:
- **Optimization Duration Distribution**: Histogram
- **Database Query Performance**: P95 query duration
- **Dremio API Latency**: External API call duration
- **LLM Invocation Duration**: Agent reasoning time
- **Memory Usage**: Application memory
- **CPU Usage**: Application CPU

### Dashboard 3: Business Metrics Dashboard

**File**: `grafana/dashboards/business_metrics.json`

Key panels:
- **Total Time Saved**: Cumulative time saved (hours)
- **Average Improvement**: Average % improvement
- **Adoption Rate**: Implemented vs rejected recommendations
- **Top Issue Types**: Most common performance issues
- **Success Rate by Issue Type**: Effectiveness of each detector
- **ROI Metrics**: Cost savings calculations

---

## Component 5: Alerting

### Alert Rules

**File**: `prometheus/alerts/optimizer_alerts.yml`

```yaml
groups:
  - name: optimizer_alerts
    interval: 30s
    rules:
      # High error rate
      - alert: HighOptimizationErrorRate
        expr: |
          rate(optimizer_requests_total{status="error"}[5m]) > 0.1
        for: 5m
        labels:
          severity: warning
        annotations:
          summary: "High optimization error rate"
          description: "Error rate is {{ $value }} errors/sec over 5 minutes"

      # Slow optimizations
      - alert: SlowOptimizations
        expr: |
          histogram_quantile(0.95, optimizer_duration_seconds_bucket{operation="full_optimization"}) > 30
        for: 10m
        labels:
          severity: warning
        annotations:
          summary: "Optimizations are slow"
          description: "P95 duration is {{ $value }}s (threshold: 30s)"

      # Database connection issues
      - alert: DatabaseConnectionFailures
        expr: |
          rate(db_connection_errors_total[5m]) > 0
        for: 2m
        labels:
          severity: critical
        annotations:
          summary: "Database connection failures detected"
          description: "Cannot connect to PostgreSQL"

      # Dremio API failures
      - alert: DremioAPIFailures
        expr: |
          rate(dremio_api_errors_total[5m]) > 0.05
        for: 5m
        labels:
          severity: warning
        annotations:
          summary: "High Dremio API error rate"
          description: "Dremio API error rate: {{ $value }} errors/sec"

      # Low recommendation adoption
      - alert: LowRecommendationAdoption
        expr: |
          (
            sum(rate(recommendations_generated_total[24h]))
            /
            sum(rate(measurements_recorded_total[24h]))
          ) < 0.3
        for: 1h
        labels:
          severity: info
        annotations:
          summary: "Low recommendation adoption rate"
          description: "Only {{ $value | humanizePercentage }} of recommendations are measured"

      # Average improvement below threshold
      - alert: LowAverageImprovement
        expr: |
          average_improvement_pct < 20
        for: 6h
        labels:
          severity: warning
        annotations:
          summary: "Average improvement below target"
          description: "Average improvement is {{ $value }}% (target: >20%)"
```

---

## Component 6: Configuration

### Settings Enhancement

**File**: `src/config/settings.py` (add observability settings)

```python
class Settings(BaseSettings):
    # ... existing settings ...

    # Observability
    tempo_endpoint: str = "http://tempo:4317"
    loki_endpoint: str = "http://loki:3100"
    prometheus_port: int = 9090
    environment: str = "development"

    # Tracing
    enable_tracing: bool = True
    trace_sample_rate: float = 1.0  # Sample 100% in dev, 10% in prod

    # Logging
    log_level: str = "INFO"
    log_to_loki: bool = False

    class Config:
        env_prefix = "OPTIMIZER_"
```

---

## Component 7: Docker Compose for Observability Stack

### File: `docker-compose.observability.yml`

```yaml
version: '3.8'

services:
  # Tempo (Tracing)
  tempo:
    image: grafana/tempo:latest
    command: ["-config.file=/etc/tempo.yaml"]
    volumes:
      - ./tempo/tempo.yaml:/etc/tempo.yaml
      - tempo-data:/tmp/tempo
    ports:
      - "4317:4317"  # OTLP gRPC
      - "3200:3200"  # Tempo HTTP

  # Loki (Logging)
  loki:
    image: grafana/loki:latest
    command: -config.file=/etc/loki/local-config.yaml
    volumes:
      - loki-data:/loki
    ports:
      - "3100:3100"

  # Prometheus (Metrics)
  prometheus:
    image: prom/prometheus:latest
    command:
      - '--config.file=/etc/prometheus/prometheus.yml'
      - '--storage.tsdb.path=/prometheus'
    volumes:
      - ./prometheus/prometheus.yml:/etc/prometheus/prometheus.yml
      - ./prometheus/alerts:/etc/prometheus/alerts
      - prometheus-data:/prometheus
    ports:
      - "9090:9090"

  # Grafana (Visualization)
  grafana:
    image: grafana/grafana:latest
    environment:
      - GF_SECURITY_ADMIN_PASSWORD=admin
      - GF_AUTH_ANONYMOUS_ENABLED=true
    volumes:
      - ./grafana/datasources:/etc/grafana/provisioning/datasources
      - ./grafana/dashboards:/etc/grafana/provisioning/dashboards
      - grafana-data:/var/lib/grafana
    ports:
      - "3000:3000"
    depends_on:
      - prometheus
      - loki
      - tempo

volumes:
  tempo-data:
  loki-data:
  prometheus-data:
  grafana-data:
```

---

## Testing Strategy

### Tracing Tests

```python
def test_tracing_spans_created():
    """Test that optimization creates expected spans."""
    from opentelemetry.sdk.trace import ReadableSpan
    from opentelemetry.sdk.trace.export import ConsoleSpanExporter

    # Configure test exporter
    exporter = ConsoleSpanExporter()

    # Run optimization
    service = OptimizationService()
    service.optimize_query("test-123")

    # Verify spans
    spans = exporter.get_finished_spans()
    span_names = [s.name for s in spans]

    assert "analysis.analyze_query" in span_names
    assert "agent.call_optimizer" in span_names
    assert any("detector." in name for name in span_names)
```

### Logging Tests

```python
def test_structured_logging():
    """Test that structured logs contain required fields."""
    from loguru import logger

    # Capture logs
    logs = []
    logger.add(lambda msg: logs.append(msg), format="{message}")

    # Generate log
    log_optimization_start("test-123")

    # Verify structure
    assert len(logs) == 1
    assert "job_id" in logs[0]
    assert "event_type" in logs[0]
```

---

## Success Criteria

- ✅ All API requests traced end-to-end in Tempo
- ✅ Structured logs searchable in Loki
- ✅ Prometheus metrics exposed at /metrics
- ✅ 3 Grafana dashboards operational
- ✅ Alert rules firing correctly
- ✅ Trace sampling reduces overhead to <5%
- ✅ P95 tracing overhead <100ms

---

## Next Steps

After Phase 6, proceed to:
- **Phase 7**: Comprehensive Testing & Documentation
