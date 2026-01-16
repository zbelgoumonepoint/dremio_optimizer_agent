# Phase 4: Performance Measurement System

**Duration**: 1 week
**Status**: Planned
**Dependencies**: Phases 2 & 3 (Analysis Engine, AI Agent)

## Overview

Build a comprehensive system to measure and validate the actual performance impact of implemented optimizations. This phase provides empirical evidence that recommendations deliver real improvements.

### Goals

1. Track before/after metrics for all optimizations
2. Calculate actual performance improvements
3. Compare estimated vs actual impact
4. Build optimization success dashboard
5. Enable continuous learning from measurements

### Key Deliverables

- Measurement service with before/after tracking
- Impact calculation algorithms
- Measurement API endpoints
- Success metrics dashboard
- Automated validation workflows

---

## Architecture

```
Recommendation → Before Metrics → Implementation → After Metrics → Impact Analysis
                      ↓                                    ↓              ↓
                 measurements                         measurements    Success %
                 table (before_*)                     table (after_*)  Validation
```

---

## Component 1: Measurement Data Model

### Database Schema Enhancement

**File**: `src/database/models.py` (add to existing)

```python
class Measurement(Base):
    """Track before/after performance metrics for optimizations."""

    __tablename__ = "measurements"

    id = Column(Integer, primary_key=True, autoincrement=True)
    recommendation_id = Column(Integer, ForeignKey("recommendations.id"), nullable=False)
    job_id_before = Column(String(100), nullable=False)
    job_id_after = Column(String(100), nullable=True)

    # Before metrics (original query)
    before_duration_ms = Column(Integer, nullable=False)
    before_memory_mb = Column(Integer)
    before_data_scanned_mb = Column(Integer)
    before_rows_scanned = Column(BigInteger)
    before_rows_returned = Column(BigInteger)
    before_partitions_scanned = Column(Integer)
    before_cpu_time_ms = Column(Integer)

    # After metrics (optimized query)
    after_duration_ms = Column(Integer)
    after_memory_mb = Column(Integer)
    after_data_scanned_mb = Column(Integer)
    after_rows_scanned = Column(BigInteger)
    after_rows_returned = Column(BigInteger)
    after_partitions_scanned = Column(Integer)
    after_cpu_time_ms = Column(Integer)

    # Calculated improvements
    duration_improvement_pct = Column(Float)
    memory_reduction_pct = Column(Float)
    scan_reduction_pct = Column(Float)
    cpu_reduction_pct = Column(Float)

    # Validation
    meets_expectation = Column(Boolean)  # Did we meet estimated improvement?
    expectation_delta_pct = Column(Float)  # Difference: actual - estimated
    validation_notes = Column(Text)

    # Metadata
    measured_at = Column(DateTime, default=datetime.utcnow)
    measured_by = Column(String(100))  # User or system

    # Relationships
    recommendation = relationship("Recommendation", back_populates="measurements")

    __table_args__ = (
        Index("idx_measurements_recommendation", "recommendation_id"),
        Index("idx_measurements_before_job", "job_id_before"),
        Index("idx_measurements_after_job", "job_id_after"),
    )
```

### Migration

**File**: `alembic/versions/004_add_measurements.py`

```python
def upgrade():
    op.create_table(
        'measurements',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('recommendation_id', sa.Integer(), nullable=False),
        sa.Column('job_id_before', sa.String(100), nullable=False),
        sa.Column('job_id_after', sa.String(100)),
        # ... all columns from model
        sa.ForeignKeyConstraint(['recommendation_id'], ['recommendations.id']),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('idx_measurements_recommendation', 'measurements', ['recommendation_id'])
```

---

## Component 2: Measurement Service

### File: `src/services/measurement_service.py`

