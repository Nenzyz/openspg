"""Sample social network data for demonstrating GraphSPG."""

import sys
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from graphspg.storage.memgraph import MemgraphAdapter
from graphspg.schema.models import (
    EntityType,
    Property,
    PropertyType,
    Relation,
    RelationConstraint,
    Schema,
)
from graphspg.schema.registry import schema_registry


def create_social_network_schema() -> Schema:
    """Create social network schema."""
    # Define entity types
    user_type = EntityType(
        name="User",
        description="Social network user",
        properties=[
            Property(name="name", type=PropertyType.STRING, required=True, indexed=True),
            Property(name="age", type=PropertyType.INTEGER, required=True),
            Property(name="email", type=PropertyType.STRING, required=True, indexed=True),
            Property(name="city", type=PropertyType.STRING),
            Property(name="interests", type=PropertyType.TEXT),
        ]
    )

    post_type = EntityType(
        name="Post",
        description="User post",
        properties=[
            Property(name="title", type=PropertyType.STRING, required=True),
            Property(name="content", type=PropertyType.TEXT, required=True),
            Property(name="created_at", type=PropertyType.DATETIME, required=True),
            Property(name="likes", type=PropertyType.INTEGER),
        ]
    )

    group_type = EntityType(
        name="Group",
        description="User group or community",
        properties=[
            Property(name="name", type=PropertyType.STRING, required=True, indexed=True),
            Property(name="description", type=PropertyType.TEXT),
            Property(name="member_count", type=PropertyType.INTEGER),
        ]
    )

    # Define relations
    follows_relation = Relation(
        name="FOLLOWS",
        source_type="User",
        target_type="User",
        description="User follows another user",
        constraint=RelationConstraint.MANY_TO_MANY,
    )

    posted_relation = Relation(
        name="POSTED",
        source_type="User",
        target_type="Post",
        description="User posted a post",
        constraint=RelationConstraint.ONE_TO_MANY,
    )

    member_of_relation = Relation(
        name="MEMBER_OF",
        source_type="User",
        target_type="Group",
        description="User is member of a group",
        constraint=RelationConstraint.MANY_TO_MANY,
        properties=[
            Property(name="joined_at", type=PropertyType.DATETIME),
            Property(name="role", type=PropertyType.STRING),
        ]
    )

    likes_relation = Relation(
        name="LIKES",
        source_type="User",
        target_type="Post",
        description="User likes a post",
        constraint=RelationConstraint.MANY_TO_MANY,
    )

    # Create schema
    schema = Schema(
        name="social_network",
        version="1.0.0",
        entity_types=[user_type, post_type, group_type],
        relations=[follows_relation, posted_relation, member_of_relation, likes_relation],
    )

    return schema


