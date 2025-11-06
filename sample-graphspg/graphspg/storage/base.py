"""Base storage interface."""

from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional


class StorageAdapter(ABC):
    """Abstract base class for storage adapters."""

    @abstractmethod
    def connect(self):
        """Establish connection to the storage."""
        pass

    @abstractmethod
    def close(self):
        """Close connection to the storage."""
        pass

    @abstractmethod
    def create_vertex(
        self,
        labels: List[str],
        properties: Dict[str, Any],
        vertex_id: Optional[str] = None
    ) -> str:
        """Create a vertex and return its ID."""
        pass

    @abstractmethod
    def create_edge(
        self,
        source_id: str,
        target_id: str,
        edge_type: str,
        properties: Optional[Dict[str, Any]] = None
    ) -> str:
        """Create an edge and return its ID."""
        pass

    @abstractmethod
    def get_vertex(self, vertex_id: str) -> Optional[Dict[str, Any]]:
        """Get vertex by ID."""
        pass

    @abstractmethod
    def update_vertex(self, vertex_id: str, properties: Dict[str, Any]) -> bool:
        """Update vertex properties."""
        pass

    @abstractmethod
    def delete_vertex(self, vertex_id: str) -> bool:
        """Delete vertex by ID."""
        pass

    @abstractmethod
    def execute_query(self, query: str, parameters: Optional[Dict[str, Any]] = None) -> List[Dict[str, Any]]:
        """Execute a Cypher query and return results."""
        pass

    @abstractmethod
    def create_index(self, label: str, property_name: str):
        """Create an index on a label and property."""
        pass

    @abstractmethod
    def clear_database(self):
        """Clear all data from the database (for testing)."""
        pass
