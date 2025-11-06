"""Schema registry for managing schemas."""

from typing import Dict, Optional
from graphspg.schema.models import Schema


class SchemaRegistry:
    """Global schema registry."""

    def __init__(self):
        self._schemas: Dict[str, Schema] = {}
        self._active_schema: Optional[str] = None

    def register(self, schema: Schema, set_active: bool = False):
        """Register a schema."""
        self._schemas[schema.name] = schema
        if set_active or self._active_schema is None:
            self._active_schema = schema.name

    def get(self, name: str) -> Optional[Schema]:
        """Get schema by name."""
        return self._schemas.get(name)

    def get_active(self) -> Optional[Schema]:
        """Get the active schema."""
        if self._active_schema:
            return self._schemas.get(self._active_schema)
        return None

    def set_active(self, name: str):
        """Set active schema."""
        if name not in self._schemas:
            raise ValueError(f"Schema not found: {name}")
        self._active_schema = name

    def list_schemas(self) -> list[str]:
        """List all registered schema names."""
        return list(self._schemas.keys())


# Global schema registry instance
schema_registry = SchemaRegistry()
