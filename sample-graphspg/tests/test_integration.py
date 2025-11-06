"""
Integration tests with Memgraph ported from OpenSPG.

These tests require a running Memgraph instance.
Run with: pytest test_integration.py --memgraph-uri bolt://localhost:7687
"""

import pytest
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from graphspg.storage.memgraph import MemgraphAdapter
from graphspg.engine.executor import QueryExecutor


# Mark all tests as requiring memgraph
pytestmark = pytest.mark.memgraph


@pytest.fixture(scope="module")
def memgraph_uri(request):
    """Get Memgraph URI from command line or use default."""
    return request.config.getoption(
        "--memgraph-uri",
        default="bolt://localhost:7687"
    )


@pytest.fixture(scope="module")
def storage(memgraph_uri):
    """Create Memgraph storage adapter."""
    try:
        adapter = MemgraphAdapter(uri=memgraph_uri)
        adapter.connect()
        yield adapter
        adapter.close()
    except Exception as e:
        pytest.skip(f"Memgraph not available: {e}")


@pytest.fixture(scope="module")
def executor(storage):
    """Create query executor."""
    return QueryExecutor(storage=storage)


@pytest.fixture(autouse=True)
def clean_database(storage):
    """Clean database before each test."""
    storage.clear_database()
    yield
    storage.clear_database()