```python
from typing import Dict, Any, Optional
from datetime import datetime
from src.database.repositories.measurement_repository import MeasurementRepository
from src.database.repositories.query_repository import QueryRepository
from src.database.repositories.profile_repository import ProfileRepository
from src.database.repositories.recommendation_repository import RecommendationRepository
from src.database.connection import get_db_session
from src.observability.tracing import tracer
from src.observability.logging import logger


class MeasurementService:
    """Service for tracking and analyzing optimization performance impact."""

    def __init__(self):
        pass

    def record_before_metrics(
        self,
        recommendation_id: int,
        job_id: str,
        measured_by: Optional[str] = "system"
    ) -> Dict[str, Any]:
        """
        Record baseline metrics before optimization is implemented.

        Args:
            recommendation_id: ID of the recommendation being measured
            job_id: Original query job ID (before optimization)
            measured_by: User or system recording the measurement

        Returns:
            Created measurement record
        """
        with tracer.start_as_current_span("measurement.record_before") as span:
            span.set_attribute("recommendation_id", recommendation_id)
            span.set_attribute("job_id", job_id)

            with get_db_session() as session:
                # Fetch query and profile
                query_repo = QueryRepository(session)
                profile_repo = ProfileRepository(session)

                query = query_repo.get_by_job_id(job_id)
                if not query:
                    raise ValueError(f"Query not found: {job_id}")

                profile = profile_repo.get_by_job_id(job_id)

                # Extract metrics
                before_metrics = self._extract_metrics(query, profile)

                # Create measurement
                measurement_repo = MeasurementRepository(session)
                measurement = measurement_repo.create({
                    "recommendation_id": recommendation_id,
                    "job_id_before": job_id,
                    "before_duration_ms": before_metrics["duration_ms"],
                    "before_memory_mb": before_metrics.get("memory_mb"),
                    "before_data_scanned_mb": before_metrics.get("data_scanned_mb"),
                    "before_rows_scanned": before_metrics.get("rows_scanned"),
                    "before_rows_returned": before_metrics.get("rows_returned"),
                    "before_partitions_scanned": before_metrics.get("partitions_scanned"),
                    "before_cpu_time_ms": before_metrics.get("cpu_time_ms"),
                    "measured_at": datetime.utcnow(),
                    "measured_by": measured_by
                })

                session.commit()

                logger.info(
                    "Recorded before metrics",
                    recommendation_id=recommendation_id,
                    duration_ms=before_metrics["duration_ms"]
                )

                return measurement.to_dict()

    def record_after_metrics(
        self,
        recommendation_id: int,
        job_id_after: str,
        measured_by: Optional[str] = "system"
    ) -> Dict[str, Any]:
        """
        Record metrics after optimization is implemented and calculate improvements.

        Args:
            recommendation_id: ID of the recommendation being measured
            job_id_after: Optimized query job ID (after optimization)
            measured_by: User or system recording the measurement

        Returns:
            Updated measurement record with calculated improvements
        """
        with tracer.start_as_current_span("measurement.record_after") as span:
            span.set_attribute("recommendation_id", recommendation_id)
            span.set_attribute("job_id_after", job_id_after)

            with get_db_session() as session:
                measurement_repo = MeasurementRepository(session)
                query_repo = QueryRepository(session)
                profile_repo = ProfileRepository(session)
                recommendation_repo = RecommendationRepository(session)

                # Get existing measurement
                measurement = measurement_repo.get_by_recommendation(recommendation_id)
                if not measurement:
                    raise ValueError(f"No before metrics found for recommendation {recommendation_id}")

                # Fetch optimized query and profile
                query = query_repo.get_by_job_id(job_id_after)
                if not query:
                    raise ValueError(f"Query not found: {job_id_after}")

                profile = profile_repo.get_by_job_id(job_id_after)

                # Extract after metrics
                after_metrics = self._extract_metrics(query, profile)

                # Calculate improvements
                improvements = self._calculate_improvements(
                    before={
                        "duration_ms": measurement.before_duration_ms,
                        "memory_mb": measurement.before_memory_mb,
                        "data_scanned_mb": measurement.before_data_scanned_mb,
                        "cpu_time_ms": measurement.before_cpu_time_ms
                    },
                    after=after_metrics
                )

                # Get estimated improvement for validation
                recommendation = recommendation_repo.get_by_id(recommendation_id)
                estimated_improvement = recommendation.estimated_improvement_pct or 0

                meets_expectation, delta = self._validate_expectation(
                    estimated=estimated_improvement,
                    actual=improvements["duration_improvement_pct"]
                )

                # Update measurement
                measurement.job_id_after = job_id_after
                measurement.after_duration_ms = after_metrics["duration_ms"]
                measurement.after_memory_mb = after_metrics.get("memory_mb")
                measurement.after_data_scanned_mb = after_metrics.get("data_scanned_mb")
                measurement.after_rows_scanned = after_metrics.get("rows_scanned")
                measurement.after_rows_returned = after_metrics.get("rows_returned")
                measurement.after_partitions_scanned = after_metrics.get("partitions_scanned")
                measurement.after_cpu_time_ms = after_metrics.get("cpu_time_ms")
                measurement.duration_improvement_pct = improvements["duration_improvement_pct"]
                measurement.memory_reduction_pct = improvements.get("memory_reduction_pct")
                measurement.scan_reduction_pct = improvements.get("scan_reduction_pct")
                measurement.cpu_reduction_pct = improvements.get("cpu_reduction_pct")
                measurement.meets_expectation = meets_expectation
                measurement.expectation_delta_pct = delta
                measurement.measured_by = measured_by

                session.commit()

                logger.info(
                    "Recorded after metrics",
                    recommendation_id=recommendation_id,
                    improvement_pct=improvements["duration_improvement_pct"],
                    meets_expectation=meets_expectation
                )

                span.set_attribute("improvement_pct", improvements["duration_improvement_pct"])
                span.set_attribute("meets_expectation", meets_expectation)

                return measurement.to_dict()

    def get_measurement(self, recommendation_id: int) -> Optional[Dict[str, Any]]:
        """
        Retrieve measurement for a recommendation.

        Args:
            recommendation_id: Recommendation ID

        Returns:
            Measurement record or None
        """
        with get_db_session() as session:
            repo = MeasurementRepository(session)
            measurement = repo.get_by_recommendation(recommendation_id)
            return measurement.to_dict() if measurement else None

    def get_summary_metrics(self, days: int = 30) -> Dict[str, Any]:
        """
        Get summary metrics for all measurements in the last N days.

        Args:
            days: Lookback period in days

        Returns:
            Summary statistics
        """
        with get_db_session() as session:
            repo = MeasurementRepository(session)
            measurements = repo.get_recent(days=days)

            if not measurements:
                return {
                    "total_measurements": 0,
                    "avg_improvement_pct": 0,
                    "success_rate_pct": 0
                }

            completed = [m for m in measurements if m.job_id_after is not None]

            if not completed:
                return {
                    "total_measurements": len(measurements),
                    "completed_measurements": 0,
                    "avg_improvement_pct": 0,
                    "success_rate_pct": 0
                }

            # Calculate statistics
            avg_improvement = sum(m.duration_improvement_pct or 0 for m in completed) / len(completed)
            met_expectations = sum(1 for m in completed if m.meets_expectation)
            success_rate = (met_expectations / len(completed)) * 100

            # Calculate total time saved
            total_time_saved_ms = sum(
                m.before_duration_ms - m.after_duration_ms
                for m in completed
                if m.before_duration_ms and m.after_duration_ms
            )

            return {
                "total_measurements": len(measurements),
                "completed_measurements": len(completed),
                "avg_improvement_pct": round(avg_improvement, 1),
                "success_rate_pct": round(success_rate, 1),
                "total_time_saved_seconds": round(total_time_saved_ms / 1000, 1),
                "met_expectations_count": met_expectations,
                "exceeded_expectations_count": sum(
                    1 for m in completed if m.expectation_delta_pct and m.expectation_delta_pct > 10
                ),
                "underperformed_count": sum(
                    1 for m in completed if not m.meets_expectation
                )
            }

    def _extract_metrics(self, query, profile) -> Dict[str, Any]:
        """Extract metrics from query and profile objects."""
        metrics = {
            "duration_ms": query.duration_ms
        }

        if profile:
            metrics.update({
                "memory_mb": profile.memory_allocated / (1024 * 1024) if profile.memory_allocated else None,
                "data_scanned_mb": profile.data_scanned / (1024 * 1024) if profile.data_scanned else None,
                "rows_scanned": profile.rows_scanned,
                "rows_returned": profile.rows_returned,
                "partitions_scanned": profile.partitions_scanned,
                "cpu_time_ms": profile.cpu_time_ms
            })

        return metrics

    def _calculate_improvements(
        self,
        before: Dict[str, Any],
        after: Dict[str, Any]
    ) -> Dict[str, float]:
        """Calculate percentage improvements."""
        improvements = {}

        # Duration improvement
        if before["duration_ms"] > 0:
            improvements["duration_improvement_pct"] = (
                (before["duration_ms"] - after["duration_ms"]) / before["duration_ms"]
            ) * 100

        # Memory reduction
        if before.get("memory_mb") and after.get("memory_mb") and before["memory_mb"] > 0:
            improvements["memory_reduction_pct"] = (
                (before["memory_mb"] - after["memory_mb"]) / before["memory_mb"]
            ) * 100

        # Data scan reduction
        if before.get("data_scanned_mb") and after.get("data_scanned_mb") and before["data_scanned_mb"] > 0:
            improvements["scan_reduction_pct"] = (
                (before["data_scanned_mb"] - after["data_scanned_mb"]) / before["data_scanned_mb"]
            ) * 100

        # CPU reduction
        if before.get("cpu_time_ms") and after.get("cpu_time_ms") and before["cpu_time_ms"] > 0:
            improvements["cpu_reduction_pct"] = (
                (before["cpu_time_ms"] - after["cpu_time_ms"]) / before["cpu_time_ms"]
            ) * 100

        return improvements

    def _validate_expectation(
        self,
        estimated: float,
        actual: float,
        tolerance_pct: float = 20.0
    ) -> tuple[bool, float]:
        """
        Validate if actual improvement meets estimated improvement.

        Args:
            estimated: Estimated improvement percentage
            actual: Actual improvement percentage
            tolerance_pct: Acceptable tolerance (default 20%)

        Returns:
            (meets_expectation, delta_pct)
        """
        delta = actual - estimated

        # Meets expectation if within tolerance or better
        meets_expectation = actual >= (estimated - tolerance_pct)

        return meets_expectation, round(delta, 1)
```

