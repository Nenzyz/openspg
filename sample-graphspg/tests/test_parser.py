"""
Comprehensive parser tests ported from OpenSPG.

Based on:
- reasoner/kgdsl-parser/src/test/scala/com/antgroup/openspg/reasoner/parser/OpenSPGDslParserTest.scala
"""

import pytest
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

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


class TestOpenSPGDslParser:
    """Test DSL parser following OpenSPG test patterns."""

    def setup_method(self):
        """Set up parser for each test."""
        self.parser = DSLParser()

    def test_gql_basic_match(self):
        """Test basic MATCH pattern: MATCH (s)-[]->(o) RETURN s.id, o.id"""
        dsl = "MATCH (s)-[]->(o) RETURN s.id, o.id"
        statement = self.parser.parse(dsl)

        assert statement.type == StatementType.MATCH
        assert isinstance(statement.body, MatchStatement)
        assert statement.body.return_clause is not None
        assert len(statement.body.return_clause.items) == 2

    def test_gql_with_where_equals(self):
        """Test MATCH with WHERE clause: s.id = 1"""
        dsl = "MATCH (s)-[]->(o) WHERE s.id = 1 RETURN s.id, o.id"
        statement = self.parser.parse(dsl)

        assert statement.type == StatementType.MATCH
        assert statement.body.where is not None

        # Check WHERE condition is binary expression
        condition = statement.body.where.condition
        assert isinstance(condition, BinaryExpr)
        assert condition.op == BinaryOp.EQ

    def test_gql_with_where_greater_than(self):
        """Test MATCH with WHERE clause: s.id > o.id"""
        dsl = "MATCH (s)-[]->(o) WHERE s.id > o.id RETURN s.id, o.id"
        statement = self.parser.parse(dsl)

        assert statement.type == StatementType.MATCH
        condition = statement.body.where.condition
        assert isinstance(condition, BinaryExpr)
        assert condition.op == BinaryOp.GT

    def test_gql_multiple_patterns(self):
        """Test multiple patterns: MATCH (s)-[]->(o), (o)-[]->(p1)"""
        dsl = """MATCH (s)-[]->(o), (o)-[]->(p1)
                 WHERE s.id > o.id
                 RETURN s.id, o.id, p1.id"""

        statement = self.parser.parse(dsl)

        assert statement.type == StatementType.MATCH
        # Should have 2 patterns
        assert len(statement.body.patterns) == 2
        # Should return 3 items
        assert len(statement.body.return_clause.items) == 3

    def test_label_matching(self):
        """Test node with label: MATCH (s:User)"""
        dsl = "MATCH (s:User) RETURN s.id"
        statement = self.parser.parse(dsl)

        assert statement.type == StatementType.MATCH
        pattern = statement.body.patterns[0]

        # First element should be a NodePattern
        node = pattern.elements[0]
        assert isinstance(node, NodePattern)
        assert node.variable == "s"
        assert "User" in node.labels

    def test_multiple_labels(self):
        """Test node with multiple labels: MATCH (s:User:Person)"""
        dsl = "MATCH (s:User:Person) RETURN s.id"
        statement = self.parser.parse(dsl)

        pattern = statement.body.patterns[0]
        node = pattern.elements[0]
        assert isinstance(node, NodePattern)
        assert "User" in node.labels
        assert "Person" in node.labels

    def test_edge_with_type(self):
        """Test edge with type: MATCH (a:User)-[:FOLLOWS]->(b:User)"""
        dsl = "MATCH (a:User)-[:FOLLOWS]->(b:User) RETURN a.name, b.name"
        statement = self.parser.parse(dsl)

        pattern = statement.body.patterns[0]
        # Pattern should have 3 elements: node, edge, node
        assert len(pattern.elements) == 3

        edge = pattern.elements[1]
        assert isinstance(edge, EdgePattern)
        assert "FOLLOWS" in edge.types
        assert edge.direction == "->"

    def test_reverse_edge(self):
        """Test reverse edge direction: MATCH (a)<-[:FOLLOWS]-(b)"""
        dsl = "MATCH (a)<-[:FOLLOWS]-(b) RETURN a, b"
        statement = self.parser.parse(dsl)

        pattern = statement.body.patterns[0]
        edge = pattern.elements[1]
        assert isinstance(edge, EdgePattern)
        assert edge.direction == "<-"

    def test_bidirectional_edge(self):
        """Test bidirectional edge: MATCH (a)-[:KNOWS]-(b)"""
        dsl = "MATCH (a)-[:KNOWS]-(b) RETURN a, b"
        statement = self.parser.parse(dsl)

        pattern = statement.body.patterns[0]
        edge = pattern.elements[1]
        assert isinstance(edge, EdgePattern)
        assert edge.direction == "-"

    def test_where_with_and(self):
        """Test WHERE with AND operator"""
        dsl = "MATCH (u:User) WHERE u.age > 30 AND u.city = 'NYC' RETURN u.name"
        statement = self.parser.parse(dsl)

        condition = statement.body.where.condition
        assert isinstance(condition, BinaryExpr)
        assert condition.op == BinaryOp.AND

    def test_where_with_or(self):
        """Test WHERE with OR operator"""
        dsl = "MATCH (u:User) WHERE u.age > 30 OR u.city = 'NYC' RETURN u.name"
        statement = self.parser.parse(dsl)

        condition = statement.body.where.condition
        assert isinstance(condition, BinaryExpr)
        assert condition.op == BinaryOp.OR

    def test_where_comparison_operators(self):
        """Test all comparison operators"""
        test_cases = [
            ("u.age = 30", BinaryOp.EQ),
            ("u.age != 30", BinaryOp.NEQ),
            ("u.age > 30", BinaryOp.GT),
            ("u.age >= 30", BinaryOp.GTE),
            ("u.age < 30", BinaryOp.LT),
            ("u.age <= 30", BinaryOp.LTE),
        ]

        for where_clause, expected_op in test_cases:
            dsl = f"MATCH (u:User) WHERE {where_clause} RETURN u"
            statement = self.parser.parse(dsl)
            condition = statement.body.where.condition
            assert condition.op == expected_op, f"Failed for {where_clause}"

    def test_property_reference(self):
        """Test property reference: variable.property"""
        dsl = "MATCH (u:User) WHERE u.age > 30 RETURN u.name"
        statement = self.parser.parse(dsl)

        # Check WHERE condition has property reference
        condition = statement.body.where.condition
        assert isinstance(condition.left, PropertyRef)
        assert condition.left.variable == "u"
        assert condition.left.property == "age"

    def test_variable_reference(self):
        """Test variable reference in RETURN"""
        dsl = "MATCH (u:User) RETURN u"
        statement = self.parser.parse(dsl)

        return_item = statement.body.return_clause.items[0]
        assert isinstance(return_item, VariableRef)
        assert return_item.name == "u"

    def test_complex_pattern(self):
        """Test complex multi-hop pattern"""
        dsl = """MATCH (a:User)-[:FOLLOWS]->(b:User)-[:POSTS]->(c:Post)
                 WHERE a.age > 25 AND c.likes > 100
                 RETURN a.name, b.name, c.title"""

        statement = self.parser.parse(dsl)

        pattern = statement.body.patterns[0]
        # Should have 5 elements: node, edge, node, edge, node
        assert len(pattern.elements) == 5

        # Verify structure
        assert isinstance(pattern.elements[0], NodePattern)
        assert isinstance(pattern.elements[1], EdgePattern)
        assert isinstance(pattern.elements[2], NodePattern)
        assert isinstance(pattern.elements[3], EdgePattern)
        assert isinstance(pattern.elements[4], NodePattern)

    def test_exception_invalid_syntax(self):
        """Test parser exception on invalid syntax"""
        dsl = "MATCH (s) BLAH RETURN s"

        with pytest.raises(ParseError):
            self.parser.parse(dsl)

    def test_exception_empty_query(self):
        """Test parser exception on empty query"""
        dsl = ""

        with pytest.raises(ParseError):
            self.parser.parse(dsl)

    def test_exception_incomplete_pattern(self):
        """Test parser exception on incomplete pattern"""
        dsl = "MATCH (s)-[]->"

        with pytest.raises(ParseError):
            self.parser.parse(dsl)

    def test_mutual_followers(self):
        """Test mutual follower pattern: (a)-[:FOLLOWS]->(b)-[:FOLLOWS]->(a)"""
        dsl = "MATCH (a:User)-[:FOLLOWS]->(b:User)-[:FOLLOWS]->(a) RETURN a.name, b.name"
        statement = self.parser.parse(dsl)

        pattern = statement.body.patterns[0]
        # Should have 5 elements forming a cycle
        assert len(pattern.elements) == 5

        # Verify first and last nodes reference same variable
        first_node = pattern.elements[0]
        last_node = pattern.elements[4]
        assert first_node.variable == last_node.variable == "a"

    def test_return_multiple_properties(self):
        """Test returning multiple properties"""
        dsl = "MATCH (u:User) RETURN u.id, u.name, u.email, u.age"
        statement = self.parser.parse(dsl)

        items = statement.body.return_clause.items
        assert len(items) == 4

        # All should be PropertyRef
        for item in items:
            assert isinstance(item, PropertyRef)
            assert item.variable == "u"

    def test_edge_variable(self):
        """Test edge with variable: -[rel:FOLLOWS]->"""
        dsl = "MATCH (a)-[rel:FOLLOWS]->(b) RETURN a, rel, b"
        statement = self.parser.parse(dsl)

        pattern = statement.body.patterns[0]
        edge = pattern.elements[1]
        assert edge.variable == "rel"
        assert "FOLLOWS" in edge.types

    def test_node_without_label(self):
        """Test node without label: (s)"""
        dsl = "MATCH (s) RETURN s"
        statement = self.parser.parse(dsl)

        pattern = statement.body.patterns[0]
        node = pattern.elements[0]
        assert node.variable == "s"
        assert len(node.labels) == 0

    def test_edge_without_type(self):
        """Test edge without type: -[]->"""
        dsl = "MATCH (a)-[]->(b) RETURN a, b"
        statement = self.parser.parse(dsl)

        pattern = statement.body.patterns[0]
        edge = pattern.elements[1]
        assert len(edge.types) == 0

    def test_string_literal_single_quote(self):
        """Test string literal with single quotes"""
        dsl = "MATCH (u:User) WHERE u.name = 'Alice' RETURN u"
        statement = self.parser.parse(dsl)

        condition = statement.body.where.condition
        assert isinstance(condition.right, Literal)
        assert condition.right.value == "Alice"

    def test_string_literal_double_quote(self):
        """Test string literal with double quotes"""
        dsl = 'MATCH (u:User) WHERE u.name = "Bob" RETURN u'
        statement = self.parser.parse(dsl)

        condition = statement.body.where.condition
        assert isinstance(condition.right, Literal)
        assert condition.right.value == "Bob"

    def test_integer_literal(self):
        """Test integer literal"""
        dsl = "MATCH (u:User) WHERE u.age = 30 RETURN u"
        statement = self.parser.parse(dsl)

        condition = statement.body.where.condition
        assert isinstance(condition.right, Literal)
        assert condition.right.value == 30
        assert isinstance(condition.right.value, int)

    def test_float_literal(self):
        """Test float literal"""
        dsl = "MATCH (u:User) WHERE u.rating = 4.5 RETURN u"
        statement = self.parser.parse(dsl)

        condition = statement.body.where.condition
        assert isinstance(condition.right, Literal)
        assert condition.right.value == 4.5
        assert isinstance(condition.right.value, float)

    def test_comparison_with_property_refs(self):
        """Test comparison between two property references"""
        dsl = "MATCH (a:User)-[]->(b:User) WHERE a.age > b.age RETURN a, b"
        statement = self.parser.parse(dsl)

        condition = statement.body.where.condition
        assert isinstance(condition.left, PropertyRef)
        assert isinstance(condition.right, PropertyRef)
        assert condition.left.variable == "a"
        assert condition.right.variable == "b"

    def test_three_node_pattern(self):
        """Test three-node linear pattern"""
        dsl = "MATCH (a)-[]->(b)-[]->(c) RETURN a, b, c"
        statement = self.parser.parse(dsl)

        pattern = statement.body.patterns[0]
        # 5 elements: a, edge, b, edge, c
        assert len(pattern.elements) == 5

        # Verify all nodes
        assert pattern.elements[0].variable == "a"
        assert pattern.elements[2].variable == "b"
        assert pattern.elements[4].variable == "c"

    def test_film_director_pattern(self):
        """Test film director pattern from OpenSPG examples"""
        dsl = """MATCH (A:Film)-[:directFilm]-(B:FilmDirector)
                 WHERE B.birthDate > '1980'
                 RETURN B.name"""

        statement = self.parser.parse(dsl)

        assert statement.type == StatementType.MATCH
        pattern = statement.body.patterns[0]

        # Verify nodes
        film_node = pattern.elements[0]
        assert "Film" in film_node.labels

        # Verify edge
        edge = pattern.elements[1]
        assert "directFilm" in edge.types

        # Verify WHERE condition
        condition = statement.body.where.condition
        assert isinstance(condition.left, PropertyRef)
        assert condition.left.property == "birthDate"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
