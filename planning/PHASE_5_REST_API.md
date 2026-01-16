# Phase 5: REST API Development

**Duration**: 1 week
**Status**: Planned
**Dependencies**: Phases 1-4 (all core services must be functional)

## Overview

Build a comprehensive FastAPI-based REST API that exposes all optimizer functionality: data collection, analysis, recommendations, and measurements. This API enables integration with external systems, dashboards, and automation workflows.

### Goals

1. Expose all optimizer services via REST endpoints
2. Implement authentication and authorization
3. Create OpenAPI documentation
4. Add rate limiting and caching
5. Build comprehensive error handling
6. Enable batch operations and async processing

### Key Deliverables

- Complete REST API with 20+ endpoints
- OpenAPI/Swagger documentation
- Authentication middleware
- Rate limiting and caching
- API client SDK (Python)
- Integration tests for all endpoints

---

## Architecture

```
External Systems → FastAPI (Auth + Rate Limit) → Services → Database
                          ↓
                  OpenAPI Docs (/docs)
                  Health Checks (/health)
```

---

## Component 1: Main FastAPI Application

### File: `src/api/main.py`

```python
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.trustedhost import TrustedHostMiddleware
from fastapi.responses import JSONResponse
from contextlib import asynccontextmanager
import uvicorn

from src.api.routes import (
    optimization,
    recommendations,
    analysis,
    measurements,
    metrics,
    health
)
from src.api.middleware.auth import AuthMiddleware
from src.api.middleware.rate_limit import RateLimitMiddleware
from src.observability.tracing import setup_tracing
from src.observability.logging import setup_logging
from src.config.settings import get_settings

settings = get_settings()


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan events."""
    # Startup
    setup_logging()
    setup_tracing()
    print("🚀 Dremio Optimizer Agent API started")

    yield

    # Shutdown
    print("👋 Shutting down Dremio Optimizer Agent API")


def create_app() -> FastAPI:
    """Create and configure FastAPI application."""

    app = FastAPI(
        title="Dremio Optimizer Agent API",
        description="AI-powered query optimization and performance analysis for Dremio",
        version="1.0.0",
        docs_url="/docs",
        redoc_url="/redoc",
        openapi_url="/openapi.json",
        lifespan=lifespan
    )

    # CORS middleware
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # Trusted host middleware (security)
    if settings.environment == "production":
        app.add_middleware(
            TrustedHostMiddleware,
            allowed_hosts=settings.allowed_hosts
        )

    # Custom middleware
    app.add_middleware(AuthMiddleware)
    app.add_middleware(RateLimitMiddleware)

    # Exception handlers
    @app.exception_handler(ValueError)
    async def value_error_handler(request, exc):
        return JSONResponse(
            status_code=400,
            content={"detail": str(exc)}
        )

    @app.exception_handler(Exception)
    async def general_exception_handler(request, exc):
        return JSONResponse(
            status_code=500,
            content={"detail": "Internal server error"}
        )

    # Include routers
    app.include_router(health.router)
    app.include_router(optimization.router)
    app.include_router(recommendations.router)
    app.include_router(analysis.router)
    app.include_router(measurements.router)
    app.include_router(metrics.router)

    return app


app = create_app()


if __name__ == "__main__":
    uvicorn.run(
        "src.api.main:app",
        host="0.0.0.0",
        port=8000,
        reload=settings.environment == "development"
    )
```

---

## Component 2: API Routes

### Optimization Routes

**File**: `src/api/routes/optimization.py`

```python
from fastapi import APIRouter, BackgroundTasks, HTTPException
from typing import Optional
from src.services.optimization_service import OptimizationService
from src.api.schemas.optimization_schema import (
    OptimizeQueryRequest,
    OptimizeQueryResponse,
    OptimizeBatchRequest,
    OptimizeBatchResponse,
    CollectDataRequest,
    CollectDataResponse
)

router = APIRouter(prefix="/api/v1/optimize", tags=["optimization"])


@router.post("/query", response_model=OptimizeQueryResponse)
async def optimize_query(request: OptimizeQueryRequest):
    """
    Analyze and optimize a single query.

    Full workflow: collect data → analyze → generate recommendations

    Returns:
    - Detected issues
    - AI-generated recommendations
    - Estimated improvements
    """
    service = OptimizationService()

    try:
        result = await service.optimize_query(request.job_id)
        return OptimizeQueryResponse(**result)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))


@router.post("/batch", response_model=OptimizeBatchResponse)
async def optimize_batch(
    request: OptimizeBatchRequest,
    background_tasks: BackgroundTasks
):
    """
    Batch optimize multiple queries (background task).

    Analyzes recent queries and generates recommendations for all
    queries with performance issues.

    Returns task ID to check progress.
    """
    service = OptimizationService()

    task_id = await service.optimize_batch_async(
        lookback_hours=request.lookback_hours,
        limit=request.limit,
        background_tasks=background_tasks
    )

    return OptimizeBatchResponse(
        task_id=task_id,
        status="started",
        message=f"Batch optimization started for {request.limit} queries"
    )


@router.get("/batch/{task_id}")
async def get_batch_status(task_id: str):
    """Get status of batch optimization task."""
    service = OptimizationService()
    status = await service.get_batch_status(task_id)

    if not status:
        raise HTTPException(status_code=404, detail="Task not found")

    return status


@router.post("/collect", response_model=CollectDataResponse)
async def collect_data(request: CollectDataRequest):
    """
    Trigger data collection from Dremio.

    Collects:
    - Query history
    - Query profiles
    - Metadata
    - Reflections
    """
    service = OptimizationService()

    try:
        result = await service.collect_data(
            lookback_hours=request.lookback_hours
        )
        return CollectDataResponse(**result)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
```

