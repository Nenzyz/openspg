"""Basic tests for GraphSPG components."""

import sys
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from graphspg.dsl.parser import DSLParser
from graphspg.engine.compiler import CypherCompiler
from graphspg.dsl.ast import StatementType


def test_parser_simple_match():
    """Test parsing a simple MATCH statement."""
    parser = DSLParser()
    query = "MATCH (u:User) RETURN u"

    try:
        statement = parser.parse(query)
        assert statement.type == StatementType.MATCH
        print("✓ Parser test: Simple MATCH")
        return True
    except Exception as e:
        print(f"✗ Parser test failed: {e}")
        return False


def test_parser_with_where():
    """Test parsing MATCH with WHERE clause."""
    parser = DSLParser()
    query = "MATCH (u:User) WHERE u.age > 30 RETURN u.name"

    try:
        statement = parser.parse(query)
        assert statement.type == StatementType.MATCH
        assert statement.body.where is not None
        print("✓ Parser test: MATCH with WHERE")
        return True
    except Exception as e:
        print(f"✗ Parser test failed: {e}")
        return False


def test_parser_pattern_with_edge():
    """Test parsing pattern with edge."""
    parser = DSLParser()
    query = "MATCH (a:User)-[:FOLLOWS]->(b:User) RETURN a, b"

    try:
        statement = parser.parse(query)
        assert statement.type == StatementType.MATCH
        assert len(statement.body.patterns) == 1
        pattern = statement.body.patterns[0]
        assert len(pattern.elements) == 3  # node, edge, node
        print("✓ Parser test: Pattern with edge")
        return True
    except Exception as e:
        print(f"✗ Parser test failed: {e}")
        return False


def test_compiler_simple():
    """Test compiling a simple query to Cypher."""
    parser = DSLParser()
    compiler = CypherCompiler()
    query = "MATCH (u:User) RETURN u"

    try:
        statement = parser.parse(query)
        cypher = compiler.compile(statement)
        assert "MATCH" in cypher
        assert "(u:User)" in cypher
        assert "RETURN" in cypher
        print("✓ Compiler test: Simple query")
        print(f"  Compiled: {cypher.strip()}")
        return True
    except Exception as e:
        print(f"✗ Compiler test failed: {e}")
        return False


def test_compiler_with_where():
    """Test compiling query with WHERE clause."""
    parser = DSLParser()
    compiler = CypherCompiler()
    query = "MATCH (u:User) WHERE u.age > 30 RETURN u.name"

    try:
        statement = parser.parse(query)
        cypher = compiler.compile(statement)
        assert "WHERE" in cypher
        assert "u.age > 30" in cypher
        print("✓ Compiler test: Query with WHERE")
        print(f"  Compiled: {cypher.strip()}")
        return True
    except Exception as e:
        print(f"✗ Compiler test failed: {e}")
        return False


def test_compiler_complex_pattern():
    """Test compiling complex pattern."""
    parser = DSLParser()
    compiler = CypherCompiler()
    query = "MATCH (a:User)-[:FOLLOWS]->(b:User) WHERE a.age > 25 RETURN a.name, b.name"

    try:
        statement = parser.parse(query)
        cypher = compiler.compile(statement)
        assert "(a:User)" in cypher
        assert "[:FOLLOWS]" in cypher
        assert "(b:User)" in cypher
        assert "WHERE" in cypher
        print("✓ Compiler test: Complex pattern")
        print(f"  Compiled: {cypher.strip()}")
        return True
    except Exception as e:
        print(f"✗ Compiler test failed: {e}")
        return False


def test_schema_creation():
    """Test creating a schema."""
    try:
        from graphspg.schema.models import EntityType, Property, PropertyType, Schema
    except ImportError as e:
        print(f"⊘ Schema test skipped: {e}")
        return True  # Skip test if dependencies not installed

    try:
        user_type = EntityType(
            name="User",
            properties=[
                Property(name="name", type=PropertyType.STRING, required=True),
                Property(name="age", type=PropertyType.INTEGER),
            ]
        )

        schema = Schema(
            name="test_schema",
            entity_types=[user_type]
        )

        assert schema.get_entity_type("User") is not None
        assert schema.get_entity_type("NonExistent") is None
        print("✓ Schema test: Schema creation")
        return True
    except Exception as e:
        print(f"✗ Schema test failed: {e}")
        return False


def run_all_tests():
    """Run all tests."""
    print("=" * 80)
    print("Running GraphSPG Basic Tests")
    print("=" * 80)
    print()

    tests = [
        test_parser_simple_match,
        test_parser_with_where,
        test_parser_pattern_with_edge,
        test_compiler_simple,
        test_compiler_with_where,
        test_compiler_complex_pattern,
        test_schema_creation,
    ]

    results = []
    for test in tests:
        results.append(test())
        print()

    print("=" * 80)
    passed = sum(results)
    total = len(results)
    print(f"Results: {passed}/{total} tests passed")
    print("=" * 80)

    return all(results)


if __name__ == "__main__":
    success = run_all_tests()
    sys.exit(0 if success else 1)