def load_sample_data(storage: MemgraphAdapter):
    """Load sample social network data."""
    print("Loading sample social network data...")

    # Clear existing data
    storage.clear_database()

    # Create users
    users = [
        {
            "id": "user1",
            "name": "Alice Johnson",
            "age": 28,
            "email": "alice@example.com",
            "city": "San Francisco",
            "interests": "AI, Machine Learning, Data Science"
        },
        {
            "id": "user2",
            "name": "Bob Smith",
            "age": 34,
            "email": "bob@example.com",
            "city": "New York",
            "interests": "Graph Databases, Backend Development"
        },
        {
            "id": "user3",
            "name": "Carol White",
            "age": 26,
            "email": "carol@example.com",
            "city": "San Francisco",
            "interests": "Frontend, UX Design, React"
        },
        {
            "id": "user4",
            "name": "David Brown",
            "age": 45,
            "email": "david@example.com",
            "city": "Seattle",
            "interests": "Cloud Architecture, DevOps"
        },
        {
            "id": "user5",
            "name": "Emma Davis",
            "age": 31,
            "email": "emma@example.com",
            "city": "New York",
            "interests": "Data Engineering, Distributed Systems"
        },
    ]

    for user_data in users:
        user_id = user_data.pop("id")
        storage.create_vertex(
            labels=["User"],
            properties=user_data,
            vertex_id=user_id
        )
        print(f"Created user: {user_data['name']}")

    # Create groups
    groups = [
        {
            "id": "group1",
            "name": "AI Enthusiasts",
            "description": "Group for AI and ML discussions",
            "member_count": 3
        },
        {
            "id": "group2",
            "name": "Graph Database Users",
            "description": "Community for graph database users",
            "member_count": 4
        },
        {
            "id": "group3",
            "name": "San Francisco Tech",
            "description": "Tech professionals in SF Bay Area",
            "member_count": 2
        },
    ]

    for group_data in groups:
        group_id = group_data.pop("id")
        storage.create_vertex(
            labels=["Group"],
            properties=group_data,
            vertex_id=group_id
        )
        print(f"Created group: {group_data['name']}")

    # Create posts
    posts = [
        {
            "id": "post1",
            "title": "Introduction to Knowledge Graphs",
            "content": "Knowledge graphs are powerful tools for representing complex relationships...",
            "created_at": "2024-01-15T10:30:00",
            "likes": 15
        },
        {
            "id": "post2",
            "title": "Building Scalable APIs",
            "content": "When building APIs at scale, consider these best practices...",
            "created_at": "2024-01-16T14:20:00",
            "likes": 23
        },
        {
            "id": "post3",
            "title": "Modern Frontend Architecture",
            "content": "Modern frontend development has evolved significantly...",
            "created_at": "2024-01-17T09:15:00",
            "likes": 18
        },
    ]

    for post_data in posts:
        post_id = post_data.pop("id")
        storage.create_vertex(
            labels=["Post"],
            properties=post_data,
            vertex_id=post_id
        )
        print(f"Created post: {post_data['title']}")

    # Create relationships
    print("\nCreating relationships...")

    # FOLLOWS relationships
    follows = [
        ("user1", "user2"),
        ("user1", "user3"),
        ("user2", "user1"),
        ("user2", "user4"),
        ("user3", "user1"),
        ("user4", "user2"),
        ("user4", "user5"),
        ("user5", "user2"),
        ("user5", "user4"),
    ]

    for source, target in follows:
        storage.create_edge(source, target, "FOLLOWS")
    print(f"Created {len(follows)} FOLLOWS relationships")

    # POSTED relationships
    posted = [
        ("user1", "post1"),
        ("user2", "post2"),
        ("user3", "post3"),
    ]

    for source, target in posted:
        storage.create_edge(source, target, "POSTED")
    print(f"Created {len(posted)} POSTED relationships")

    # MEMBER_OF relationships
    memberships = [
        ("user1", "group1", {"joined_at": "2023-12-01T00:00:00", "role": "admin"}),
        ("user1", "group3", {"joined_at": "2023-11-15T00:00:00", "role": "member"}),
        ("user2", "group2", {"joined_at": "2023-10-20T00:00:00", "role": "admin"}),
        ("user3", "group1", {"joined_at": "2024-01-05T00:00:00", "role": "member"}),
        ("user3", "group3", {"joined_at": "2023-12-10T00:00:00", "role": "member"}),
        ("user4", "group2", {"joined_at": "2023-11-01T00:00:00", "role": "moderator"}),
        ("user5", "group2", {"joined_at": "2023-12-15T00:00:00", "role": "member"}),
    ]

    for source, target, props in memberships:
        storage.create_edge(source, target, "MEMBER_OF", properties=props)
    print(f"Created {len(memberships)} MEMBER_OF relationships")

    # LIKES relationships
    likes = [
        ("user2", "post1"),
        ("user3", "post1"),
        ("user4", "post1"),
        ("user1", "post2"),
        ("user3", "post2"),
        ("user5", "post2"),
        ("user1", "post3"),
        ("user2", "post3"),
    ]

    for source, target in likes:
        storage.create_edge(source, target, "LIKES")
    print(f"Created {len(likes)} LIKES relationships")

    print("\n✓ Sample data loaded successfully!")


def main():
    """Main function to load sample data."""
    # Create schema
    schema = create_social_network_schema()
    schema_registry.register(schema, set_active=True)
    print(f"✓ Registered schema: {schema.name}")

    # Connect to Memgraph
    storage = MemgraphAdapter(uri="bolt://localhost:7687")
    storage.connect()
    print("✓ Connected to Memgraph")

    try:
        # Load sample data
        load_sample_data(storage)
    finally:
        storage.close()


if __name__ == "__main__":
    main()
