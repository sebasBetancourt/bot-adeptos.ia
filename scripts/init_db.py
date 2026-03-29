from src.database import engine, Base
from src.models.lead import Lead

def init_db():
    print("Initializing Database...")
    Base.metadata.create_all(bind=engine)
    print("Database Initialized Successfully.")

if __name__ == "__main__":
    init_db()
