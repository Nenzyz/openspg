"""Query executor that orchestrates parsing, compilation, and execution."""

from typing import Any, Dict, List, Optional
from graphspg.dsl.parser import DSLParser
from graphspg.engine.compiler import CypherCompiler
from graphspg.storage.base import StorageAdapter
from graphspg.schema.registry import schema_registry


class QueryExecutor:
    """Execute DSL queries against storage."""

    def __init__(self, storage: StorageAdapter):
        """Initialize executor.

        Args:
            storage: Storage adapter to execute queries against
        """
        self.storage = storage
        self.parser = DSLParser()
        self.compiler = CypherCompiler()

    def execute(self, query: str, parameters: Optional[Dict[str, Any]] = None) -> List[Dict[str, Any]]:
        """Execute a DSL query.

        Args:
            query: DSL query string
            parameters: Optional query parameters

        Returns:
            List of result records
        """
        # Parse DSL to AST
        statement = self.parser.parse(query)

        # Compile AST to Cypher
        cypher_query = self.compiler.compile(statement)

        # Execute Cypher query
        results = self.storage.execute_query(cypher_query, parameters or {})

        return results

    def execute_cypher(
        self,
        query: str,
        parameters: Optional[Dict[str, Any]] = None
    ) -> List[Dict[str, Any]]:
        """Execute a raw Cypher query directly.

        Args:
            query: Cypher query string
            parameters: Optional query parameters

        Returns:
            List of result records
        """
        return self.storage.execute_query(query, parameters or {})

    def get_compiled_query(self, query: str) -> str:
        """Get the compiled Cypher query without executing it.

        Useful for debugging and understanding the compilation process.

        Args:
            query: DSL query string

        Returns:
            Compiled Cypher query
        """
        statement = self.parser.parse(query)
        return self.compiler.compile(statement)


class SchemaAwareExecutor(QueryExecutor):
    """Query executor with schema validation."""

    def execute(self, query: str, parameters: Optional[Dict[str, Any]] = None) -> List[Dict[str, Any]]:
        """Execute a DSL query with schema validation.

        Args:
            query: DSL query string
            parameters: Optional query parameters

        Returns:
            List of result records
        """
        # Get active schema
        schema = schema_registry.get_active()

        if schema:
            # Parse and validate against schema
            statement = self.parser.parse(query)
            # TODO: Add schema validation logic here
            # For now, just execute normally

        return super().execute(query, parameters)
