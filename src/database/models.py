"""SQLAlchemy ORM models for optimization data."""
from sqlalchemy import Column, String, Integer, Float, DateTime, Text, JSON, ForeignKey, Index, Boolean
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship
from datetime import datetime

Base = declarative_base()


class Query(Base):
    """Query history table."""

    __tablename__ = "queries"

    id = Column(Integer, primary_key=True)
    job_id = Column(String(255), unique=True, nullable=False, index=True)
    sql_text = Column(Text, nullable=False)
    user = Column(String(255))
    queue_name = Column(String(255))
    start_time = Column(DateTime, index=True)
    end_time = Column(DateTime)
    duration_ms = Column(Integer)
    status = Column(String(50))
    created_at = Column(DateTime, default=datetime.utcnow)

    # Relationships
    profile = relationship("QueryProfile", back_populates="query", uselist=False)
    recommendations = relationship("Recommendation", back_populates="query")

    __table_args__ = (Index("idx_queries_time", "start_time", "duration_ms"),)

    def to_dict(self):
        """Convert to dictionary."""
        return {
            "id": self.id,
            "job_id": self.job_id,
            "sql_text": self.sql_text,
            "user": self.user,
            "queue_name": self.queue_name,
            "start_time": self.start_time.isoformat() if self.start_time else None,
            "end_time": self.end_time.isoformat() if self.end_time else None,
            "duration_ms": self.duration_ms,
            "status": self.status,
        }


class QueryProfile(Base):
    """Query execution profile and plan."""

    __tablename__ = "query_profiles"

    id = Column(Integer, primary_key=True)
    job_id = Column(String(255), ForeignKey("queries.job_id"), nullable=False, unique=True)
    profile_json = Column(JSON)  # Full profile JSON
    plan_json = Column(JSON)  # Query plan JSON

    # Extracted metrics
    total_memory_mb = Column(Float)
    peak_memory_mb = Column(Float)
    rows_scanned = Column(Integer)
    rows_returned = Column(Integer)
    data_scanned_mb = Column(Float)

    # Reflection usage
    reflection_used = Column(String(255))
    reflection_hit = Column(Boolean, default=False)

    # Partition info
    partitions_pruned = Column(Integer)
    partitions_scanned = Column(Integer)

    created_at = Column(DateTime, default=datetime.utcnow)

    # Relationships
    query = relationship("Query", back_populates="profile")

    def to_dict(self):
        """Convert to dictionary."""
        return {
            "id": self.id,
            "job_id": self.job_id,
            "profile_json": self.profile_json,
            "plan_json": self.plan_json,
            "total_memory_mb": self.total_memory_mb,
            "peak_memory_mb": self.peak_memory_mb,
            "rows_scanned": self.rows_scanned,
            "rows_returned": self.rows_returned,
            "data_scanned_mb": self.data_scanned_mb,
            "reflection_used": self.reflection_used,
            "reflection_hit": self.reflection_hit,
            "partitions_pruned": self.partitions_pruned,
            "partitions_scanned": self.partitions_scanned,
        }


class Baseline(Base):
    """Performance baseline for queries."""

    __tablename__ = "baselines"

    id = Column(Integer, primary_key=True)
    query_signature = Column(String(64), unique=True, nullable=False, index=True)  # Hash of normalized SQL

    # Baseline metrics (median over time window)
    baseline_duration_ms = Column(Integer)
    baseline_memory_mb = Column(Float)
    baseline_rows_scanned = Column(Integer)
    baseline_data_scanned_mb = Column(Float)

    # Statistical bounds
    p50_duration_ms = Column(Integer)
    p95_duration_ms = Column(Integer)
    p99_duration_ms = Column(Integer)

    sample_size = Column(Integer)
    first_seen = Column(DateTime)
    last_updated = Column(DateTime, default=datetime.utcnow)

    def to_dict(self):
        """Convert to dictionary."""
        return {
            "id": self.id,
            "query_signature": self.query_signature,
            "baseline_duration_ms": self.baseline_duration_ms,
            "baseline_memory_mb": self.baseline_memory_mb,
            "baseline_rows_scanned": self.baseline_rows_scanned,
            "baseline_data_scanned_mb": self.baseline_data_scanned_mb,
            "p50_duration_ms": self.p50_duration_ms,
            "p95_duration_ms": self.p95_duration_ms,
            "p99_duration_ms": self.p99_duration_ms,
            "sample_size": self.sample_size,
            "first_seen": self.first_seen.isoformat() if self.first_seen else None,
            "last_updated": self.last_updated.isoformat() if self.last_updated else None,
        }


