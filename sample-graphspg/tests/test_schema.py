"""
Schema validation tests ported from OpenSPG.

Tests schema definition, validation, and registry.
"""

import pytest
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

try:
    from graphspg.schema.models import (
        EntityType,
        Property,
        PropertyType,
        Relation,
        RelationConstraint,
        Schema,
    )
    from graphspg.schema.registry import SchemaRegistry

    PYDANTIC_AVAILABLE = True
except ImportError:
    PYDANTIC_AVAILABLE = False
    pytest.skip("Pydantic not available", allow_module_level=True)


class TestSchemaModels:
    """Test schema model definitions."""

    def test_create_entity_type(self):
        """Test creating an entity type"""
        user_type = EntityType(
            name="User",
            description="Social network user",
            properties=[
                Property(name="id", type=PropertyType.STRING, required=True, indexed=True),
                Property(name="name", type=PropertyType.STRING, required=True),
                Property(name="age", type=PropertyType.INTEGER),
            ]
        )

        assert user_type.name == "User"
        assert len(user_type.properties) == 3
        assert user_type.get_property("name").type == PropertyType.STRING
        assert user_type.get_property("age").required is False

    def test_create_relation(self):
        """Test creating a relation"""
        follows = Relation(
            name="FOLLOWS",
            source_type="User",
            target_type="User",
            description="User follows another user",
            constraint=RelationConstraint.MANY_TO_MANY,
        )

        assert follows.name == "FOLLOWS"
        assert follows.source_type == "User"
        assert follows.target_type == "User"
        assert follows.constraint == RelationConstraint.MANY_TO_MANY

    def test_create_schema(self):
        """Test creating a complete schema"""
        user_type = EntityType(
            name="User",
            properties=[
                Property(name="name", type=PropertyType.STRING, required=True),
                Property(name="age", type=PropertyType.INTEGER),
            ]
        )

        post_type = EntityType(
            name="Post",
            properties=[
                Property(name="title", type=PropertyType.STRING, required=True),
                Property(name="content", type=PropertyType.TEXT),
            ]
        )

        posted_relation = Relation(
            name="POSTED",
            source_type="User",
            target_type="Post",
            constraint=RelationConstraint.ONE_TO_MANY,
        )

        schema = Schema(
            name="test_schema",
            version="1.0.0",
            entity_types=[user_type, post_type],
            relations=[posted_relation],
        )

        assert schema.name == "test_schema"
        assert len(schema.entity_types) == 2
        assert len(schema.relations) == 1

    def test_get_entity_type(self):
        """Test retrieving entity type from schema"""
        user_type = EntityType(
            name="User",
            properties=[Property(name="name", type=PropertyType.STRING)]
        )

        schema = Schema(
            name="test_schema",
            entity_types=[user_type]
        )

        retrieved = schema.get_entity_type("User")
        assert retrieved is not None
        assert retrieved.name == "User"

        non_existent = schema.get_entity_type("NonExistent")
        assert non_existent is None

    def test_get_relation(self):
        """Test retrieving relation from schema"""
        follows = Relation(
            name="FOLLOWS",
            source_type="User",
            target_type="User",
        )

        schema = Schema(
            name="test_schema",
            relations=[follows]
        )

        retrieved = schema.get_relation("FOLLOWS")
        assert retrieved is not None
        assert retrieved.name == "FOLLOWS"

        non_existent = schema.get_relation("NonExistent")
        assert non_existent is None

    def test_property_types(self):
        """Test all property types"""
        properties = [
            Property(name="str_prop", type=PropertyType.STRING),
            Property(name="int_prop", type=PropertyType.INTEGER),
            Property(name="float_prop", type=PropertyType.FLOAT),
            Property(name="bool_prop", type=PropertyType.BOOLEAN),
            Property(name="date_prop", type=PropertyType.DATE),
            Property(name="datetime_prop", type=PropertyType.DATETIME),
            Property(name="text_prop", type=PropertyType.TEXT),
        ]

        entity_type = EntityType(
            name="TestEntity",
            properties=properties
        )

        assert len(entity_type.properties) == 7
        assert entity_type.get_property("int_prop").type == PropertyType.INTEGER
        assert entity_type.get_property("text_prop").type == PropertyType.TEXT

    def test_relation_constraints(self):
        """Test all relation constraints"""
        constraints = [
            RelationConstraint.ONE_TO_ONE,
            RelationConstraint.ONE_TO_MANY,
            RelationConstraint.MANY_TO_ONE,
            RelationConstraint.MANY_TO_MANY,
        ]

        for i, constraint in enumerate(constraints):
            relation = Relation(
                name=f"REL{i}",
                source_type="A",
                target_type="B",
                constraint=constraint,
            )
            assert relation.constraint == constraint

    def test_entity_with_parent_type(self):
        """Test entity type inheritance"""
        user_type = EntityType(
            name="User",
            properties=[Property(name="name", type=PropertyType.STRING)]
        )

        admin_type = EntityType(
            name="Admin",
            parent_type="User",
            properties=[Property(name="permissions", type=PropertyType.TEXT)]
        )

        assert admin_type.parent_type == "User"

    def test_property_required_flag(self):
        """Test required property flag"""
        required_prop = Property(name="id", type=PropertyType.STRING, required=True)
        optional_prop = Property(name="bio", type=PropertyType.TEXT, required=False)

        assert required_prop.required is True
        assert optional_prop.required is False

    def test_property_indexed_flag(self):
        """Test indexed property flag"""
        indexed_prop = Property(name="email", type=PropertyType.STRING, indexed=True)
        unindexed_prop = Property(name="bio", type=PropertyType.TEXT, indexed=False)

        assert indexed_prop.indexed is True
        assert unindexed_prop.indexed is False

    def test_relation_with_properties(self):
        """Test relation with properties"""
        follows = Relation(
            name="FOLLOWS",
            source_type="User",
            target_type="User",
            properties=[
                Property(name="since", type=PropertyType.DATETIME),
                Property(name="strength", type=PropertyType.FLOAT),
            ]
        )

        assert len(follows.properties) == 2
        assert follows.properties[0].name == "since"


