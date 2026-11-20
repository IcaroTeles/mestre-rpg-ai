"""Base compartilhada para modelos SQLAlchemy futuros."""

from sqlalchemy.orm import DeclarativeBase


class Base(DeclarativeBase):
    """Base vazia para evolucao segura das futuras entidades."""
