"""Shared Pydantic base classes."""

from pydantic import BaseModel, ConfigDict


class OrmModel(BaseModel):
    """Base response schema that can validate directly from SQLAlchemy models."""

    model_config = ConfigDict(from_attributes=True)