class TestSchemaValidation:
    """Test schema validation logic."""

    def test_validate_entity_success(self):
        """Test successful entity validation"""
        user_type = EntityType(
            name="User",
            properties=[
                Property(name="name", type=PropertyType.STRING, required=True),
                Property(name="age", type=PropertyType.INTEGER, required=False),
            ]
        )

        schema = Schema(
            name="test_schema",
            entity_types=[user_type]
        )

        # Should pass with required properties
        result = schema.validate_entity("User", {"name": "Alice", "age": 30})
        assert result is True

        # Should pass with only required properties
        result = schema.validate_entity("User", {"name": "Bob"})
        assert result is True

    def test_validate_entity_missing_required(self):
        """Test validation fails on missing required property"""
        user_type = EntityType(
            name="User",
            properties=[
                Property(name="name", type=PropertyType.STRING, required=True),
            ]
        )

        schema = Schema(
            name="test_schema",
            entity_types=[user_type]
        )

        # Should fail without required property
        with pytest.raises(ValueError, match="Missing required property"):
            schema.validate_entity("User", {"age": 30})

    def test_validate_entity_unknown_type(self):
        """Test validation fails on unknown entity type"""
        schema = Schema(name="test_schema")

        with pytest.raises(ValueError, match="Unknown entity type"):
            schema.validate_entity("NonExistent", {"name": "Alice"})

    def test_validate_relation_success(self):
        """Test successful relation validation"""
        follows = Relation(
            name="FOLLOWS",
            source_type="User",
            target_type="User",
        )

        schema = Schema(
            name="test_schema",
            relations=[follows]
        )

        result = schema.validate_relation("FOLLOWS", "User", "User")
        assert result is True

    def test_validate_relation_wrong_source(self):
        """Test validation fails on wrong source type"""
        follows = Relation(
            name="FOLLOWS",
            source_type="User",
            target_type="User",
        )

        schema = Schema(
            name="test_schema",
            relations=[follows]
        )

        with pytest.raises(ValueError, match="Invalid source type"):
            schema.validate_relation("FOLLOWS", "Post", "User")

    def test_validate_relation_wrong_target(self):
        """Test validation fails on wrong target type"""
        follows = Relation(
            name="FOLLOWS",
            source_type="User",
            target_type="User",
        )

        schema = Schema(
            name="test_schema",
            relations=[follows]
        )

        with pytest.raises(ValueError, match="Invalid target type"):
            schema.validate_relation("FOLLOWS", "User", "Post")

    def test_validate_relation_unknown(self):
        """Test validation fails on unknown relation"""
        schema = Schema(name="test_schema")

        with pytest.raises(ValueError, match="Unknown relation"):
            schema.validate_relation("NonExistent", "User", "User")


class TestSchemaRegistry:
    """Test schema registry functionality."""

    def test_register_schema(self):
        """Test registering a schema"""
        registry = SchemaRegistry()
        schema = Schema(name="test_schema")

        registry.register(schema)

        retrieved = registry.get("test_schema")
        assert retrieved is not None
        assert retrieved.name == "test_schema"

    def test_register_multiple_schemas(self):
        """Test registering multiple schemas"""
        registry = SchemaRegistry()
        schema1 = Schema(name="schema1")
        schema2 = Schema(name="schema2")

        registry.register(schema1)
        registry.register(schema2)

        schemas = registry.list_schemas()
        assert len(schemas) == 2
        assert "schema1" in schemas
        assert "schema2" in schemas

    def test_set_active_schema(self):
        """Test setting active schema"""
        registry = SchemaRegistry()
        schema = Schema(name="test_schema")

        registry.register(schema, set_active=True)

        active = registry.get_active()
        assert active is not None
        assert active.name == "test_schema"

    def test_change_active_schema(self):
        """Test changing active schema"""
        registry = SchemaRegistry()
        schema1 = Schema(name="schema1")
        schema2 = Schema(name="schema2")

        registry.register(schema1, set_active=True)
        registry.register(schema2)

        # Schema1 should be active
        assert registry.get_active().name == "schema1"

        # Change to schema2
        registry.set_active("schema2")
        assert registry.get_active().name == "schema2"

    def test_set_active_nonexistent(self):
        """Test setting active to nonexistent schema fails"""
        registry = SchemaRegistry()

        with pytest.raises(ValueError, match="Schema not found"):
            registry.set_active("nonexistent")

    def test_get_nonexistent_schema(self):
        """Test getting nonexistent schema returns None"""
        registry = SchemaRegistry()

        result = registry.get("nonexistent")
        assert result is None

    def test_auto_set_first_schema_active(self):
        """Test first schema is automatically set as active"""
        registry = SchemaRegistry()
        schema = Schema(name="first_schema")

        registry.register(schema)

        active = registry.get_active()
        assert active is not None
        assert active.name == "first_schema"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