class Recommendation(Base):
    """Optimization recommendations."""

    __tablename__ = "recommendations"

    id = Column(Integer, primary_key=True)
    job_id = Column(String(255), ForeignKey("queries.job_id"), index=True)

    # Recommendation details
    issue_type = Column(String(100), nullable=False)  # e.g., "partition_pruning", "reflection_missing"
    severity = Column(String(20))  # "high", "medium", "low"
    title = Column(String(255))
    description = Column(Text)
    recommendation_text = Column(Text)

    # Impact estimates
    estimated_improvement_pct = Column(Float)
    estimated_cost_savings = Column(Float)

    # Implementation
    is_auto_applicable = Column(Boolean, default=False)
    sql_rewrite = Column(Text)  # Optional SQL rewrite suggestion
    action_items = Column(JSON)  # List of action items

    # Status tracking
    status = Column(String(50), default="pending")  # pending, accepted, rejected, implemented
    created_at = Column(DateTime, default=datetime.utcnow)
    implemented_at = Column(DateTime)

    # Relationships
    query = relationship("Query", back_populates="recommendations")
    measurement = relationship("Measurement", back_populates="recommendation", uselist=False)

    def to_dict(self):
        """Convert to dictionary."""
        return {
            "id": self.id,
            "job_id": self.job_id,
            "issue_type": self.issue_type,
            "severity": self.severity,
            "title": self.title,
            "description": self.description,
            "recommendation_text": self.recommendation_text,
            "estimated_improvement_pct": self.estimated_improvement_pct,
            "estimated_cost_savings": self.estimated_cost_savings,
            "is_auto_applicable": self.is_auto_applicable,
            "sql_rewrite": self.sql_rewrite,
            "action_items": self.action_items,
            "status": self.status,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "implemented_at": self.implemented_at.isoformat() if self.implemented_at else None,
        }


class Measurement(Base):
    """Before/after performance measurements."""

    __tablename__ = "measurements"

    id = Column(Integer, primary_key=True)
    recommendation_id = Column(Integer, ForeignKey("recommendations.id"), unique=True)

    # Before metrics
    before_duration_ms = Column(Integer)
    before_memory_mb = Column(Float)
    before_data_scanned_mb = Column(Float)

    # After metrics
    after_duration_ms = Column(Integer)
    after_memory_mb = Column(Float)
    after_data_scanned_mb = Column(Float)

    # Actual improvements
    improvement_pct = Column(Float)
    memory_reduction_pct = Column(Float)
    scan_reduction_pct = Column(Float)

    measured_at = Column(DateTime, default=datetime.utcnow)

    # Relationships
    recommendation = relationship("Recommendation", back_populates="measurement")

    def to_dict(self):
        """Convert to dictionary."""
        return {
            "id": self.id,
            "recommendation_id": self.recommendation_id,
            "before_duration_ms": self.before_duration_ms,
            "before_memory_mb": self.before_memory_mb,
            "before_data_scanned_mb": self.before_data_scanned_mb,
            "after_duration_ms": self.after_duration_ms,
            "after_memory_mb": self.after_memory_mb,
            "after_data_scanned_mb": self.after_data_scanned_mb,
            "improvement_pct": self.improvement_pct,
            "memory_reduction_pct": self.memory_reduction_pct,
            "scan_reduction_pct": self.scan_reduction_pct,
            "measured_at": self.measured_at.isoformat() if self.measured_at else None,
        }


class ReflectionMetadata(Base):
    """Dremio reflection metadata."""

    __tablename__ = "reflection_metadata"

    id = Column(Integer, primary_key=True)
    reflection_id = Column(String(255), unique=True, nullable=False)
    reflection_name = Column(String(255))
    reflection_type = Column(String(50))  # "aggregation", "raw"
    dataset_id = Column(String(255))
    dataset_path = Column(String(500))

    # Usage stats
    hit_count = Column(Integer, default=0)
    last_used = Column(DateTime)

    # Refresh info
    refresh_frequency = Column(String(50))
    last_refresh = Column(DateTime)
    size_mb = Column(Float)

    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    def to_dict(self):
        """Convert to dictionary."""
        return {
            "id": self.id,
            "reflection_id": self.reflection_id,
            "reflection_name": self.reflection_name,
            "reflection_type": self.reflection_type,
            "dataset_id": self.dataset_id,
            "dataset_path": self.dataset_path,
            "hit_count": self.hit_count,
            "last_used": self.last_used.isoformat() if self.last_used else None,
            "refresh_frequency": self.refresh_frequency,
            "last_refresh": self.last_refresh.isoformat() if self.last_refresh else None,
            "size_mb": self.size_mb,
        }


class DatasetMetadata(Base):
    """Table/dataset metadata."""

    __tablename__ = "dataset_metadata"

    id = Column(Integer, primary_key=True)
    dataset_id = Column(String(255), unique=True, nullable=False)
    dataset_path = Column(String(500))
    dataset_type = Column(String(50))  # "physical", "virtual"

    # Schema info
    columns = Column(JSON)
    partition_columns = Column(JSON)
    sort_columns = Column(JSON)

    # Storage info
    file_format = Column(String(50))
    total_size_mb = Column(Float)
    row_count = Column(Integer)
    file_count = Column(Integer)

    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    def to_dict(self):
        """Convert to dictionary."""
        return {
            "id": self.id,
            "dataset_id": self.dataset_id,
            "dataset_path": self.dataset_path,
            "dataset_type": self.dataset_type,
            "columns": self.columns,
            "partition_columns": self.partition_columns,
            "sort_columns": self.sort_columns,
            "file_format": self.file_format,
            "total_size_mb": self.total_size_mb,
            "row_count": self.row_count,
            "file_count": self.file_count,
        }
