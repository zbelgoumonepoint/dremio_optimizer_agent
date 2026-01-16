# Phase 2: Analysis Engine

**Duration**: 1-2 weeks
**Status**: Not Started
**Dependencies**: Phase 1 (Complete)
**Priority**: High

---

## Overview

Build a comprehensive detection system that analyzes Dremio queries and identifies performance issues, anti-patterns, and optimization opportunities.

## Objectives

1. Create reusable detector framework
2. Implement 6+ specialized detectors
3. Build baseline calculation system
4. Create analysis orchestration service
5. Achieve 80%+ test coverage

---

## Architecture

```
src/analysis/
├── detectors/
│   ├── __init__.py
│   ├── base_detector.py              # Base classes
│   ├── partition_pruning_detector.py # Detector 1
│   ├── reflection_detector.py        # Detector 2
│   ├── join_fanout_detector.py       # Detector 3
│   ├── select_star_detector.py       # Detector 4
│   ├── small_file_detector.py        # Detector 5
│   └── regression_detector.py        # Detector 6
├── metrics/
│   ├── __init__.py
│   └── baseline_calculator.py        # Baseline system
└── services/
    ├── __init__.py
    └── analysis_service.py            # Orchestration
```

---

## Component 1: Detector Framework

### 1.1 Detection Result Model

```python
# src/analysis/detectors/base_detector.py

from dataclasses import dataclass
from enum import Enum
from typing import Dict, Any, Optional

class IssueSeverity(str, Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"

class IssueType(str, Enum):
    PARTITION_PRUNING = "partition_pruning"
    REFLECTION_MISSING = "reflection_missing"
    REFLECTION_UNUSED = "reflection_unused"
    JOIN_FANOUT = "join_fanout"
    SELECT_STAR = "select_star"
    SMALL_FILES = "small_files"
    REGRESSION = "regression"

@dataclass
class DetectionResult:
    """Result from a detector."""
    issue_type: IssueType
    severity: IssueSeverity
    title: str
    description: str
    evidence: Dict[str, Any]
    recommendation: str
    estimated_improvement_pct: Optional[float] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "issue_type": self.issue_type.value,
            "severity": self.severity.value,
            "title": self.title,
            "description": self.description,
            "evidence": self.evidence,
            "recommendation": self.recommendation,
            "estimated_improvement_pct": self.estimated_improvement_pct,
        }
```

### 1.2 Base Detector Class

```python
from abc import ABC, abstractmethod
from typing import List, Optional
from src.database.models import Query, QueryProfile

class BaseDetector(ABC):
    """Base class for all detectors."""

    @property
    @abstractmethod
    def name(self) -> str:
        """Detector name."""
        pass

    @property
    @abstractmethod
    def description(self) -> str:
        """Detector description."""
        pass

    @abstractmethod
    def analyze(self, query: Query, profile: Optional[QueryProfile] = None) -> List[DetectionResult]:
        """Analyze a query and return detected issues."""
        pass

    def _should_analyze(self, query: Query) -> bool:
        """Check if this query should be analyzed."""
        # Skip system queries, DDL, etc.
        if not query.sql_text:
            return False

        sql_upper = query.sql_text.upper().strip()

        # Skip DDL
        if any(sql_upper.startswith(cmd) for cmd in ["CREATE", "DROP", "ALTER"]):
            return False

        return True
```

**Deliverables**:
- [ ] `IssueSeverity` enum
- [ ] `IssueType` enum
- [ ] `DetectionResult` dataclass
- [ ] `BaseDetector` abstract class
- [ ] Unit tests

---

## Component 2: Six Core Detectors

### 2.1 PartitionPruningDetector

**Purpose**: Detect queries scanning too many partitions

**Logic**:
1. Parse query profile for partition statistics
2. Check if `partitions_scanned` > threshold (e.g., 1000)
3. Analyze WHERE clause for partition column filters
4. Recommend adding/improving partition filters

**Evidence**:
- Partitions scanned
- Partition column(s)
- Current WHERE clause
- Dataset path

**Implementation**:
```python
class PartitionPruningDetector(BaseDetector):
    def __init__(self, threshold: int = 1000):
        self.threshold = threshold

    def analyze(self, query: Query, profile: Optional[QueryProfile] = None) -> List[DetectionResult]:
        if not profile or not self._should_analyze(query):
            return []

        results = []
        partitions_scanned = profile.metrics.get("partitions_scanned", 0)

        if partitions_scanned > self.threshold:
            results.append(DetectionResult(
                issue_type=IssueType.PARTITION_PRUNING,
                severity=IssueSeverity.HIGH,
                title=f"Excessive partition scanning ({partitions_scanned} partitions)",
                description=f"Query scanned {partitions_scanned} partitions, exceeding threshold of {self.threshold}",
                evidence={
                    "partitions_scanned": partitions_scanned,
                    "threshold": self.threshold,
                    "sql": query.sql_text[:500],
                },
                recommendation="Add WHERE clause filter on partition column to reduce partition scanning",
                estimated_improvement_pct=30.0,
            ))

        return results
```

