"""Repository for Baseline model."""
from typing import Optional
from sqlalchemy.orm import Session
from ..models import Baseline
from .base_repository import BaseRepository


class BaselineRepository(BaseRepository[Baseline]):
    """Repository for Baseline operations."""

    def __init__(self, session: Session):
        super().__init__(Baseline, session)

    def get_by_signature(self, query_signature: str) -> Optional[Baseline]:
        """Get baseline by query signature."""
        return self.session.query(Baseline).filter(Baseline.query_signature == query_signature).first()

    def upsert(self, baseline_data: dict) -> Baseline:
        """Insert or update baseline."""
        existing = self.get_by_signature(baseline_data["query_signature"])

        if existing:
            # Update existing
            for key, value in baseline_data.items():
                setattr(existing, key, value)
            return self.update(existing)
        else:
            # Insert new
            baseline = Baseline(**baseline_data)
            return self.insert(baseline)
