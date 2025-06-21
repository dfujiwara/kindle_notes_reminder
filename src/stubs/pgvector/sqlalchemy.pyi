# Type stubs for pgvector.sqlalchemy module
from typing import Any, Optional
from sqlalchemy.types import UserDefinedType
from sqlalchemy.sql.elements import ColumnElement

class VectorComparator(UserDefinedType.Comparator[Any]):
    """Comparator for Vector type with pgvector-specific operations."""

    def l2_distance(self, other: Any) -> ColumnElement[float]:
        """Calculate L2 (Euclidean) distance between vectors."""
        ...

    def cosine_distance(self, other: Any) -> ColumnElement[float]:
        """Calculate cosine distance between vectors."""
        ...

    def max_inner_product(self, other: Any) -> ColumnElement[float]:
        """Calculate maximum inner product between vectors."""
        ...

    def l1_distance(self, other: Any) -> ColumnElement[float]:
        """Calculate L1 (Manhattan) distance between vectors."""
        ...

    def hamming_distance(self, other: Any) -> ColumnElement[float]:
        """Calculate Hamming distance between vectors."""
        ...

    def jaccard_distance(self, other: Any) -> ColumnElement[float]:
        """Calculate Jaccard distance between vectors."""
        ...

class VECTOR(UserDefinedType[Any]):
    """VECTOR type for pgvector extension."""

    def __init__(self, dim: Optional[int] = None) -> None:
        """
        Initialize VECTOR type.

        Args:
            dim: Number of dimensions for the vector (None for variable-length)
        """
        ...

# Vector is an alias for VECTOR
Vector = VECTOR