**Deliverables**:
- [ ] Detector implementation
- [ ] Unit tests with mock data
- [ ] Integration test with real profile

---

### 2.2 ReflectionDetector

**Purpose**: Detect reflection issues (unused or missing)

**Logic**:
1. Check if query used any reflections (`accelerated` flag)
2. If not accelerated, check if suitable reflection exists
3. If accelerated, check reflection utilization stats
4. Identify unused reflections consuming resources

**Evidence**:
- Reflection usage flag
- Available reflections
- Reflection utilization stats
- Dataset path

**Implementation**:
```python
class ReflectionDetector(BaseDetector):
    def analyze(self, query: Query, profile: Optional[QueryProfile] = None) -> List[DetectionResult]:
        results = []

        # Check if query should have used reflection but didn't
        if not query.accelerated and query.duration_ms > 5000:
            # Check if reflection exists for this dataset
            # (In real implementation, query reflection metadata)
            results.append(DetectionResult(
                issue_type=IssueType.REFLECTION_MISSING,
                severity=IssueSeverity.MEDIUM,
                title="Query could benefit from reflection",
                description=f"Slow query ({query.duration_ms}ms) without reflection acceleration",
                evidence={
                    "duration_ms": query.duration_ms,
                    "accelerated": False,
                    "dataset": "...",
                },
                recommendation="Create reflection on frequently queried columns",
                estimated_improvement_pct=50.0,
            ))

        return results
```

**Deliverables**:
- [ ] Detector implementation
- [ ] Logic for both missing and unused reflections
- [ ] Unit tests
- [ ] Integration with reflection metadata

---

### 2.3 JoinFanoutDetector

**Purpose**: Detect join operations with high row multiplication

**Logic**:
1. Parse query profile operator tree
2. Find JOIN operators
3. Check `rows_in` vs `rows_out` ratio
4. If ratio > threshold (e.g., 10x), flag as fanout
5. Analyze join conditions and filters

**Evidence**:
- Join operator details
- Row counts (in/out)
- Fanout ratio
- Join condition

**Implementation**:
```python
class JoinFanoutDetector(BaseDetector):
    def __init__(self, fanout_threshold: float = 10.0):
        self.fanout_threshold = fanout_threshold

    def analyze(self, query: Query, profile: Optional[QueryProfile] = None) -> List[DetectionResult]:
        if not profile or not profile.operator_tree:
            return []

        results = []

        # Parse operator tree for joins
        for operator in self._find_join_operators(profile.operator_tree):
            rows_in = operator.get("rows_input", 0)
            rows_out = operator.get("rows_output", 0)

            if rows_in > 0:
                fanout_ratio = rows_out / rows_in

                if fanout_ratio > self.fanout_threshold:
                    results.append(DetectionResult(
                        issue_type=IssueType.JOIN_FANOUT,
                        severity=IssueSeverity.HIGH,
                        title=f"Join fanout detected ({fanout_ratio:.1f}x multiplication)",
                        description=f"Join operation multiplied rows by {fanout_ratio:.1f}x",
                        evidence={
                            "rows_in": rows_in,
                            "rows_out": rows_out,
                            "fanout_ratio": fanout_ratio,
                            "join_type": operator.get("type"),
                        },
                        recommendation="Review join condition and add filters to reduce cardinality",
                        estimated_improvement_pct=40.0,
                    ))

        return results
```

**Deliverables**:
- [ ] Detector implementation
- [ ] Operator tree parsing logic
- [ ] Unit tests
- [ ] Handle different join types

---

### 2.4 SelectStarDetector

**Purpose**: Detect `SELECT *` anti-pattern

**Logic**:
1. Parse SQL and check for `SELECT *`
2. Count total columns in result
3. Estimate unnecessary data transfer
4. Recommend column pruning

**Evidence**:
- SQL text
- Column count
- Estimated bytes transferred
- Dataset path

**Implementation**:
```python
import re

class SelectStarDetector(BaseDetector):
    def analyze(self, query: Query, profile: Optional[QueryProfile] = None) -> List[DetectionResult]:
        if not self._should_analyze(query):
            return []

        results = []
        sql = query.sql_text.upper()

        # Simple regex to detect SELECT *
        if re.search(r'\bSELECT\s+\*\s+FROM', sql):
            results.append(DetectionResult(
                issue_type=IssueType.SELECT_STAR,
                severity=IssueSeverity.LOW,
                title="SELECT * detected",
                description="Query uses SELECT * which may transfer unnecessary columns",
                evidence={
                    "sql": query.sql_text[:500],
                    "duration_ms": query.duration_ms,
                },
                recommendation="Select only the required columns instead of SELECT *",
                estimated_improvement_pct=15.0,
            ))

        return results
```

