from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, declarative_base
from src.core.config import Config

# Base class for models
Base = declarative_base()

class DatabaseManager:
    """Object-Oriented Database Manager for handling connections and sessions."""
    _instance = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(DatabaseManager, cls).__new__(cls)
            cls._instance._engine = create_engine(Config.DATABASE_URL)
            cls._instance._session_factory = sessionmaker(
                autocommit=False, autoflush=False, bind=cls._instance._engine
            )
        return cls._instance

    @property
    def engine(self):
        return self._engine

    def get_session(self):
        """Yields an active database session."""
        session = self._session_factory()
        try:
            yield session
        finally:
            session.close()

    def init_db(self):
        """Creates tables if they don't exist based on Base metadata."""
        Base.metadata.create_all(bind=self._engine)

# Global helper to maintain compatibility or simple procedural access if needed
db_manager = DatabaseManager()

def get_db():
    return next(db_manager.get_session())
