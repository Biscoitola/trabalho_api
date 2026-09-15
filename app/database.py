import os

from sqlalchemy import URL, create_engine
from sqlalchemy.orm import DeclarativeBase, sessionmaker


class Base(DeclarativeBase):
    pass


engine = create_engine(
    URL.create(
        "postgresql+psycopg",
        username=os.getenv("POSTGRES_USER", "estudante"),
        password=os.getenv("POSTGRES_PASSWORD", "estudante123"),
        host="postgres",
        database=os.getenv("POSTGRES_DB", "campeonatos"),
    ),
    pool_pre_ping=True,
)
SessionLocal = sessionmaker(bind=engine)


def get_db():
    with SessionLocal() as session:
        yield session