**Deliverables**:
- [ ] Detector implementation
- [ ] SQL parsing logic
- [ ] Unit tests with various SQL patterns
- [ ] Handle SELECT * with aliases

---

### 2.5 SmallFileDetector

**Purpose**: Detect tables with many small files

**Logic**:
1. Query dataset metadata for file count and sizes
2. If file_count > threshold (e.g., 1000) and avg_size < threshold (e.g., 64MB)
3. Flag for compaction
4. Estimate performance impact

**Evidence**:
- File count
- Average file size
- Total size
- Dataset path

**Implementation**:
```python
class SmallFileDetector(BaseDetector):
    def __init__(self, file_count_threshold: int = 1000, avg_size_mb_threshold: int = 64):
        self.file_count_threshold = file_count_threshold
        self.avg_size_mb_threshold = avg_size_mb_threshold

    def analyze(self, query: Query, profile: Optional[QueryProfile] = None) -> List[DetectionResult]:
        # This detector analyzes datasets, not individual queries
        # Would typically be called separately on dataset metadata
        pass
```

**Deliverables**:
- [ ] Detector implementation
- [ ] Dataset metadata integration
- [ ] Unit tests
- [ ] Batch dataset analysis

---

### 2.6 RegressionDetector

**Purpose**: Detect performance regressions

**Logic**:
1. Get query baseline from database
2. Compare current duration with baseline P95
3. If current > baseline * threshold (e.g., 1.5x), flag as regression
4. Calculate degradation percentage

**Evidence**:
- Current duration
- Baseline P95
- Degradation percentage
- Baseline sample size

**Implementation**:
```python
class RegressionDetector(BaseDetector):
    def __init__(self, threshold_multiplier: float = 1.5):
        self.threshold_multiplier = threshold_multiplier

    def analyze(self, query: Query, profile: Optional[QueryProfile] = None) -> List[DetectionResult]:
        from src.database.repositories.baseline_repository import BaselineRepository

        # Get baseline
        baseline = BaselineRepository.get_by_signature(query.query_signature)
        if not baseline:
            return []  # No baseline to compare against

        results = []

        if query.duration_ms > baseline.p95_duration_ms * self.threshold_multiplier:
            degradation_pct = ((query.duration_ms - baseline.p95_duration_ms) / baseline.p95_duration_ms) * 100

            results.append(DetectionResult(
                issue_type=IssueType.REGRESSION,
                severity=IssueSeverity.CRITICAL,
                title=f"Performance regression detected ({degradation_pct:.1f}% slower)",
                description=f"Query is {degradation_pct:.1f}% slower than baseline P95",
                evidence={
                    "current_duration_ms": query.duration_ms,
                    "baseline_p95_ms": baseline.p95_duration_ms,
                    "degradation_pct": degradation_pct,
                    "baseline_sample_size": baseline.sample_count,
                },
                recommendation="Investigate recent changes to data, schema, or query pattern",
            ))

        return results
```

**Deliverables**:
- [ ] Detector implementation
- [ ] Baseline repository integration
- [ ] Unit tests
- [ ] Handle missing baselines gracefully

---

## Component 3: Baseline System

### 3.1 SQL Normalization

**Purpose**: Generate query signature for grouping similar queries

```python
# src/analysis/metrics/baseline_calculator.py

import re
from typing import Dict, List

class BaselineCalculator:
    """Calculate and manage query baselines."""

    @staticmethod
    def normalize_sql(sql: str) -> str:
        """Normalize SQL by replacing literals with placeholders."""
        # Remove string literals
        sql = re.sub(r"'[^']*'", "'?'", sql)

        # Remove numeric literals
        sql = re.sub(r'\b\d+\b', '?', sql)

        # Normalize whitespace
        sql = ' '.join(sql.split())

        # Uppercase
        sql = sql.upper()

        return sql

    @staticmethod
    def generate_signature(sql: str) -> str:
        """Generate a signature hash for normalized SQL."""
        import hashlib
        normalized = BaselineCalculator.normalize_sql(sql)
        return hashlib.sha256(normalized.encode()).hexdigest()[:16]
```

### 3.2 Baseline Calculation

