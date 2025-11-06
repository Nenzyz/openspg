"""Example queries for the GraphSPG social network."""

import sys
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from graphspg.storage.memgraph import MemgraphAdapter
from graphspg.engine.executor import QueryExecutor
from graphspg.dsl.parser import DSLParser
from graphspg.engine.compiler import CypherCompiler


def print_results(title: str, results: list, compiled_query: str = None):
    """Print query results."""
    print(f"\n{'=' * 80}")
    print(f" {title}")
    print(f"{'=' * 80}")

    if compiled_query:
        print("\nCompiled Cypher:")
        print(compiled_query)
        print()

    print(f"Results ({len(results)} rows):")
    for i, row in enumerate(results, 1):
        print(f"\n{i}. {row}")


def run_example_queries():
    """Run example queries against the social network."""

    # Connect to Memgraph
    storage = MemgraphAdapter(uri="bolt://localhost:7687")
    storage.connect()
    print("✓ Connected to Memgraph")

    executor = QueryExecutor(storage=storage)

    try:
        # Example 1: Find all users who follow Alice
        print("\n" + "=" * 80)
        print(" EXAMPLE QUERIES")
        print("=" * 80)

        query1 = """
        MATCH (u:User)-[:FOLLOWS]->(alice:User)
        WHERE alice.name = 'Alice Johnson'
        RETURN u.name, u.city
        """
        compiled1 = executor.get_compiled_query(query1)
        results1 = executor.execute(query1)
        print_results("Example 1: Users who follow Alice", results1, compiled1)

        # Example 2: Find users older than 30
        query2 = """
        MATCH (u:User)
        WHERE u.age > 30
        RETURN u.name, u.age, u.city
        """
        compiled2 = executor.get_compiled_query(query2)
        results2 = executor.execute(query2)
        print_results("Example 2: Users older than 30", results2, compiled2)

        # Example 3: Find posts liked by users from San Francisco
        query3 = """
        MATCH (u:User)-[:LIKES]->(p:Post)
        WHERE u.city = 'San Francisco'
        RETURN p.title, p.likes, u.name
        """
        compiled3 = executor.get_compiled_query(query3)
        results3 = executor.execute(query3)
        print_results("Example 3: Posts liked by SF users", results3, compiled3)

        # Example 4: Find mutual followers (users who follow each other)
        query4 = """
        MATCH (a:User)-[:FOLLOWS]->(b:User)-[:FOLLOWS]->(a)
        RETURN a.name, b.name
        """
        compiled4 = executor.get_compiled_query(query4)
        results4 = executor.execute(query4)
        print_results("Example 4: Mutual followers", results4, compiled4)

        # Example 5: Find groups and their members
        query5 = """
        MATCH (u:User)-[:MEMBER_OF]->(g:Group)
        RETURN g.name, u.name
        """
        compiled5 = executor.get_compiled_query(query5)
        results5 = executor.execute(query5)
        print_results("Example 5: Groups and their members", results5, compiled5)

        # Example 6: Find users who posted content that got more than 20 likes
        query6 = """
        MATCH (u:User)-[:POSTED]->(p:Post)
        WHERE p.likes > 20
        RETURN u.name, p.title, p.likes
        """
        compiled6 = executor.get_compiled_query(query6)
        results6 = executor.execute(query6)
        print_results("Example 6: Users with popular posts (>20 likes)", results6, compiled6)

        # Example 7: Find users in the same city
        query7 = """
        MATCH (u1:User)
        MATCH (u2:User)
        WHERE u1.city = 'San Francisco' AND u2.city = 'San Francisco'
        RETURN u1.name, u2.name
        """
        compiled7 = executor.get_compiled_query(query7)
        results7 = executor.execute(query7)
        print_results("Example 7: Users in San Francisco", results7, compiled7)

        # Example 8: Complex pattern - Find users who follow someone in a specific group
        query8 = """
        MATCH (u:User)-[:FOLLOWS]->(f:User)-[:MEMBER_OF]->(g:Group)
        WHERE g.name = 'AI Enthusiasts'
        RETURN u.name, f.name, g.name
        """
        compiled8 = executor.get_compiled_query(query8)
        results8 = executor.execute(query8)
        print_results(
            "Example 8: Users following members of 'AI Enthusiasts'",
            results8,
            compiled8
        )

        # Example 9: Using raw Cypher for aggregation
        print("\n" + "=" * 80)
        print(" RAW CYPHER QUERIES (Advanced)")
        print("=" * 80)

        cypher_query1 = """
        MATCH (u:User)-[:POSTED]->(p:Post)
        RETURN u.name AS author, count(p) AS post_count
        ORDER BY post_count DESC
        """
        results9 = executor.execute_cypher(cypher_query1)
        print_results("Example 9: Post count by user (Cypher)", results9, cypher_query1)

        # Example 10: Find influencers (users with most followers)
        cypher_query2 = """
        MATCH (u:User)<-[:FOLLOWS]-(follower:User)
        RETURN u.name AS user, count(follower) AS follower_count
        ORDER BY follower_count DESC
        LIMIT 3
        """
        results10 = executor.execute_cypher(cypher_query2)
        print_results("Example 10: Top influencers (Cypher)", results10, cypher_query2)

        # Example 11: Friend recommendations (friends of friends who you don't follow)
        cypher_query3 = """
        MATCH (me:User {name: 'Alice Johnson'})-[:FOLLOWS]->(friend:User)-[:FOLLOWS]->(fof:User)
        WHERE NOT (me)-[:FOLLOWS]->(fof) AND me <> fof
        RETURN DISTINCT fof.name AS recommended_user, count(friend) AS common_friends
        ORDER BY common_friends DESC
        """
        results11 = executor.execute_cypher(cypher_query3)
        print_results(
            "Example 11: Friend recommendations for Alice (Cypher)",
            results11,
            cypher_query3
        )

        print("\n" + "=" * 80)
        print(" ✓ All queries executed successfully!")
        print("=" * 80 + "\n")

    finally:
        storage.close()


if __name__ == "__main__":
    run_example_queries()
