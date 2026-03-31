from typing import TypeVar, Generic, Type, Optional, List, Any
from sqlalchemy.orm import Session
from src.core.database import Base, db_manager

ModelType = TypeVar("ModelType", bound=Base)

class BaseRepository(Generic[ModelType]):
    """Generic CRUD operations for SQLAlchemy Models."""
    
    def __init__(self, model: Type[ModelType]):
        self.model = model

    def get_session(self) -> Session:
        """Returns a new session from the DatabaseManager."""
        return next(db_manager.get_session())

    def get(self, id: Any) -> Optional[ModelType]:
        db = self.get_session()
        try:
            return db.query(self.model).filter(self.model.id == id).first()
        finally:
            db.close()

    def get_all(self, skip: int = 0, limit: int = 100) -> List[ModelType]:
        db = self.get_session()
        try:
            return db.query(self.model).offset(skip).limit(limit).all()
        finally:
            db.close()

    def count(self) -> int:
        db = self.get_session()
        try:
            return db.query(self.model).count()
        finally:
            db.close()

    def _add_and_commit(self, db: Session, instance: ModelType) -> ModelType:
        try:
            db.add(instance)
            db.commit()
            db.refresh(instance)
            return instance
        except Exception as e:
            db.rollback()
            raise e

    def create(self, **kwargs) -> ModelType:
        db = self.get_session()
        try:
            instance = self.model(**kwargs)
            return self._add_and_commit(db, instance)
        finally:
            db.close()
