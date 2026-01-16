"""Repository for Query model."""
from typing import List, Optional
from sqlalchemy.orm import Session
from sqlalchemy import desc
from ..models import Query
from .base_repository import BaseRepository


class QueryRepository(BaseRepository[Query]):
    """Repository for Query operations."""

    def __init__(self, session: Session):
        super().__init__(Query, session)

    def get_by_job_id(self, job_id: str) -> Optional[Query]:
        """Get query by job_id."""
        return self.session.query(Query).filter(Query.job_id == job_id).first()

    def get_recent(self, limit: int = 100) -> List[Query]:
        """Get recent queries ordered by start_time."""
        return self.session.query(Query).order_by(desc(Query.start_time)).limit(limit).all()

    def get_slow_queries(self, threshold_ms: int = 10000, limit: int = 100) -> List[Query]:
        """Get slow queries above threshold."""
        return (
            self.session.query(Query)
            .filter(Query.duration_ms > threshold_ms)
            .order_by(desc(Query.duration_ms))
            .limit(limit)
            .all()
        )

    def get_by_user(self, user: str, limit: int = 100) -> List[Query]:
        """Get queries by user."""
        return self.session.query(Query).filter(Query.user == user).order_by(desc(Query.start_time)).limit(limit).all()

    def insert_from_dict(self, query_data: dict) -> Query:
        """Insert query from dictionary."""
        query = Query(**query_data)
        return self.insert(query)

    def bulk_insert_from_dicts(self, queries_data: List[dict]) -> int:
        """Bulk insert queries from dictionaries."""
        queries = [Query(**q) for q in queries_data]
        return self.bulk_insert(queries)
