"""Base repository with common CRUD operations."""
from typing import TypeVar, Generic, Type, List, Optional
from sqlalchemy.orm import Session

T = TypeVar("T")


class BaseRepository(Generic[T]):
    """Base repository for common database operations."""

    def __init__(self, model: Type[T], session: Session):
        self.model = model
        self.session = session

    def get_by_id(self, id: int) -> Optional[T]:
        """Get entity by ID."""
        return self.session.query(self.model).filter(self.model.id == id).first()

    def get_all(self, limit: int = 100, offset: int = 0) -> List[T]:
        """Get all entities with pagination."""
        return self.session.query(self.model).limit(limit).offset(offset).all()

    def insert(self, entity: T) -> T:
        """Insert a new entity."""
        self.session.add(entity)
        self.session.flush()
        return entity

    def bulk_insert(self, entities: List[T]) -> int:
        """Bulk insert entities."""
        self.session.bulk_save_objects(entities)
        self.session.flush()
        return len(entities)

    def update(self, entity: T) -> T:
        """Update an entity."""
        self.session.merge(entity)
        self.session.flush()
        return entity

    def delete(self, entity: T) -> None:
        """Delete an entity."""
        self.session.delete(entity)
        self.session.flush()

    def delete_by_id(self, id: int) -> bool:
        """Delete entity by ID."""
        entity = self.get_by_id(id)
        if entity:
            self.delete(entity)
            return True
        return False