class TestMemgraphIntegration:
    """Integration tests with real Memgraph database."""

    def test_create_and_query_single_node(self, storage, executor):
        """Test creating and querying a single node"""
        # Create node
        user_id = storage.create_vertex(
            labels=["User"],
            properties={"name": "Alice", "age": 28}
        )

        # Query using DSL
        results = executor.execute("MATCH (u:User) RETURN u")

        assert len(results) == 1
        assert results[0]["u"]["name"] == "Alice"

    def test_create_and_query_relationship(self, storage, executor):
        """Test creating and querying relationships"""
        # Create nodes
        alice_id = storage.create_vertex(
            labels=["User"],
            properties={"name": "Alice", "age": 28}
        )
        bob_id = storage.create_vertex(
            labels=["User"],
            properties={"name": "Bob", "age": 32}
        )

        # Create relationship
        storage.create_edge(
            source_id=alice_id,
            target_id=bob_id,
            edge_type="FOLLOWS"
        )

        # Query
        results = executor.execute(
            "MATCH (a:User)-[:FOLLOWS]->(b:User) RETURN a.name, b.name"
        )

        assert len(results) == 1
        assert results[0]["a.name"] == "Alice"
        assert results[0]["b.name"] == "Bob"

    def test_where_clause_filtering(self, storage, executor):
        """Test WHERE clause filtering"""
        # Create multiple users
        for name, age in [("Alice", 25), ("Bob", 35), ("Carol", 30)]:
            storage.create_vertex(
                labels=["User"],
                properties={"name": name, "age": age}
            )

        # Query with WHERE clause
        results = executor.execute(
            "MATCH (u:User) WHERE u.age > 28 RETURN u.name"
        )

        assert len(results) == 2
        names = [r["u.name"] for r in results]
        assert "Bob" in names
        assert "Carol" in names
        assert "Alice" not in names

    def test_two_hop_traversal(self, storage, executor):
        """Test two-hop graph traversal"""
        # Create chain: A -> B -> C
        a_id = storage.create_vertex(labels=["User"], properties={"name": "A"})
        b_id = storage.create_vertex(labels=["User"], properties={"name": "B"})
        c_id = storage.create_vertex(labels=["User"], properties={"name": "C"})

        storage.create_edge(a_id, b_id, "KNOWS")
        storage.create_edge(b_id, c_id, "KNOWS")

        # Query two-hop pattern
        results = executor.execute(
            "MATCH (a)-[:KNOWS]->(b)-[:KNOWS]->(c) RETURN a.name, b.name, c.name"
        )

        assert len(results) == 1
        assert results[0]["a.name"] == "A"
        assert results[0]["b.name"] == "B"
        assert results[0]["c.name"] == "C"

    def test_mutual_relationships(self, storage, executor):
        """Test finding mutual relationships"""
        # Create A <-> B mutual follow
        a_id = storage.create_vertex(labels=["User"], properties={"name": "Alice"})
        b_id = storage.create_vertex(labels=["User"], properties={"name": "Bob"})

        storage.create_edge(a_id, b_id, "FOLLOWS")
        storage.create_edge(b_id, a_id, "FOLLOWS")

        # Query mutual follows
        results = executor.execute(
            "MATCH (a:User)-[:FOLLOWS]->(b:User)-[:FOLLOWS]->(a) RETURN a.name, b.name"
        )

        assert len(results) == 1
        # Could be either direction
        names = {results[0]["a.name"], results[0]["b.name"]}
        assert names == {"Alice", "Bob"}

    def test_complex_where_conditions(self, storage, executor):
        """Test complex WHERE conditions with AND/OR"""
        # Create users
        users = [
            {"name": "Alice", "age": 25, "city": "NYC"},
            {"name": "Bob", "age": 35, "city": "SF"},
            {"name": "Carol", "age": 30, "city": "NYC"},
            {"name": "David", "age": 40, "city": "LA"},
        ]

        for user in users:
            storage.create_vertex(labels=["User"], properties=user)

        # Query with complex condition
        results = executor.execute(
            "MATCH (u:User) WHERE u.age > 28 AND u.city = 'NYC' RETURN u.name"
        )

        assert len(results) == 1
        assert results[0]["u.name"] == "Carol"

    def test_film_director_pattern(self, storage, executor):
        """Test film-director pattern from OpenSPG examples"""
        # Create film and director
        film_id = storage.create_vertex(
            labels=["Film"],
            properties={"title": "Inception"}
        )
        director_id = storage.create_vertex(
            labels=["FilmDirector"],
            properties={"name": "Nolan", "birthDate": "1985"}
        )

        # Create relationship
        storage.create_edge(film_id, director_id, "directFilm")

        # Query
        results = executor.execute(
            "MATCH (f:Film)-[:directFilm]-(d:FilmDirector) WHERE d.birthDate > '1980' RETURN d.name"
        )

        assert len(results) == 1
        assert results[0]["d.name"] == "Nolan"

    def test_property_comparison(self, storage, executor):
        """Test property-to-property comparison"""
        # Create users with followers
        alice_id = storage.create_vertex(
            labels=["User"],
            properties={"name": "Alice", "followerCount": 100}
        )
        bob_id = storage.create_vertex(
            labels=["User"],
            properties={"name": "Bob", "followerCount": 50}
        )
        carol_id = storage.create_vertex(
            labels=["User"],
            properties={"name": "Carol", "followerCount": 150}
        )

        storage.create_edge(alice_id, bob_id, "KNOWS")
        storage.create_edge(alice_id, carol_id, "KNOWS")

        # Find connections where source has fewer followers than target
        results = executor.execute(
            "MATCH (a:User)-[:KNOWS]->(b:User) WHERE a.followerCount < b.followerCount RETURN b.name"
        )

        assert len(results) == 1
        assert results[0]["b.name"] == "Carol"

    def test_multiple_patterns(self, storage, executor):
        """Test query with multiple independent patterns"""
        # Create separate subgraphs
        user1 = storage.create_vertex(labels=["User"], properties={"name": "Alice"})
        user2 = storage.create_vertex(labels=["User"], properties={"name": "Bob"})

        post1 = storage.create_vertex(labels=["Post"], properties={"title": "Post1"})
        post2 = storage.create_vertex(labels=["Post"], properties={"title": "Post2"})

        # Create relationships
        storage.create_edge(user1, post1, "POSTED")
        storage.create_edge(user2, post2, "POSTED")

        # Query both patterns
        results = executor.execute(
            "MATCH (u:User)-[:POSTED]->(p:Post) RETURN u.name, p.title"
        )

        assert len(results) == 2

    def test_reverse_edge_direction(self, storage, executor):
        """Test reverse edge direction matching"""
        a_id = storage.create_vertex(labels=["User"], properties={"name": "A"})
        b_id = storage.create_vertex(labels=["User"], properties={"name": "B"})

        # Create A -> B
        storage.create_edge(a_id, b_id, "FOLLOWS")

        # Query with reverse direction: B <- A
        results = executor.execute(
            "MATCH (a:User)<-[:FOLLOWS]-(b:User) RETURN a.name, b.name"
        )

        assert len(results) == 1
        assert results[0]["a.name"] == "B"
        assert results[0]["b.name"] == "A"

    def test_bidirectional_matching(self, storage, executor):
        """Test bidirectional edge matching"""
        a_id = storage.create_vertex(labels=["User"], properties={"name": "A"})
        b_id = storage.create_vertex(labels=["User"], properties={"name": "B"})

        # Create A -> B
        storage.create_edge(a_id, b_id, "KNOWS")

        # Query with no direction
        results = executor.execute(
            "MATCH (a:User)-[:KNOWS]-(b:User) RETURN a.name, b.name"
        )

        # Should match in both directions
        assert len(results) == 2

    def test_three_node_triangle(self, storage, executor):
        """Test triangle pattern: A -> B -> C, C -> A"""
        a_id = storage.create_vertex(labels=["User"], properties={"name": "A"})
        b_id = storage.create_vertex(labels=["User"], properties={"name": "B"})
        c_id = storage.create_vertex(labels=["User"], properties={"name": "C"})

        storage.create_edge(a_id, b_id, "KNOWS")
        storage.create_edge(b_id, c_id, "KNOWS")
        storage.create_edge(c_id, a_id, "KNOWS")

        # Query triangle
        results = executor.execute(
            "MATCH (a)-[:KNOWS]->(b)-[:KNOWS]->(c)-[:KNOWS]->(a) RETURN a.name"
        )

        assert len(results) == 1

    def test_cypher_aggregation(self, storage, executor):
        """Test raw Cypher aggregation query"""
        # Create users with posts
        alice_id = storage.create_vertex(labels=["User"], properties={"name": "Alice"})
        bob_id = storage.create_vertex(labels=["User"], properties={"name": "Bob"})

        for i in range(3):
            post_id = storage.create_vertex(labels=["Post"], properties={"id": i})
            storage.create_edge(alice_id, post_id, "POSTED")

        for i in range(5):
            post_id = storage.create_vertex(labels=["Post"], properties={"id": i + 10})
            storage.create_edge(bob_id, post_id, "POSTED")

        # Use raw Cypher for aggregation
        results = executor.execute_cypher(
            """
            MATCH (u:User)-[:POSTED]->(p:Post)
            RETURN u.name AS author, count(p) AS post_count
            ORDER BY post_count DESC
            """
        )

        assert len(results) == 2
        assert results[0]["post_count"] == 5
        assert results[0]["author"] == "Bob"
        assert results[1]["post_count"] == 3
        assert results[1]["author"] == "Alice"

    def test_no_results(self, storage, executor):
        """Test query with no matching results"""
        storage.create_vertex(labels=["User"], properties={"name": "Alice", "age": 25})

        results = executor.execute(
            "MATCH (u:User) WHERE u.age > 100 RETURN u"
        )

        assert len(results) == 0

    def test_multiple_labels_on_node(self, storage, executor):
        """Test node with multiple labels"""
        storage.create_vertex(
            labels=["User", "Admin"],
            properties={"name": "Alice"}
        )

        results = executor.execute(
            "MATCH (u:User:Admin) RETURN u.name"
        )

        assert len(results) == 1
        assert results[0]["u.name"] == "Alice"

    def test_edge_with_properties(self, storage, executor):
        """Test querying edge properties"""
        a_id = storage.create_vertex(labels=["User"], properties={"name": "Alice"})
        b_id = storage.create_vertex(labels=["User"], properties={"name": "Bob"})

        storage.create_edge(
            a_id,
            b_id,
            "KNOWS",
            properties={"since": "2020", "strength": 0.9}
        )

        # Query with edge variable to access properties
        results = executor.execute_cypher(
            """
            MATCH (a:User)-[r:KNOWS]->(b:User)
            RETURN a.name, b.name, r.since, r.strength
            """
        )

        assert len(results) == 1
        assert results[0]["r.since"] == "2020"
        assert results[0]["r.strength"] == 0.9


def pytest_addoption(parser):
    """Add custom command-line options."""
    parser.addoption(
        "--memgraph-uri",
        action="store",
        default="bolt://localhost:7687",
        help="Memgraph connection URI"
    )


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--memgraph-uri", "bolt://localhost:7687"])
