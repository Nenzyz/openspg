"""Memgraph storage adapter implementation."""

import uuid
from typing import Any, Dict, List, Optional
from neo4j import GraphDatabase, Driver
from graphspg.storage.base import StorageAdapter


class MemgraphAdapter(StorageAdapter):
    """Memgraph database adapter using Neo4j driver."""

    def __init__(self, uri: str, user: str = "", password: str = ""):
        """Initialize Memgraph adapter.

        Args:
            uri: Memgraph connection URI (e.g., "bolt://localhost:7687")
            user: Username (optional for Memgraph)
            password: Password (optional for Memgraph)
        """
        self.uri = uri
        self.user = user
        self.password = password
        self.driver: Optional[Driver] = None

    def connect(self):
        """Establish connection to Memgraph."""
        auth = (self.user, self.password) if self.user else None
        self.driver = GraphDatabase.driver(self.uri, auth=auth)
        # Test connection
        with self.driver.session() as session:
            session.run("RETURN 1")

    def close(self):
        """Close connection to Memgraph."""
        if self.driver:
            self.driver.close()
            self.driver = None

    def create_vertex(
        self,
        labels: List[str],
        properties: Dict[str, Any],
        vertex_id: Optional[str] = None
    ) -> str:
        """Create a vertex in Memgraph.

        Args:
            labels: List of labels for the vertex
            properties: Vertex properties
            vertex_id: Optional custom ID (generated if not provided)

        Returns:
            Vertex ID
        """
        if not self.driver:
            raise RuntimeError("Not connected to database")

        vertex_id = vertex_id or str(uuid.uuid4())
        labels_str = ':'.join(labels)
        properties_with_id = {**properties, 'id': vertex_id}

        with self.driver.session() as session:
            query = f"""
            CREATE (n:{labels_str})
            SET n = $properties
            RETURN n.id AS id
            """
            result = session.run(query, properties=properties_with_id)
            record = result.single()
            return record["id"]

    def create_edge(
        self,
        source_id: str,
        target_id: str,
        edge_type: str,
        properties: Optional[Dict[str, Any]] = None
    ) -> str:
        """Create an edge in Memgraph.

        Args:
            source_id: Source vertex ID
            target_id: Target vertex ID
            edge_type: Edge type/label
            properties: Optional edge properties

        Returns:
            Edge ID (generated)
        """
        if not self.driver:
            raise RuntimeError("Not connected to database")

        edge_id = str(uuid.uuid4())
        props = properties or {}
        props['id'] = edge_id

        with self.driver.session() as session:
            query = f"""
            MATCH (source {{id: $source_id}})
            MATCH (target {{id: $target_id}})
            CREATE (source)-[r:{edge_type}]->(target)
            SET r = $properties
            RETURN r.id AS id
            """
            result = session.run(
                query,
                source_id=source_id,
                target_id=target_id,
                properties=props
            )
            record = result.single()
            return record["id"]

    def get_vertex(self, vertex_id: str) -> Optional[Dict[str, Any]]:
        """Get vertex by ID.

        Args:
            vertex_id: Vertex ID

        Returns:
            Vertex data or None if not found
        """
        if not self.driver:
            raise RuntimeError("Not connected to database")

        with self.driver.session() as session:
            query = """
            MATCH (n {id: $vertex_id})
            RETURN n, labels(n) AS labels
            """
            result = session.run(query, vertex_id=vertex_id)
            record = result.single()

            if not record:
                return None

            node = record["n"]
            labels = record["labels"]

            return {
                "id": vertex_id,
                "labels": labels,
                "properties": dict(node)
            }

    def update_vertex(self, vertex_id: str, properties: Dict[str, Any]) -> bool:
        """Update vertex properties.

        Args:
            vertex_id: Vertex ID
            properties: Properties to update

        Returns:
            True if updated, False if not found
        """
        if not self.driver:
            raise RuntimeError("Not connected to database")

        with self.driver.session() as session:
            query = """
            MATCH (n {id: $vertex_id})
            SET n += $properties
            RETURN n.id AS id
            """
            result = session.run(query, vertex_id=vertex_id, properties=properties)
            return result.single() is not None

    def delete_vertex(self, vertex_id: str) -> bool:
        """Delete vertex by ID.

        Args:
            vertex_id: Vertex ID

        Returns:
            True if deleted, False if not found
        """
        if not self.driver:
            raise RuntimeError("Not connected to database")

        with self.driver.session() as session:
            query = """
            MATCH (n {id: $vertex_id})
            DETACH DELETE n
            RETURN count(n) AS deleted
            """
            result = session.run(query, vertex_id=vertex_id)
            record = result.single()
            return record["deleted"] > 0

    def execute_query(
        self,
        query: str,
        parameters: Optional[Dict[str, Any]] = None
    ) -> List[Dict[str, Any]]:
        """Execute a Cypher query.

        Args:
            query: Cypher query string
            parameters: Query parameters

        Returns:
            List of result records
        """
        if not self.driver:
            raise RuntimeError("Not connected to database")

        with self.driver.session() as session:
            result = session.run(query, parameters or {})
            records = []
            for record in result:
                records.append(dict(record))
            return records

    def create_index(self, label: str, property_name: str):
        """Create an index on a label and property.

        Args:
            label: Node label
            property_name: Property name to index
        """
        if not self.driver:
            raise RuntimeError("Not connected to database")

        with self.driver.session() as session:
            query = f"CREATE INDEX ON :{label}({property_name})"
            session.run(query)

    def clear_database(self):
        """Clear all data from the database."""
        if not self.driver:
            raise RuntimeError("Not connected to database")

        with self.driver.session() as session:
            session.run("MATCH (n) DETACH DELETE n")

    def __enter__(self):
        """Context manager entry."""
        self.connect()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit."""
        self.close()