### Recommendations Routes

**File**: `src/api/routes/recommendations.py`

```python
from fastapi import APIRouter, HTTPException, Query
from typing import Optional, List
from src.services.recommendation_service import RecommendationService
from src.api.schemas.recommendation_schema import (
    RecommendationResponse,
    RecommendationListResponse,
    RecommendationStatusUpdate
)

router = APIRouter(prefix="/api/v1/recommendations", tags=["recommendations"])


@router.get("", response_model=RecommendationListResponse)
async def list_recommendations(
    job_id: Optional[str] = None,
    status: Optional[str] = Query(None, regex="^(pending|implemented|rejected|in_progress)$"),
    severity: Optional[str] = Query(None, regex="^(high|medium|low)$"),
    limit: int = Query(100, ge=1, le=1000)
):
    """
    List recommendations with optional filters.

    Filters:
    - job_id: Filter by specific query
    - status: pending, implemented, rejected, in_progress
    - severity: high, medium, low
    - limit: Maximum results (1-1000)
    """
    service = RecommendationService()

    recommendations = service.get_recommendations(
        job_id=job_id,
        status=status,
        severity=severity,
        limit=limit
    )

    return RecommendationListResponse(
        recommendations=recommendations,
        total=len(recommendations)
    )


@router.get("/{recommendation_id}", response_model=RecommendationResponse)
async def get_recommendation(recommendation_id: int):
    """Get specific recommendation by ID."""
    service = RecommendationService()

    # Implementation here
    recommendation = service.get_by_id(recommendation_id)

    if not recommendation:
        raise HTTPException(status_code=404, detail="Recommendation not found")

    return RecommendationResponse(**recommendation)


@router.patch("/{recommendation_id}/status")
async def update_recommendation_status(
    recommendation_id: int,
    update: RecommendationStatusUpdate
):
    """
    Update recommendation status.

    Status transitions:
    - pending → in_progress
    - in_progress → implemented | rejected
    """
    service = RecommendationService()

    try:
        updated = service.update_status(
            recommendation_id=recommendation_id,
            status=update.status,
            notes=update.notes
        )
        return updated
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))


@router.get("/{recommendation_id}/impact")
async def get_recommendation_impact(recommendation_id: int):
    """
    Get measured impact for a recommendation.

    Returns before/after metrics and actual improvement.
    """
    from src.services.measurement_service import MeasurementService

    service = MeasurementService()
    measurement = service.get_measurement(recommendation_id)

    if not measurement:
        raise HTTPException(
            status_code=404,
            detail="No measurements found for this recommendation"
        )

    return measurement
```

### Analysis Routes

**File**: `src/api/routes/analysis.py`

```python
from fastapi import APIRouter, Query
from typing import List
from src.services.analysis_service import AnalysisService
from src.api.schemas.analysis_schema import (
    BaselineResponse,
    RegressionResponse,
    IssueTypeBreakdown
)

router = APIRouter(prefix="/api/v1/analysis", tags=["analysis"])


@router.get("/baselines")
async def list_baselines(limit: int = Query(100, ge=1, le=1000)):
    """List performance baselines for query signatures."""
    service = AnalysisService()
    baselines = service.get_baselines(limit=limit)

    return {
        "baselines": baselines,
        "total": len(baselines)
    }


@router.post("/baselines/refresh")
async def refresh_baselines():
    """
    Refresh all baselines.

    Recalculates p50/p95/p99 for all query signatures
    based on recent executions.
    """
    service = AnalysisService()
    result = await service.refresh_all_baselines()

    return {
        "status": "success",
        "baselines_refreshed": result["count"],
        "duration_seconds": result["duration_seconds"]
    }


@router.get("/regressions")
async def detect_regressions(
    lookback_hours: int = Query(24, ge=1, le=168)
):
    """
    Detect query regressions in last N hours.

    Compares recent query durations to baselines and flags
    queries running significantly slower than normal.
    """
    service = AnalysisService()
    regressions = service.detect_regressions(lookback_hours=lookback_hours)

    return {
        "regressions": regressions,
        "total": len(regressions),
        "lookback_hours": lookback_hours
    }


@router.get("/issues/breakdown")
async def get_issue_breakdown(days: int = Query(7, ge=1, le=90)):
    """
    Get breakdown of detected issues by type.

    Returns count and percentage for each issue type.
    """
    service = AnalysisService()
    breakdown = service.get_issue_breakdown(days=days)

    return breakdown
```

