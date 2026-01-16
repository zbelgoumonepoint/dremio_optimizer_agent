# Phase 7: Comprehensive Testing & Documentation

**Duration**: 1-2 weeks
**Status**: Planned
**Dependencies**: Phases 1-6 (all components must be implemented)

## Overview

Establish comprehensive test coverage and production-ready documentation. This phase ensures the system is reliable, maintainable, and ready for deployment.

### Goals

1. Achieve 85%+ test coverage across all components
2. Implement unit, integration, and end-to-end tests
3. Create comprehensive API documentation
4. Write deployment and operational guides
5. Build troubleshooting documentation
6. Set up CI/CD pipeline

### Key Deliverables

- Comprehensive test suite (unit + integration + e2e)
- API documentation (OpenAPI + usage examples)
- Deployment guide (Docker + Kubernetes)
- Operational runbook
- Troubleshooting guide
- CI/CD pipeline (GitHub Actions)

---

## Testing Strategy

### Test Pyramid

```
        /\
       /  \      E2E Tests (10%)
      /    \     - Full workflow tests
     /------\    - API integration tests
    /        \
   /  INTEG   \  Integration Tests (30%)
  /    TESTS   \ - Service integration
 /--------------\- Database operations
/                \
/   UNIT TESTS    \ Unit Tests (60%)
\    (60%)        / - Business logic
 \----------------/ - Detectors, tools
                    - Utilities
```

---

## Component 1: Unit Tests

### Detector Tests

**File**: `tests/unit/detectors/test_partition_pruning_detector.py`

```python
import pytest
from src.analysis.detectors.partition_pruning_detector import PartitionPruningDetector
from src.database.models import Query, QueryProfile


class TestPartitionPruningDetector:
    """Test partition pruning detector."""

    def setup_method(self):
        """Setup test fixtures."""
        self.detector = PartitionPruningDetector()

    def test_detects_missing_partition_filter(self):
        """Test detection when partition filter is missing."""
        query = Query(
            sql_text="SELECT * FROM sales.orders WHERE status = 'COMPLETED'"
        )

        profile = QueryProfile(
            partitions_total=365,
            partitions_scanned=365,
            partition_columns=["order_date"]
        )

        result = self.detector.detect(query, profile, metadata=None)

        assert result.detected is True
        assert result.severity == "high"
        assert "partition" in result.title.lower()
        assert result.estimated_improvement_pct > 50

    def test_no_detection_when_partitions_pruned(self):
        """Test no detection when partitions are already pruned."""
        query = Query(
            sql_text="SELECT * FROM sales.orders WHERE order_date >= '2024-01-01'"
        )

        profile = QueryProfile(
            partitions_total=365,
            partitions_scanned=30,  # Only 30 days scanned
            partition_columns=["order_date"]
        )

        result = self.detector.detect(query, profile, metadata=None)

        assert result.detected is False

    def test_no_detection_when_table_not_partitioned(self):
        """Test no detection for non-partitioned tables."""
        query = Query(
            sql_text="SELECT * FROM dimension.customers"
        )

        profile = QueryProfile(
            partitions_total=None,
            partitions_scanned=None,
            partition_columns=[]
        )

        result = self.detector.detect(query, profile, metadata=None)

        assert result.detected is False

    @pytest.mark.parametrize("scanned,total,expected", [
        (10, 100, True),   # 10% scanned - should detect
        (50, 100, True),   # 50% scanned - should detect
        (90, 100, False),  # 90% scanned - no detection
    ])
    def test_pruning_ratio_threshold(self, scanned, total, expected):
        """Test pruning ratio threshold."""
        query = Query(sql_text="SELECT * FROM test")
        profile = QueryProfile(
            partitions_total=total,
            partitions_scanned=scanned,
            partition_columns=["date_col"]
        )

        result = self.detector.detect(query, profile, metadata=None)
        assert result.detected == expected
```

### Agent Tool Tests

**File**: `tests/unit/agents/test_query_analyzer.py`