---

## Component 3: Measurement Repository

### File: `src/database/repositories/measurement_repository.py`

```python
from typing import List, Optional
from datetime import datetime, timedelta
from sqlalchemy.orm import Session
from src.database.models import Measurement
from src.database.repositories.base_repository import BaseRepository


class MeasurementRepository(BaseRepository[Measurement]):
    """Repository for measurement operations."""

    def __init__(self, session: Session):
        super().__init__(Measurement, session)

    def get_by_recommendation(self, recommendation_id: int) -> Optional[Measurement]:
        """Get measurement by recommendation ID."""
        return self.session.query(Measurement).filter(
            Measurement.recommendation_id == recommendation_id
        ).first()

    def get_recent(self, days: int = 30) -> List[Measurement]:
        """Get measurements from last N days."""
        cutoff = datetime.utcnow() - timedelta(days=days)
        return self.session.query(Measurement).filter(
            Measurement.measured_at >= cutoff
        ).all()

    def get_successful(self, days: int = 30) -> List[Measurement]:
        """Get successful measurements (met or exceeded expectations)."""
        cutoff = datetime.utcnow() - timedelta(days=days)
        return self.session.query(Measurement).filter(
            Measurement.measured_at >= cutoff,
            Measurement.meets_expectation == True,
            Measurement.job_id_after.isnot(None)
        ).all()

    def get_by_issue_type(self, issue_type: str, days: int = 30) -> List[Measurement]:
        """Get measurements for specific issue type."""
        cutoff = datetime.utcnow() - timedelta(days=days)
        return self.session.query(Measurement).join(
            Measurement.recommendation
        ).filter(
            Measurement.measured_at >= cutoff,
            Measurement.recommendation.issue_type == issue_type
        ).all()
```