### Metrics Routes

**File**: `src/api/routes/metrics.py`

```python
from fastapi import APIRouter, Query
from src.services.metrics_service import MetricsService

router = APIRouter(prefix="/api/v1/metrics", tags=["metrics"])


@router.get("/summary")
async def get_metrics_summary(days: int = Query(30, ge=1, le=365)):
    """
    Get summary metrics for optimizer performance.

    Returns:
    - Queries analyzed
    - Issues detected
    - Recommendations generated
    - Average improvement
    - Adoption rate
    """
    service = MetricsService()
    summary = service.get_summary(days=days)

    return summary


@router.get("/by-issue-type")
async def get_metrics_by_issue_type(days: int = Query(30, ge=1, le=365)):
    """
    Get metrics broken down by issue type.

    Shows effectiveness of each detector type.
    """
    service = MetricsService()
    breakdown = service.get_by_issue_type(days=days)

    return breakdown


@router.get("/adoption")
async def get_adoption_metrics(days: int = Query(30, ge=1, le=365)):
    """
    Get recommendation adoption metrics.

    Shows how many recommendations are implemented vs rejected.
    """
    service = MetricsService()
    adoption = service.get_adoption_metrics(days=days)

    return adoption


@router.get("/trends")
async def get_performance_trends(days: int = Query(90, ge=7, le=365)):
    """
    Get performance trends over time.

    Shows time-series data for key metrics.
    """
    service = MetricsService()
    trends = service.get_trends(days=days)

    return trends
```

### Health Routes

**File**: `src/api/routes/health.py`

```python
from fastapi import APIRouter
from datetime import datetime
from src.database.connection import engine
from src.clients.dremio_client import DremioClient
from src.config.settings import get_settings

router = APIRouter(tags=["health"])


@router.get("/health")
async def health_check():
    """Basic health check."""
    return {
        "status": "healthy",
        "timestamp": datetime.utcnow().isoformat(),
        "version": "1.0.0"
    }


@router.get("/health/detailed")
async def detailed_health_check():
    """Detailed health check with dependency status."""
    settings = get_settings()

    # Check database
    db_healthy = False
    try:
        with engine.connect() as conn:
            conn.execute("SELECT 1")
        db_healthy = True
    except Exception as e:
        db_error = str(e)

    # Check Dremio connection
    dremio_healthy = False
    try:
        client = DremioClient()
        client.authenticate()
        dremio_healthy = True
    except Exception as e:
        dremio_error = str(e)

    overall_status = "healthy" if (db_healthy and dremio_healthy) else "degraded"

    return {
        "status": overall_status,
        "timestamp": datetime.utcnow().isoformat(),
        "version": "1.0.0",
        "dependencies": {
            "database": {
                "status": "healthy" if db_healthy else "unhealthy",
                "error": None if db_healthy else db_error
            },
            "dremio": {
                "status": "healthy" if dremio_healthy else "unhealthy",
                "error": None if dremio_healthy else dremio_error
            }
        }
    }
```

---

## Component 3: Authentication & Authorization

### File: `src/api/middleware/auth.py`

```python
from fastapi import Request, HTTPException
from starlette.middleware.base import BaseHTTPMiddleware
from src.config.settings import get_settings
import secrets

settings = get_settings()


class AuthMiddleware(BaseHTTPMiddleware):
    """API key authentication middleware."""

    async def dispatch(self, request: Request, call_next):
        # Skip auth for health and docs endpoints
        if request.url.path in ["/health", "/health/detailed", "/docs", "/redoc", "/openapi.json"]:
            return await call_next(request)

        # Check API key
        api_key = request.headers.get("X-API-Key")

        if not api_key:
            raise HTTPException(status_code=401, detail="API key required")

        # Validate API key (constant-time comparison)
        if not secrets.compare_digest(api_key, settings.api_key):
            raise HTTPException(status_code=403, detail="Invalid API key")

        response = await call_next(request)
        return response
```

---

## Component 4: Rate Limiting

### File: `src/api/middleware/rate_limit.py`