```python
from src.agents.tools.query_analyzer import analyze_query_pattern


class TestQueryAnalyzer:
    """Test query pattern analyzer tool."""

    def test_detects_select_star(self):
        """Test detection of SELECT *."""
        sql = "SELECT * FROM sales.orders WHERE status = 'COMPLETED'"
        profile = {"rows_scanned": 1000, "rows_returned": 500}

        result = analyze_query_pattern(sql, profile)

        assert "select_star" in result.lower()
        assert "issue" in result.lower()

    def test_calculates_selectivity(self):
        """Test selectivity calculation."""
        sql = "SELECT customer_id FROM orders WHERE amount > 1000"
        profile = {"rows_scanned": 10000, "rows_returned": 500}

        result = analyze_query_pattern(sql, profile)

        assert "5.00%" in result  # 500/10000 = 5%
        assert "selectivity" in result.lower()

    def test_detects_join_fanout(self):
        """Test detection of join fan-out."""
        sql = "SELECT * FROM orders JOIN order_items ON orders.id = order_items.order_id"
        profile = {"rows_scanned": 1000, "rows_returned": 5000}

        result = analyze_query_pattern(sql, profile)

        assert "fan-out" in result.lower()

    def test_assesses_complexity(self):
        """Test complexity assessment."""
        # Simple query
        simple_sql = "SELECT id FROM orders"
        simple_profile = {}
        simple_result = analyze_query_pattern(simple_sql, simple_profile)
        assert "low" in simple_result.lower()

        # Complex query
        complex_sql = """
        SELECT customer_id, SUM(amount)
        FROM (
            SELECT * FROM orders WHERE status = 'COMPLETED'
        ) subquery
        JOIN customers ON subquery.customer_id = customers.id
        GROUP BY customer_id
        """
        complex_profile = {}
        complex_result = analyze_query_pattern(complex_sql, complex_profile)
        assert "high" in complex_result.lower()
```

### Service Tests

**File**: `tests/unit/services/test_analysis_service.py`

```python
from unittest.mock import Mock, patch
from src.services.analysis_service import AnalysisService


class TestAnalysisService:
    """Test analysis service."""

    def setup_method(self):
        """Setup test fixtures."""
        self.service = AnalysisService()

    @patch('src.services.analysis_service.QueryRepository')
    @patch('src.services.analysis_service.ProfileRepository')
    def test_analyze_query_returns_detected_issues(self, mock_profile_repo, mock_query_repo):
        """Test that analyze_query returns detected issues."""
        # Mock data
        mock_query = Mock(
            job_id="test-123",
            sql_text="SELECT * FROM large_table",
            duration_ms=60000
        )
        mock_profile = Mock(
            rows_scanned=10000000,
            rows_returned=5000000,
            partitions_total=365,
            partitions_scanned=365
        )

        mock_query_repo.return_value.get_by_job_id.return_value = mock_query
        mock_profile_repo.return_value.get_by_job_id.return_value = mock_profile

        # Execute
        issues = self.service.analyze_query("test-123")

        # Assert
        assert len(issues) > 0
        assert any(issue["issue_type"] == "missing_partition_filter" for issue in issues)

    def test_analyze_batch_processes_multiple_queries(self):
        """Test batch analysis processes multiple queries."""
        # Mock recent queries
        with patch.object(self.service, 'analyze_query') as mock_analyze:
            mock_analyze.return_value = [{"issue_type": "test"}]

            results = self.service.analyze_batch(limit=10)

            assert mock_analyze.call_count > 0
            assert len(results) > 0
```

---

## Component 2: Integration Tests

### Database Integration Tests

**File**: `tests/integration/test_database_operations.py`

```python
import pytest
from datetime import datetime
from src.database.connection import get_db_session
from src.database.models import Query, QueryProfile, Recommendation
from src.database.repositories.query_repository import QueryRepository


@pytest.fixture
def db_session():
    """Create test database session."""
    with get_db_session() as session:
        yield session
        session.rollback()


class TestDatabaseOperations:
    """Integration tests for database operations."""

    def test_create_and_retrieve_query(self, db_session):
        """Test creating and retrieving a query."""
        repo = QueryRepository(db_session)

        # Create query
        query_data = {
            "job_id": "test-integration-123",
            "sql_text": "SELECT * FROM test",
            "user": "test_user",
            "duration_ms": 5000,
            "status": "COMPLETED",
            "start_time": datetime.utcnow()
        }

        created = repo.create(query_data)
        db_session.commit()

        # Retrieve
        retrieved = repo.get_by_job_id("test-integration-123")

        assert retrieved is not None
        assert retrieved.job_id == "test-integration-123"
        assert retrieved.duration_ms == 5000

    def test_query_with_profile_relationship(self, db_session):
        """Test query-profile relationship."""
        # Create query
        query = Query(
            job_id="test-rel-456",
            sql_text="SELECT 1",
            duration_ms=1000,
            start_time=datetime.utcnow()
        )
        db_session.add(query)
        db_session.commit()

        # Create profile
        profile = QueryProfile(
            job_id="test-rel-456",
            profile_json={"test": "data"},
            rows_scanned=100,
            rows_returned=50
        )
        db_session.add(profile)
        db_session.commit()

        # Retrieve with relationship
        retrieved_query = db_session.query(Query).filter_by(job_id="test-rel-456").first()

        assert retrieved_query.profile is not None
        assert retrieved_query.profile.rows_scanned == 100
```

