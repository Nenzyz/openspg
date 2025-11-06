"""
Test runner that works without pytest.

Runs all tests and reports results.
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

# Import all test modules
from test_basic import run_all_tests as run_basic_tests


def run_parser_tests():
    """Run parser tests without pytest."""
    print("\n" + "=" * 80)
    print(" PARSER TESTS")
    print("=" * 80)

    from graphspg.dsl.parser import DSLParser, ParseError
    from graphspg.dsl.ast import (
        BinaryOp,
        MatchStatement,
        StatementType,
        NodePattern,
        EdgePattern,
        PropertyRef,
        VariableRef,
        Literal,
        BinaryExpr,
    )

    parser = DSLParser()
    passed = 0
    failed = 0
    tests_run = 0

    # Test 1: Basic MATCH
    tests_run += 1
    try:
        dsl = "MATCH (s)-[]->(o) RETURN s.id, o.id"
        statement = parser.parse(dsl)
        assert statement.type == StatementType.MATCH
        assert isinstance(statement.body, MatchStatement)
        assert statement.body.return_clause is not None
        print("✓ test_gql_basic_match")
        passed += 1
    except Exception as e:
        print(f"✗ test_gql_basic_match: {e}")
        failed += 1

    # Test 2: WHERE with equals
    tests_run += 1
    try:
        dsl = "MATCH (s)-[]->(o) WHERE s.id = 1 RETURN s.id, o.id"
        statement = parser.parse(dsl)
        assert statement.type == StatementType.MATCH
        assert statement.body.where is not None
        condition = statement.body.where.condition
        assert isinstance(condition, BinaryExpr)
        assert condition.op == BinaryOp.EQ
        print("✓ test_gql_with_where_equals")
        passed += 1
    except Exception as e:
        print(f"✗ test_gql_with_where_equals: {e}")
        failed += 1

    # Test 3: WHERE with greater than
    tests_run += 1
    try:
        dsl = "MATCH (s)-[]->(o) WHERE s.id > o.id RETURN s.id, o.id"
        statement = parser.parse(dsl)
        condition = statement.body.where.condition
        assert isinstance(condition, BinaryExpr)
        assert condition.op == BinaryOp.GT
        print("✓ test_gql_with_where_greater_than")
        passed += 1
    except Exception as e:
        print(f"✗ test_gql_with_where_greater_than: {e}")
        failed += 1

    # Test 4: Multiple patterns
    tests_run += 1
    try:
        dsl = """MATCH (s)-[]->(o), (o)-[]->(p1)
                 WHERE s.id > o.id
                 RETURN s.id, o.id, p1.id"""
        statement = parser.parse(dsl)
        assert len(statement.body.patterns) == 2
        assert len(statement.body.return_clause.items) == 3
        print("✓ test_gql_multiple_patterns")
        passed += 1
    except Exception as e:
        print(f"✗ test_gql_multiple_patterns: {e}")
        failed += 1

    # Test 5: Label matching
    tests_run += 1
    try:
        dsl = "MATCH (s:User) RETURN s.id"
        statement = parser.parse(dsl)
        pattern = statement.body.patterns[0]
        node = pattern.elements[0]
        assert isinstance(node, NodePattern)
        assert node.variable == "s"
        assert "User" in node.labels
        print("✓ test_label_matching")
        passed += 1
    except Exception as e:
        print(f"✗ test_label_matching: {e}")
        failed += 1

    # Test 6: Edge with type
    tests_run += 1
    try:
        dsl = "MATCH (a:User)-[:FOLLOWS]->(b:User) RETURN a.name, b.name"
        statement = parser.parse(dsl)
        pattern = statement.body.patterns[0]
        edge = pattern.elements[1]
        assert isinstance(edge, EdgePattern)
        assert "FOLLOWS" in edge.types
        assert edge.direction == "->"
        print("✓ test_edge_with_type")
        passed += 1
    except Exception as e:
        print(f"✗ test_edge_with_type: {e}")
        failed += 1

    # Test 7: WHERE with AND
    tests_run += 1
    try:
        dsl = "MATCH (u:User) WHERE u.age > 30 AND u.city = 'NYC' RETURN u.name"
        statement = parser.parse(dsl)
        condition = statement.body.where.condition
        assert isinstance(condition, BinaryExpr)
        assert condition.op == BinaryOp.AND
        print("✓ test_where_with_and")
        passed += 1
    except Exception as e:
        print(f"✗ test_where_with_and: {e}")
        failed += 1

    # Test 8: WHERE with OR
    tests_run += 1
    try:
        dsl = "MATCH (u:User) WHERE u.age > 30 OR u.city = 'NYC' RETURN u.name"
        statement = parser.parse(dsl)
        condition = statement.body.where.condition
        assert isinstance(condition, BinaryExpr)
        assert condition.op == BinaryOp.OR
        print("✓ test_where_with_or")
        passed += 1
    except Exception as e:
        print(f"✗ test_where_with_or: {e}")
        failed += 1

    # Test 9: Property reference
    tests_run += 1
    try:
        dsl = "MATCH (u:User) WHERE u.age > 30 RETURN u.name"
        statement = parser.parse(dsl)
        condition = statement.body.where.condition
        assert isinstance(condition.left, PropertyRef)
        assert condition.left.variable == "u"
        assert condition.left.property == "age"
        print("✓ test_property_reference")
        passed += 1
    except Exception as e:
        print(f"✗ test_property_reference: {e}")
        failed += 1

    # Test 10: Complex pattern
    tests_run += 1
    try:
        dsl = """MATCH (a:User)-[:FOLLOWS]->(b:User)-[:POSTS]->(c:Post)
                 WHERE a.age > 25 AND c.likes > 100
                 RETURN a.name, b.name, c.title"""
        statement = parser.parse(dsl)
        pattern = statement.body.patterns[0]
        assert len(pattern.elements) == 5
        assert isinstance(pattern.elements[0], NodePattern)
        assert isinstance(pattern.elements[1], EdgePattern)
        assert isinstance(pattern.elements[2], NodePattern)
        assert isinstance(pattern.elements[3], EdgePattern)
        assert isinstance(pattern.elements[4], NodePattern)
        print("✓ test_complex_pattern")
        passed += 1
    except Exception as e:
        print(f"✗ test_complex_pattern: {e}")
        failed += 1

    print(f"\nParser Tests: {passed}/{tests_run} passed")
    return passed == tests_run


def run_compiler_tests():
    """Run compiler tests without pytest."""
    print("\n" + "=" * 80)
    print(" COMPILER TESTS")
    print("=" * 80)

    from graphspg.dsl.parser import DSLParser
    from graphspg.engine.compiler import CypherCompiler

    parser = DSLParser()
    compiler = CypherCompiler()
    passed = 0
    failed = 0
    tests_run = 0

    # Test 1: Basic MATCH compilation
    tests_run += 1
    try:
        dsl = "MATCH (s:User) RETURN s"
        statement = parser.parse(dsl)
        cypher = compiler.compile(statement)
        assert "MATCH" in cypher
        assert "(s:User)" in cypher
        assert "RETURN s" in cypher
        print("✓ test_basic_match_compilation")
        passed += 1
    except Exception as e:
        print(f"✗ test_basic_match_compilation: {e}")
        failed += 1

    # Test 2: MATCH with edge
    tests_run += 1
    try:
        dsl = "MATCH (a:User)-[:FOLLOWS]->(b:User) RETURN a, b"
        statement = parser.parse(dsl)
        cypher = compiler.compile(statement)
        assert "(a:User)" in cypher
        assert "[:FOLLOWS]" in cypher
        assert "(b:User)" in cypher
        print("✓ test_match_with_edge_compilation")
        passed += 1
    except Exception as e:
        print(f"✗ test_match_with_edge_compilation: {e}")
        failed += 1

    # Test 3: WHERE compilation
    tests_run += 1
    try:
        dsl = "MATCH (u:User) WHERE u.age > 30 RETURN u.name"
        statement = parser.parse(dsl)
        cypher = compiler.compile(statement)
        assert "WHERE" in cypher
        assert "u.age > 30" in cypher
        print("✓ test_where_compilation")
        passed += 1
    except Exception as e:
        print(f"✗ test_where_compilation: {e}")
        failed += 1

    # Test 4: Not equals (should convert to <>)
    tests_run += 1
    try:
        dsl = "MATCH (u:User) WHERE u.status != 'active' RETURN u"
        statement = parser.parse(dsl)
        cypher = compiler.compile(statement)
        assert "<>" in cypher  # != should be converted to <>
        print("✓ test_not_equals_conversion")
        passed += 1
    except Exception as e:
        print(f"✗ test_not_equals_conversion: {e}")
        failed += 1

    # Test 5: Complex pattern compilation
    tests_run += 1
    try:
        dsl = """MATCH (a:User)-[:FOLLOWS]->(b:User)-[:POSTS]->(c:Post)
                 WHERE a.age > 25 AND c.likes > 100
                 RETURN a.name, b.name, c.title"""
        statement = parser.parse(dsl)
        cypher = compiler.compile(statement)
        assert "(a:User)" in cypher
        assert "[:FOLLOWS]" in cypher
        assert "(b:User)" in cypher
        assert "[:POSTS]" in cypher
        assert "(c:Post)" in cypher
        assert "WHERE" in cypher
        assert "AND" in cypher
        print("✓ test_complex_pattern_compilation")
        passed += 1
    except Exception as e:
        print(f"✗ test_complex_pattern_compilation: {e}")
        failed += 1

    print(f"\nCompiler Tests: {passed}/{tests_run} passed")
    return passed == tests_run


def main():
    """Run all tests."""
    print("=" * 80)
    print(" GraphSPG Test Suite")
    print(" Ported from OpenSPG")
    print("=" * 80)

    all_passed = True

    # Run basic tests
    all_passed &= run_basic_tests()

    # Run parser tests
    all_passed &= run_parser_tests()

    # Run compiler tests
    all_passed &= run_compiler_tests()

    print("\n" + "=" * 80)
    if all_passed:
        print(" ✓ ALL TESTS PASSED")
    else:
        print(" ✗ SOME TESTS FAILED")
    print("=" * 80 + "\n")

    return 0 if all_passed else 1


if __name__ == "__main__":
    sys.exit(main())