```python
import statistics
from typing import List
from src.database.models import Query, Baseline

class BaselineCalculator:
    @staticmethod
    def calculate_baseline(queries: List[Query]) -> Dict[str, float]:
        """Calculate baseline metrics from query samples."""
        if not queries:
            return {}

        durations = [q.duration_ms for q in queries if q.duration_ms]

        if not durations:
            return {}

        return {
            "sample_count": len(durations),
            "min_duration_ms": min(durations),
            "max_duration_ms": max(durations),
            "avg_duration_ms": statistics.mean(durations),
            "p50_duration_ms": statistics.median(durations),
            "p95_duration_ms": statistics.quantiles(durations, n=20)[18],  # 95th percentile
            "p99_duration_ms": statistics.quantiles(durations, n=100)[98],  # 99th percentile
        }

    @staticmethod
    def should_refresh_baseline(baseline: Baseline) -> bool:
        """Check if baseline should be refreshed."""
        from datetime import datetime, timedelta

        # Refresh if older than 7 days
        if datetime.utcnow() - baseline.updated_at > timedelta(days=7):
            return True

        # Refresh if sample size too small
        if baseline.sample_count < 20:
            return True

        return False
```

**Deliverables**:
- [ ] SQL normalization logic
- [ ] Signature generation
- [ ] Baseline calculation (P50, P95, P99)
- [ ] Refresh logic
- [ ] Unit tests

---

## Component 4: Analysis Service

### 4.1 Service Implementation

```python
# src/analysis/services/analysis_service.py

from typing import List, Dict, Any
from src.database.models import Query, QueryProfile
from src.analysis.detectors.base_detector import BaseDetector, DetectionResult
from src.analysis.detectors import *

class AnalysisService:
    """Orchestrate analysis across all detectors."""

    def __init__(self):
        self.detectors: List[BaseDetector] = [
            PartitionPruningDetector(),
            ReflectionDetector(),
            JoinFanoutDetector(),
            SelectStarDetector(),
            SmallFileDetector(),
            RegressionDetector(),
        ]

    def analyze_query(self, query: Query, profile: QueryProfile = None) -> List[DetectionResult]:
        """Analyze a single query with all detectors."""
        results = []

        for detector in self.detectors:
            try:
                detector_results = detector.analyze(query, profile)
                results.extend(detector_results)
            except Exception as e:
                # Log error but continue with other detectors
                print(f"Detector {detector.name} failed: {e}")

        return self._prioritize(results)

    def analyze_batch(self, queries: List[Query]) -> Dict[str, List[DetectionResult]]:
        """Analyze a batch of queries."""
        results = {}

        for query in queries:
            # Fetch profile if exists
            profile = None  # TODO: fetch from repository

            query_results = self.analyze_query(query, profile)
            if query_results:
                results[query.job_id] = query_results

        return results

    def _prioritize(self, results: List[DetectionResult]) -> List[DetectionResult]:
        """Prioritize results by severity and estimated improvement."""
        severity_order = {
            "critical": 4,
            "high": 3,
            "medium": 2,
            "low": 1,
        }

        return sorted(
            results,
            key=lambda r: (
                severity_order.get(r.severity.value, 0),
                r.estimated_improvement_pct or 0
            ),
            reverse=True
        )
```

**Deliverables**:
- [ ] Analysis service implementation
- [ ] Detector orchestration
- [ ] Batch analysis support
- [ ] Priority scoring
- [ ] Error handling

---

## Testing Strategy

### Unit Tests
- Test each detector with mock data
- Test baseline calculator with sample durations
- Test SQL normalization with various queries

### Integration Tests
- Test with real Dremio query profiles
- Test analysis service with multiple detectors
- Test baseline creation and refresh

### Test Data
- Create fixture files with sample profiles
- Mock database queries
- Sample SQL queries with known issues

**Test Coverage Goal**: 80%+

---

## Success Criteria

- [ ] All 6 detectors implemented and tested
- [ ] Baseline system calculating P50/P95/P99
- [ ] Analysis service orchestrates all detectors
- [ ] Detects issues on 10 sample queries
- [ ] Unit test coverage > 80%
- [ ] Integration tests pass
- [ ] Documentation complete

---

## Estimated Timeline

**Week 1**:
- Days 1-2: Detector framework
- Days 3-4: Implement 3 detectors
- Day 5: Unit tests

**Week 2**:
- Days 1-2: Implement 3 remaining detectors
- Day 3: Baseline system
- Day 4: Analysis service
- Day 5: Integration tests and documentation

---

## Next Steps

1. Create `src/analysis/detectors/base_detector.py`
2. Implement `BaseDetector` and `DetectionResult`
3. Start with `PartitionPruningDetector`
4. Add unit tests
5. Continue with remaining detectors

---

**Document Version**: 1.0
**Status**: Ready to Start