### API Integration Tests

**File**: `tests/integration/test_optimization_flow.py`

```python
import pytest
from src.services.optimization_service import OptimizationService
from src.services.analysis_service import AnalysisService
from src.services.recommendation_service import RecommendationService


@pytest.mark.integration
class TestOptimizationFlow:
    """End-to-end optimization workflow tests."""

    def test_full_optimization_workflow(self, db_session, dremio_client):
        """Test complete optimization workflow."""
        # Given: A query exists in Dremio
        job_id = "test-workflow-789"

        # Mock Dremio data collection
        # (In real test, would use test Dremio instance)

        # When: We optimize the query
        optimization_service = OptimizationService()
        result = optimization_service.optimize_query(job_id)

        # Then: We get issues and recommendations
        assert "issues_detected" in result
        assert "recommendations" in result
        assert len(result["issues_detected"]) > 0
        assert len(result["recommendations"]) > 0

        # And: Data is persisted
        recommendation_service = RecommendationService()
        saved_recs = recommendation_service.get_recommendations(job_id=job_id)
        assert len(saved_recs) > 0

    def test_analysis_to_recommendation_flow(self, db_session):
        """Test flow from analysis to recommendation generation."""
        # Setup test query and profile
        # ...

        # Analyze
        analysis_service = AnalysisService()
        issues = analysis_service.analyze_query("test-789")

        assert len(issues) > 0

        # Generate recommendations
        recommendation_service = RecommendationService()
        query_context = {"job_id": "test-789", "sql_text": "...", "duration_ms": 30000}

        recommendations = recommendation_service.generate_recommendations(
            "test-789", query_context, issues
        )

        assert len(recommendations) > 0
        assert recommendations[0]["issue_type"] in [i["issue_type"] for i in issues]
```

---

## Component 3: End-to-End Tests

### API E2E Tests

**File**: `tests/e2e/test_api_endpoints.py`

```python
import pytest
from fastapi.testclient import TestClient
from src.api.main import create_app


@pytest.fixture
def client():
    """Create test client."""
    app = create_app()
    return TestClient(app)


@pytest.fixture
def auth_headers(client):
    """Get authentication headers."""
    return {"X-API-Key": "test-api-key"}


class TestOptimizationEndpoints:
    """E2E tests for optimization endpoints."""

    def test_health_check(self, client):
        """Test health check endpoint."""
        response = client.get("/health")

        assert response.status_code == 200
        assert response.json()["status"] == "healthy"

    def test_optimize_query_requires_auth(self, client):
        """Test authentication is required."""
        response = client.post(
            "/api/v1/optimize/query",
            json={"job_id": "test-123"}
        )

        assert response.status_code == 401

    def test_optimize_query_success(self, client, auth_headers):
        """Test successful query optimization."""
        response = client.post(
            "/api/v1/optimize/query",
            json={"job_id": "test-e2e-123"},
            headers=auth_headers
        )

        assert response.status_code == 200
        data = response.json()

        assert "job_id" in data
        assert "issues_detected" in data
        assert "recommendations" in data
        assert isinstance(data["issues_detected"], list)

    def test_list_recommendations(self, client, auth_headers):
        """Test listing recommendations."""
        response = client.get(
            "/api/v1/recommendations",
            headers=auth_headers
        )

        assert response.status_code == 200
        data = response.json()

        assert "recommendations" in data
        assert "total" in data

    def test_get_metrics_summary(self, client, auth_headers):
        """Test metrics summary endpoint."""
        response = client.get(
            "/api/v1/metrics/summary?days=7",
            headers=auth_headers
        )

        assert response.status_code == 200
        data = response.json()

        assert "queries_analyzed" in data
        assert "avg_improvement_pct" in data

    def test_record_measurement_workflow(self, client, auth_headers):
        """Test full measurement workflow."""
        # First, create a recommendation (via optimization)
        opt_response = client.post(
            "/api/v1/optimize/query",
            json={"job_id": "test-meas-456"},
            headers=auth_headers
        )

        recommendation_id = opt_response.json()["recommendations"][0]["id"]

        # Record before metrics
        before_response = client.post(
            "/api/v1/measurements/before",
            json={
                "recommendation_id": recommendation_id,
                "job_id": "test-meas-456"
            },
            headers=auth_headers
        )

        assert before_response.status_code == 200

        # Record after metrics
        after_response = client.post(
            "/api/v1/measurements/after",
            json={
                "recommendation_id": recommendation_id,
                "job_id": "test-meas-456-optimized"
            },
            headers=auth_headers
        )

        assert after_response.status_code == 200
        data = after_response.json()

        assert "duration_improvement_pct" in data
        assert "meets_expectation" in data
```

