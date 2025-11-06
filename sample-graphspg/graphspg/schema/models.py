"""Schema definition models for GraphSPG."""

from enum import Enum
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field


class PropertyType(str, Enum):
    """Property data types."""
    STRING = "String"
    INTEGER = "Integer"
    FLOAT = "Float"
    BOOLEAN = "Boolean"
    DATE = "Date"
    DATETIME = "DateTime"
    TEXT = "Text"  # Long text field


class Property(BaseModel):
    """Property definition for an entity or relation type."""
    name: str
    type: PropertyType
    description: Optional[str] = None
    required: bool = False
    indexed: bool = False


class RelationConstraint(str, Enum):
    """Relation cardinality constraints."""
    ONE_TO_ONE = "1:1"
    ONE_TO_MANY = "1:N"
    MANY_TO_ONE = "N:1"
    MANY_TO_MANY = "N:N"


class Relation(BaseModel):
    """Relation definition between entity types."""
    name: str
    source_type: str
    target_type: str
    description: Optional[str] = None
    constraint: RelationConstraint = RelationConstraint.MANY_TO_MANY
    properties: List[Property] = Field(default_factory=list)


class EntityType(BaseModel):
    """Entity type definition in the schema."""
    name: str
    description: Optional[str] = None
    properties: List[Property] = Field(default_factory=list)
    parent_type: Optional[str] = None  # For inheritance

    def get_property(self, name: str) -> Optional[Property]:
        """Get property by name."""
        for prop in self.properties:
            if prop.name == name:
                return prop
        return None


class Schema(BaseModel):
    """Complete schema definition."""
    name: str
    version: str = "1.0.0"
    entity_types: List[EntityType] = Field(default_factory=list)
    relations: List[Relation] = Field(default_factory=list)

    def get_entity_type(self, name: str) -> Optional[EntityType]:
        """Get entity type by name."""
        for entity_type in self.entity_types:
            if entity_type.name == name:
                return entity_type
        return None

    def get_relation(self, name: str) -> Optional[Relation]:
        """Get relation by name."""
        for relation in self.relations:
            if relation.name == name:
                return relation
        return None

    def validate_entity(self, type_name: str, properties: Dict[str, Any]) -> bool:
        """Validate entity properties against schema."""
        entity_type = self.get_entity_type(type_name)
        if not entity_type:
            raise ValueError(f"Unknown entity type: {type_name}")

        # Check required properties
        for prop in entity_type.properties:
            if prop.required and prop.name not in properties:
                raise ValueError(f"Missing required property: {prop.name}")

        return True

    def validate_relation(
        self,
        relation_name: str,
        source_type: str,
        target_type: str
    ) -> bool:
        """Validate relation against schema."""
        relation = self.get_relation(relation_name)
        if not relation:
            raise ValueError(f"Unknown relation: {relation_name}")

        if relation.source_type != source_type:
            raise ValueError(
                f"Invalid source type: expected {relation.source_type}, got {source_type}"
            )

        if relation.target_type != target_type:
            raise ValueError(
                f"Invalid target type: expected {relation.target_type}, got {target_type}"
            )

        return True
