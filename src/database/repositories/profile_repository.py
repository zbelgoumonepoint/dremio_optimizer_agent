"""Repository for QueryProfile model."""
from typing import Optional
from sqlalchemy.orm import Session
from ..models import QueryProfile
from .base_repository import BaseRepository


class ProfileRepository(BaseRepository[QueryProfile]):
    """Repository for QueryProfile operations."""

    def __init__(self, session: Session):
        super().__init__(QueryProfile, session)

    def get_by_job_id(self, job_id: str) -> Optional[QueryProfile]:
        """Get profile by job_id."""
        return self.session.query(QueryProfile).filter(QueryProfile.job_id == job_id).first()

    def insert_from_dict(self, profile_data: dict) -> QueryProfile:
        """Insert profile from dictionary."""
        profile = QueryProfile(**profile_data)
        return self.insert(profile)