---

## Component 4: Test Infrastructure

### Pytest Configuration

**File**: `pytest.ini`

```ini
[pytest]
testpaths = tests
python_files = test_*.py
python_classes = Test*
python_functions = test_*
asyncio_mode = auto

markers =
    unit: Unit tests
    integration: Integration tests
    e2e: End-to-end tests
    slow: Slow-running tests

addopts =
    --verbose
    --cov=src
    --cov-report=html
    --cov-report=term-missing
    --cov-fail-under=85
```

### Fixtures

**File**: `tests/conftest.py`

```python
import pytest
from src.database.connection import engine, Base
from src.config.settings import get_settings


@pytest.fixture(scope="session")
def test_db():
    """Create test database."""
    Base.metadata.create_all(engine)
    yield
    Base.metadata.drop_all(engine)


@pytest.fixture
def db_session(test_db):
    """Create database session for tests."""
    from src.database.connection import get_db_session

    with get_db_session() as session:
        yield session
        session.rollback()


@pytest.fixture
def dremio_client():
    """Create test Dremio client."""
    from src.clients.dremio_client import DremioClient
    return DremioClient()


@pytest.fixture
def sample_query():
    """Sample query for testing."""
    return {
        "job_id": "sample-123",
        "sql_text": "SELECT * FROM sales.orders WHERE status = 'COMPLETED'",
        "duration_ms": 45000,
        "rows_scanned": 10000000,
        "rows_returned": 500000
    }


@pytest.fixture
def sample_profile():
    """Sample profile for testing."""
    return {
        "job_id": "sample-123",
        "rows_scanned": 10000000,
        "rows_returned": 500000,
        "partitions_total": 365,
        "partitions_scanned": 365,
        "memory_allocated": 2147483648,  # 2GB
        "cpu_time_ms": 120000
    }
```

---

## Component 5: CI/CD Pipeline

### GitHub Actions Workflow

**File**: `.github/workflows/ci.yml`

```yaml
name: CI/CD Pipeline

on:
  push:
    branches: [main, develop]
  pull_request:
    branches: [main, develop]

jobs:
  test:
    runs-on: ubuntu-latest

    services:
      postgres:
        image: postgres:15
        env:
          POSTGRES_DB: optimizer_test
          POSTGRES_USER: postgres
          POSTGRES_PASSWORD: postgres
        options: >-
          --health-cmd pg_isready
          --health-interval 10s
          --health-timeout 5s
          --health-retries 5
        ports:
          - 5432:5432

    steps:
      - name: Checkout code
        uses: actions/checkout@v3

      - name: Set up Python
        uses: actions/setup-python@v4
        with:
          python-version: '3.11'

      - name: Install uv
        run: curl -LsSf https://astral.sh/uv/install.sh | sh

      - name: Create virtual environment
        run: uv venv

      - name: Install dependencies
        run: |
          source .venv/bin/activate
          uv sync

      - name: Run linting
        run: |
          source .venv/bin/activate
          ruff check src/
          black --check src/

      - name: Run type checking
        run: |
          source .venv/bin/activate
          mypy src/

      - name: Run unit tests
        env:
          DATABASE_URL: postgresql://postgres:postgres@localhost:5432/optimizer_test
        run: |
          source .venv/bin/activate
          pytest tests/unit -v --cov=src --cov-report=xml

      - name: Run integration tests
        env:
          DATABASE_URL: postgresql://postgres:postgres@localhost:5432/optimizer_test
        run: |
          source .venv/bin/activate
          pytest tests/integration -v

      - name: Upload coverage
        uses: codecov/codecov-action@v3
        with:
          file: ./coverage.xml
          fail_ci_if_error: true

  build:
    needs: test
    runs-on: ubuntu-latest
    if: github.ref == 'refs/heads/main'

    steps:
      - name: Checkout code
        uses: actions/checkout@v3

      - name: Build Docker image
        run: docker build -t dremio-optimizer-agent:${{ github.sha }} .

      - name: Push to registry
        run: |
          echo "${{ secrets.DOCKER_PASSWORD }}" | docker login -u "${{ secrets.DOCKER_USERNAME }}" --password-stdin
          docker push dremio-optimizer-agent:${{ github.sha }}
```

