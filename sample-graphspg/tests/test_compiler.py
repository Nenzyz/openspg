"""
Compiler tests ported from OpenSPG.

Tests DSL to Cypher compilation.
"""

import pytest
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from graphspg.dsl.parser import DSLParser
from graphspg.engine.compiler import CypherCompiler


class TestCypherCompiler:
    """Test Cypher compiler following OpenSPG patterns."""

    def setup_method(self):
        """Set up parser and compiler for each test."""
        self.parser = DSLParser()
        self.compiler = CypherCompiler()

    def test_basic_match(self):
        """Test compiling basic MATCH"""
        dsl = "MATCH (s:User) RETURN s"
        statement = self.parser.parse(dsl)
        cypher = self.compiler.compile(statement)

        assert "MATCH" in cypher
        assert "(s:User)" in cypher
        assert "RETURN s" in cypher

    def test_match_with_edge(self):
        """Test compiling MATCH with edge"""
        dsl = "MATCH (a:User)-[:FOLLOWS]->(b:User) RETURN a, b"
        statement = self.parser.parse(dsl)
        cypher = self.compiler.compile(statement)

        assert "MATCH" in cypher
        assert "(a:User)" in cypher
        assert "[:FOLLOWS]" in cypher
        assert "(b:User)" in cypher
        assert "RETURN a, b" in cypher

    def test_match_with_where_equals(self):
        """Test compiling WHERE with equals"""
        dsl = "MATCH (u:User) WHERE u.age = 30 RETURN u.name"
        statement = self.parser.parse(dsl)
        cypher = self.compiler.compile(statement)

        assert "WHERE" in cypher
        assert "u.age = 30" in cypher or "u.age = '30'" in cypher
        assert "RETURN u.name" in cypher

    def test_match_with_where_greater_than(self):
        """Test compiling WHERE with greater than"""
        dsl = "MATCH (u:User) WHERE u.age > 30 RETURN u.name"
        statement = self.parser.parse(dsl)
        cypher = self.compiler.compile(statement)

        assert "WHERE" in cypher
        assert "u.age > 30" in cypher
        assert "RETURN u.name" in cypher

    def test_match_with_where_not_equal(self):
        """Test compiling WHERE with not equals (converts to <>)"""
        dsl = "MATCH (u:User) WHERE u.status != 'active' RETURN u"
        statement = self.parser.parse(dsl)
        cypher = self.compiler.compile(statement)

        assert "WHERE" in cypher
        # != should be converted to <>
        assert "<>" in cypher

    def test_match_with_where_and(self):
        """Test compiling WHERE with AND"""
        dsl = "MATCH (u:User) WHERE u.age > 30 AND u.city = 'NYC' RETURN u"
        statement = self.parser.parse(dsl)
        cypher = self.compiler.compile(statement)

        assert "WHERE" in cypher
        assert "AND" in cypher
        assert "u.age > 30" in cypher

    def test_match_with_where_or(self):
        """Test compiling WHERE with OR"""
        dsl = "MATCH (u:User) WHERE u.age > 30 OR u.city = 'NYC' RETURN u"
        statement = self.parser.parse(dsl)
        cypher = self.compiler.compile(statement)

        assert "WHERE" in cypher
        assert "OR" in cypher

    def test_match_multiple_patterns(self):
        """Test compiling multiple patterns"""
        dsl = "MATCH (a)-[]->(b), (b)-[]->(c) RETURN a, b, c"
        statement = self.parser.parse(dsl)
        cypher = self.compiler.compile(statement)

        assert "MATCH" in cypher
        assert "(a)" in cypher
        assert "(b)" in cypher
        assert "(c)" in cypher
        # Should have comma separating patterns
        assert "," in cypher

    def test_reverse_edge_direction(self):
        """Test compiling reverse edge direction"""
        dsl = "MATCH (a)<-[:FOLLOWS]-(b) RETURN a, b"
        statement = self.parser.parse(dsl)
        cypher = self.compiler.compile(statement)

        assert "<-[:FOLLOWS]-" in cypher

    def test_forward_edge_direction(self):
        """Test compiling forward edge direction"""
        dsl = "MATCH (a)-[:FOLLOWS]->(b) RETURN a, b"
        statement = self.parser.parse(dsl)
        cypher = self.compiler.compile(statement)

        assert "-[:FOLLOWS]->" in cypher

    def test_bidirectional_edge(self):
        """Test compiling bidirectional edge"""
        dsl = "MATCH (a)-[:KNOWS]-(b) RETURN a, b"
        statement = self.parser.parse(dsl)
        cypher = self.compiler.compile(statement)

        assert "-[:KNOWS]-" in cypher
        # Should not have directional arrows
        assert "-[:KNOWS]->" not in cypher
        assert "<-[:KNOWS]-" not in cypher

    def test_return_property_reference(self):
        """Test compiling property reference in RETURN"""
        dsl = "MATCH (u:User) RETURN u.name, u.age"
        statement = self.parser.parse(dsl)
        cypher = self.compiler.compile(statement)

        assert "RETURN u.name, u.age" in cypher

    def test_string_literal_escaping(self):
        """Test string literals are properly quoted"""
        dsl = "MATCH (u:User) WHERE u.name = 'Alice' RETURN u"
        statement = self.parser.parse(dsl)
        cypher = self.compiler.compile(statement)

        assert "'Alice'" in cypher

    def test_multi_label_node(self):
        """Test node with multiple labels"""
        dsl = "MATCH (u:User:Person) RETURN u"
        statement = self.parser.parse(dsl)
        cypher = self.compiler.compile(statement)

        assert "(u:User:Person)" in cypher

    def test_edge_with_variable(self):
        """Test edge with variable name"""
        dsl = "MATCH (a)-[rel:FOLLOWS]->(b) RETURN rel"
        statement = self.parser.parse(dsl)
        cypher = self.compiler.compile(statement)

        assert "[rel:FOLLOWS]" in cypher

    def test_comparison_operators(self):
        """Test all comparison operators compile correctly"""
        test_cases = [
            ("u.age = 30", "u.age = 30"),
            ("u.age != 30", "u.age <> 30"),  # != converts to <>
            ("u.age > 30", "u.age > 30"),
            ("u.age >= 30", "u.age >= 30"),
            ("u.age < 30", "u.age < 30"),
            ("u.age <= 30", "u.age <= 30"),
        ]

        for dsl_where, expected_cypher_where in test_cases:
            dsl = f"MATCH (u:User) WHERE {dsl_where} RETURN u"
            statement = self.parser.parse(dsl)
            cypher = self.compiler.compile(statement)
            assert expected_cypher_where in cypher, f"Failed for {dsl_where}"

    def test_complex_pattern_compilation(self):
        """Test complex multi-hop pattern compilation"""
        dsl = """MATCH (a:User)-[:FOLLOWS]->(b:User)-[:POSTS]->(c:Post)
                 WHERE a.age > 25 AND c.likes > 100
                 RETURN a.name, b.name, c.title"""

        statement = self.parser.parse(dsl)
        cypher = self.compiler.compile(statement)

        # Verify structure
        assert "(a:User)" in cypher
        assert "[:FOLLOWS]" in cypher
        assert "(b:User)" in cypher
        assert "[:POSTS]" in cypher
        assert "(c:Post)" in cypher
        assert "WHERE" in cypher
        assert "AND" in cypher
        assert "RETURN a.name, b.name, c.title" in cypher

    def test_film_director_compilation(self):
        """Test film director pattern compilation"""
        dsl = """MATCH (A:Film)-[:directFilm]-(B:FilmDirector)
                 WHERE B.birthDate > '1980'
                 RETURN B.name"""

        statement = self.parser.parse(dsl)
        cypher = self.compiler.compile(statement)

        assert "(A:Film)" in cypher
        assert "[:directFilm]" in cypher
        assert "(B:FilmDirector)" in cypher
        assert "B.birthDate > '1980'" in cypher
        assert "RETURN B.name" in cypher

    def test_mutual_followers_compilation(self):
        """Test mutual followers pattern compilation"""
        dsl = "MATCH (a:User)-[:FOLLOWS]->(b:User)-[:FOLLOWS]->(a) RETURN a.name, b.name"
        statement = self.parser.parse(dsl)
        cypher = self.compiler.compile(statement)

        # Should have proper cycle pattern
        assert "(a:User)" in cypher
        assert "[:FOLLOWS]" in cypher
        assert "(b:User)" in cypher
        # Second edge should point back to (a)
        assert cypher.count("(a") == 2 or cypher.count("(a:") == 1  # One definition, one reference

    def test_property_comparison(self):
        """Test property-to-property comparison"""
        dsl = "MATCH (a:User)-[]->(b:User) WHERE a.age > b.age RETURN a, b"
        statement = self.parser.parse(dsl)
        cypher = self.compiler.compile(statement)

        assert "a.age > b.age" in cypher

    def test_multiple_return_items(self):
        """Test multiple return items"""
        dsl = "MATCH (u:User) RETURN u.id, u.name, u.email, u.age"
        statement = self.parser.parse(dsl)
        cypher = self.compiler.compile(statement)

        assert "RETURN u.id, u.name, u.email, u.age" in cypher

    def test_integer_literal(self):
        """Test integer literal formatting"""
        dsl = "MATCH (u:User) WHERE u.age = 30 RETURN u"
        statement = self.parser.parse(dsl)
        cypher = self.compiler.compile(statement)

        assert "u.age = 30" in cypher
        # Should not have quotes around integer
        assert "u.age = '30'" not in cypher

    def test_float_literal(self):
        """Test float literal formatting"""
        dsl = "MATCH (u:User) WHERE u.rating = 4.5 RETURN u"
        statement = self.parser.parse(dsl)
        cypher = self.compiler.compile(statement)

        assert "4.5" in cypher

    def test_boolean_literal(self):
        """Test boolean literal formatting"""
        dsl = "MATCH (u:User) WHERE u.active = true RETURN u"
        statement = self.parser.parse(dsl)
        cypher = self.compiler.compile(statement)

        # Cypher uses lowercase true/false
        assert "true" in cypher.lower()

    def test_three_hop_pattern(self):
        """Test three-hop pattern compilation"""
        dsl = "MATCH (a)-[:REL1]->(b)-[:REL2]->(c)-[:REL3]->(d) RETURN a, d"
        statement = self.parser.parse(dsl)
        cypher = self.compiler.compile(statement)

        assert "(a)" in cypher
        assert "[:REL1]" in cypher
        assert "(b)" in cypher
        assert "[:REL2]" in cypher
        assert "(c)" in cypher
        assert "[:REL3]" in cypher
        assert "(d)" in cypher

    def test_parallel_patterns(self):
        """Test parallel pattern matching"""
        dsl = "MATCH (a:User), (b:Post) WHERE a.id = 1 AND b.id = 2 RETURN a, b"
        statement = self.parser.parse(dsl)
        cypher = self.compiler.compile(statement)

        assert "(a:User)" in cypher
        assert "(b:Post)" in cypher
        assert "," in cypher  # Comma separating patterns

    def test_no_labels_or_types(self):
        """Test pattern without labels or types"""
        dsl = "MATCH (a)-[]->(b) RETURN a, b"
        statement = self.parser.parse(dsl)
        cypher = self.compiler.compile(statement)

        assert "(a)" in cypher
        assert "(b)" in cypher
        # Should have edge without type
        assert "-[]->" in cypher or "[]" in cypher


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
