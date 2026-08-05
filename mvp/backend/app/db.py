from sqlalchemy import create_engine, inspect, text
from sqlalchemy.orm import DeclarativeBase, Session, sessionmaker

from app.config import settings

engine = create_engine(
    f"sqlite:///{settings.family_db_path}",
    connect_args={"check_same_thread": False},
)
SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False)


class Base(DeclarativeBase):
    pass


def get_db():
    db: Session = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def run_migrations() -> None:
    """`Base.metadata.create_all()` only creates missing tables — it never
    alters an existing one. This is the lightweight stand-in for a real
    migration tool (Alembic) at this stage of the project: check for columns
    added after a table already existed, and ALTER TABLE them in if missing."""
    inspector = inspect(engine)
    if "ancestor_profiles" not in inspector.get_table_names():
        return
    existing_columns = {c["name"] for c in inspector.get_columns("ancestor_profiles")}
    if "parent_ancestor_id" not in existing_columns:
        with engine.begin() as conn:
            conn.execute(text("ALTER TABLE ancestor_profiles ADD COLUMN parent_ancestor_id INTEGER"))
    if "spouse_ancestor_id" not in existing_columns:
        with engine.begin() as conn:
            conn.execute(text("ALTER TABLE ancestor_profiles ADD COLUMN spouse_ancestor_id INTEGER"))