---

## Component 6: Documentation

### API Documentation

**Auto-generated via FastAPI at `/docs`**

Additional manual documentation:

**File**: `docs/API_REFERENCE.md`

```markdown
# API Reference

## Authentication

All API endpoints (except /health) require authentication via API key:

```bash
curl -H "X-API-Key: your-api-key" https://api.example.com/api/v1/optimize/query
```

## Endpoints

### POST /api/v1/optimize/query

Optimize a single query.

**Request:**
```json
{
  "job_id": "abc123"
}
```

**Response:**
```json
{
  "job_id": "abc123",
  "analyzed_at": "2026-01-15T10:30:00Z",
  "issues_detected": [...],
  "recommendations": [...],
  "total_estimated_improvement_pct": 65.0
}
```

### GET /api/v1/recommendations

List recommendations with filters.

**Query Parameters:**
- `job_id` (optional): Filter by job ID
- `status` (optional): pending | implemented | rejected
- `severity` (optional): high | medium | low
- `limit` (optional): Max results (default: 100)

**Response:**
```json
{
  "recommendations": [...],
  "total": 42
}
```

[Continue with all endpoints...]
```

### Deployment Guide

**File**: `docs/DEPLOYMENT.md`

```markdown
# Deployment Guide

## Prerequisites

- Docker 20.10+
- Docker Compose 2.0+
- PostgreSQL 15+
- 4GB RAM minimum
- Access to Dremio instance

## Quick Start with Docker Compose

1. Clone repository:
```bash
git clone https://github.com/yourorg/dremio-optimizer-agent.git
cd dremio-optimizer-agent
```

2. Configure environment:
```bash
cp .env.example .env
# Edit .env with your settings
```

3. Start services:
```bash
docker-compose up -d
```

4. Verify deployment:
```bash
curl http://localhost:8000/health
```

## Production Deployment

### Kubernetes Deployment

[Include Kubernetes manifests and instructions]

### Configuration

[Detail all environment variables]

### Scaling

[Describe horizontal scaling strategies]

### Backup & Recovery

[Detail backup procedures]
```

### Operational Runbook

**File**: `docs/RUNBOOK.md`

```markdown
# Operational Runbook

## Common Operations

### Restart Service

```bash
docker-compose restart optimizer-api
```

### View Logs

```bash
docker-compose logs -f optimizer-api
```

### Database Migrations

```bash
docker-compose exec optimizer-api alembic upgrade head
```

## Troubleshooting

### High Error Rate

**Symptoms:** Alert "HighOptimizationErrorRate" firing

**Investigation:**
1. Check logs: `docker-compose logs optimizer-api | grep ERROR`
2. Check Dremio connectivity: `curl -v $DREMIO_URL`
3. Check database: `docker-compose exec postgres psql -U postgres -c "SELECT 1"`

**Resolution:**
- If Dremio down: Wait for Dremio recovery
- If database down: Restart postgres container
- If application error: Check logs and restart service

[Continue with more scenarios...]
```

---

## Success Criteria

- ✅ Test coverage ≥85% (unit + integration)
- ✅ All E2E tests passing
- ✅ CI/CD pipeline operational
- ✅ API documentation complete
- ✅ Deployment guide tested
- ✅ Runbook covers common scenarios
- ✅ Zero critical security vulnerabilities

---

## Deliverables Checklist

### Testing
- [ ] Unit tests (60+ tests)
- [ ] Integration tests (20+ tests)
- [ ] E2E tests (10+ tests)
- [ ] Performance tests
- [ ] Security tests

### Documentation
- [ ] API reference (OpenAPI + examples)
- [ ] Deployment guide (Docker + K8s)
- [ ] Operational runbook
- [ ] Troubleshooting guide
- [ ] Architecture diagrams
- [ ] Contributing guide

### CI/CD
- [ ] GitHub Actions workflow
- [ ] Automated testing
- [ ] Code coverage reporting
- [ ] Docker image build
- [ ] Automated deployment (staging)

### Quality
- [ ] Linting configured (ruff)
- [ ] Formatting configured (black)
- [ ] Type checking (mypy)
- [ ] Security scanning
- [ ] Dependency scanning

---

## Post-Phase 7

After completing Phase 7, the system is **production-ready**:
- Fully tested and documented
- CI/CD pipeline operational
- Monitoring and alerting configured
- Runbook for operations team
- Ready for deployment to production

**Next:** Deploy to production environment and begin measuring real-world impact!
