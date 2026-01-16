"""Repository for Recommendation model."""
from typing import List, Optional
from sqlalchemy.orm import Session
from sqlalchemy import desc
from ..models import Recommendation
from .base_repository import BaseRepository


class RecommendationRepository(BaseRepository[Recommendation]):
    """Repository for Recommendation operations."""

    def __init__(self, session: Session):
        super().__init__(Recommendation, session)

    def get_by_job_id(self, job_id: str) -> List[Recommendation]:
        """Get recommendations by job_id."""
        return self.session.query(Recommendation).filter(Recommendation.job_id == job_id).all()

    def get_by_status(self, status: str, limit: int = 100) -> List[Recommendation]:
        """Get recommendations by status."""
        return (
            self.session.query(Recommendation)
            .filter(Recommendation.status == status)
            .order_by(desc(Recommendation.created_at))
            .limit(limit)
            .all()
        )

    def get_by_severity(self, severity: str, limit: int = 100) -> List[Recommendation]:
        """Get recommendations by severity."""
        return (
            self.session.query(Recommendation)
            .filter(Recommendation.severity == severity)
            .order_by(desc(Recommendation.estimated_improvement_pct))
            .limit(limit)
            .all()
        )

    def update_status(self, recommendation_id: int, status: str) -> Optional[Recommendation]:
        """Update recommendation status."""
        recommendation = self.get_by_id(recommendation_id)
        if recommendation:
            recommendation.status = status
            return self.update(recommendation)
        return None

    def insert_from_dict(self, recommendation_data: dict) -> Recommendation:
        """Insert recommendation from dictionary."""
        recommendation = Recommendation(**recommendation_data)
        return self.insert(recommendation)