---

## Component 4: Measurement API Endpoints

### File: `src/api/routes/measurements.py`

```python
from fastapi import APIRouter, Depends, HTTPException
from typing import Optional
from src.services.measurement_service import MeasurementService
from src.api.schemas.measurement_schema import (
    MeasurementRecordRequest,
    MeasurementResponse,
    MeasurementSummaryResponse
)

router = APIRouter(prefix="/api/v1/measurements", tags=["measurements"])


@router.post("/before")
def record_before_metrics(request: MeasurementRecordRequest) -> MeasurementResponse:
    """
    Record baseline metrics before optimization.

    Records the performance metrics of the original query before any optimization
    is applied. This establishes the baseline for comparison.
    """
    service = MeasurementService()

    try:
        measurement = service.record_before_metrics(
            recommendation_id=request.recommendation_id,
            job_id=request.job_id,
            measured_by=request.measured_by
        )
        return MeasurementResponse(**measurement)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))


@router.post("/after")
def record_after_metrics(request: MeasurementRecordRequest) -> MeasurementResponse:
    """
    Record metrics after optimization and calculate improvements.

    Records the performance metrics of the optimized query and calculates the
    actual improvement compared to the baseline.
    """
    service = MeasurementService()

    try:
        measurement = service.record_after_metrics(
            recommendation_id=request.recommendation_id,
            job_id_after=request.job_id,
            measured_by=request.measured_by
        )
        return MeasurementResponse(**measurement)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))


@router.get("/{recommendation_id}")
def get_measurement(recommendation_id: int) -> MeasurementResponse:
    """Get measurement for a specific recommendation."""
    service = MeasurementService()
    measurement = service.get_measurement(recommendation_id)

    if not measurement:
        raise HTTPException(status_code=404, detail="Measurement not found")

    return MeasurementResponse(**measurement)


@router.get("/summary/metrics")
def get_summary_metrics(days: int = 30) -> MeasurementSummaryResponse:
    """
    Get summary metrics for all measurements.

    Returns aggregate statistics including average improvement,
    success rate, and total time saved.
    """
    service = MeasurementService()
    summary = service.get_summary_metrics(days=days)
    return MeasurementSummaryResponse(**summary)
```

