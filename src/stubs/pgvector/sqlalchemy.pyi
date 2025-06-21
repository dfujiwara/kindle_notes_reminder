# Type stubs for pgvector.sqlalchemy module
from typing import Any, Optional, Union
from sqlalchemy.types import TypeEngine
from sqlalchemy.sql.elements import ColumnElement
from sqlalchemy.sql.type_api import TypeEngine as TypeEngineBase

class VectorComparator(TypeEngineBase.Comparator[Any]):
    """Comparator for Vector type with pgvector-specific operations."""

    def cosine_distance(
        self, other: Union[list[float], "Vector"]
    ) -> ColumnElement[float]:
        """Calculate cosine distance between this vector and another."""
        ...

    def is_not(self, other: Any) -> ColumnElement[bool]:
        """Check if this vector is not equal to another value."""
        ...

class Vector(TypeEngine[Any]):
    """Vector type for pgvector extension."""

    def __init__(self, dimensions: Optional[int] = None) -> None:
        """
        Initialize Vector type.

        Args:
            dimensions: Number of dimensions for the vector
        """
        ...

# Type alias for Vector columns in SQLModel
VectorColumn = Union[Vector, ColumnElement[Vector]]