```python
from fastapi import Request, HTTPException
from starlette.middleware.base import BaseHTTPMiddleware
from collections import defaultdict
from datetime import datetime, timedelta
import asyncio


class RateLimitMiddleware(BaseHTTPMiddleware):
    """Rate limiting middleware using token bucket algorithm."""

    def __init__(self, app, requests_per_minute: int = 60):
        super().__init__(app)
        self.requests_per_minute = requests_per_minute
        self.buckets = defaultdict(lambda: {"tokens": requests_per_minute, "last_update": datetime.utcnow()})
        self.lock = asyncio.Lock()

    async def dispatch(self, request: Request, call_next):
        # Skip rate limiting for health checks
        if request.url.path.startswith("/health"):
            return await call_next(request)

        # Get client identifier (API key or IP)
        client_id = request.headers.get("X-API-Key", request.client.host)

        async with self.lock:
            bucket = self.buckets[client_id]
            now = datetime.utcnow()

            # Refill tokens based on time elapsed
            elapsed = (now - bucket["last_update"]).total_seconds()
            tokens_to_add = (elapsed / 60) * self.requests_per_minute
            bucket["tokens"] = min(self.requests_per_minute, bucket["tokens"] + tokens_to_add)
            bucket["last_update"] = now

            # Check if request is allowed
            if bucket["tokens"] >= 1:
                bucket["tokens"] -= 1
                response = await call_next(request)
                response.headers["X-RateLimit-Remaining"] = str(int(bucket["tokens"]))
                return response
            else:
                raise HTTPException(
                    status_code=429,
                    detail="Rate limit exceeded. Try again later.",
                    headers={"Retry-After": "60"}
                )
```

---

## Component 5: Metrics Service

### File: `src/services/metrics_service.py`

```python
from typing import Dict, Any
from datetime import datetime, timedelta
from src.database.connection import get_db_session
from src.database.repositories import (
    QueryRepository,
    RecommendationRepository,
    MeasurementRepository
)


class MetricsService:
    """Service for aggregate metrics and analytics."""

    def get_summary(self, days: int = 30) -> Dict[str, Any]:
        """Get summary metrics."""
        cutoff = datetime.utcnow() - timedelta(days=days)

        with get_db_session() as session:
            query_repo = QueryRepository(session)
            rec_repo = RecommendationRepository(session)
            meas_repo = MeasurementRepository(session)

            queries_analyzed = query_repo.count_since(cutoff)
            recommendations = rec_repo.count_since(cutoff)
            measurements = meas_repo.get_recent(days=days)

            completed = [m for m in measurements if m.job_id_after is not None]
            avg_improvement = (
                sum(m.duration_improvement_pct or 0 for m in completed) / len(completed)
                if completed else 0
            )

            return {
                "period_days": days,
                "queries_analyzed": queries_analyzed,
                "recommendations_generated": recommendations,
                "optimizations_measured": len(completed),
                "avg_improvement_pct": round(avg_improvement, 1),
                "total_time_saved_hours": sum(
                    (m.before_duration_ms - m.after_duration_ms) / (1000 * 3600)
                    for m in completed
                    if m.before_duration_ms and m.after_duration_ms
                )
            }

    def get_by_issue_type(self, days: int = 30) -> Dict[str, Any]:
        """Get metrics by issue type."""
        # Implementation
        pass

    def get_adoption_metrics(self, days: int = 30) -> Dict[str, Any]:
        """Get recommendation adoption metrics."""
        # Implementation
        pass

    def get_trends(self, days: int = 90) -> Dict[str, Any]:
        """Get time-series trends."""
        # Implementation
        pass
```

---

## Component 6: Testing

### Integration Tests

**File**: `tests/integration/test_api.py`

```python
from fastapi.testclient import TestClient
from src.api.main import app

client = TestClient(app)


def test_health_check():
    """Test health endpoint."""
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json()["status"] == "healthy"


def test_optimize_query_requires_auth():
    """Test authentication required."""
    response = client.post("/api/v1/optimize/query", json={"job_id": "test-123"})
    assert response.status_code == 401


def test_optimize_query_with_auth(api_key):
    """Test query optimization with authentication."""
    response = client.post(
        "/api/v1/optimize/query",
        json={"job_id": "test-123"},
        headers={"X-API-Key": api_key}
    )
    assert response.status_code == 200
    assert "issues_detected" in response.json()
```

---

## Success Criteria

- ✅ All endpoints functional and documented
- ✅ OpenAPI documentation at /docs
- ✅ Authentication and rate limiting working
- ✅ Response time <500ms p95
- ✅ API test coverage >90%
- ✅ Client SDK generated and tested

---

## Next Steps

After Phase 5, proceed to:
- **Phase 6**: Observability (tracing, logging, monitoring)
- **Phase 7**: Testing & Documentation