---

## Component 5: Measurement Schemas

### File: `src/api/schemas/measurement_schema.py`

```python
from pydantic import BaseModel
from typing import Optional
from datetime import datetime


class MeasurementRecordRequest(BaseModel):
    """Request to record measurement."""
    recommendation_id: int
    job_id: str
    measured_by: Optional[str] = "system"


class MeasurementResponse(BaseModel):
    """Measurement response with all metrics."""
    id: int
    recommendation_id: int
    job_id_before: str
    job_id_after: Optional[str]

    # Before metrics
    before_duration_ms: int
    before_memory_mb: Optional[int]
    before_data_scanned_mb: Optional[int]

    # After metrics
    after_duration_ms: Optional[int]
    after_memory_mb: Optional[int]
    after_data_scanned_mb: Optional[int]

    # Improvements
    duration_improvement_pct: Optional[float]
    memory_reduction_pct: Optional[float]
    scan_reduction_pct: Optional[float]

    # Validation
    meets_expectation: Optional[bool]
    expectation_delta_pct: Optional[float]

    measured_at: datetime


class MeasurementSummaryResponse(BaseModel):
    """Summary statistics for measurements."""
    total_measurements: int
    completed_measurements: int
    avg_improvement_pct: float
    success_rate_pct: float
    total_time_saved_seconds: float
    met_expectations_count: int
    exceeded_expectations_count: int
    underperformed_count: int
```

---

## Testing Strategy

### Unit Tests

```python
def test_calculate_improvements():
    """Test improvement calculation logic."""
    service = MeasurementService()

    before = {"duration_ms": 60000, "memory_mb": 1000}
    after = {"duration_ms": 12000, "memory_mb": 400}

    improvements = service._calculate_improvements(before, after)

    assert improvements["duration_improvement_pct"] == 80.0
    assert improvements["memory_reduction_pct"] == 60.0


def test_validate_expectation_met():
    """Test expectation validation when met."""
    service = MeasurementService()

    meets, delta = service._validate_expectation(estimated=70, actual=75)

    assert meets is True
    assert delta == 5.0


def test_validate_expectation_not_met():
    """Test expectation validation when not met."""
    service = MeasurementService()

    meets, delta = service._validate_expectation(estimated=70, actual=40)

    assert meets is False
    assert delta == -30.0
```

---

## Success Criteria

- ✅ Before/after metrics tracked for all recommendations
- ✅ Improvements calculated accurately (±5% precision)
- ✅ 80%+ of optimizations meet or exceed estimated improvements
- ✅ Summary metrics available via API
- ✅ End-to-end measurement workflow <5 seconds
- ✅ Test coverage >90%

---

## Next Steps After Phase 4

Once Phase 4 is complete, proceed to:
- **Phase 5**: REST API (comprehensive API for all services)
- **Phase 6**: Observability (monitoring and alerting)
