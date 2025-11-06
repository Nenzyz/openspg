"""Compiler to convert DSL AST to Cypher queries."""

from typing import Any, Dict, List
from graphspg.dsl.ast import (
    AggregateExpr,
    BinaryExpr,
    BinaryOp,
    DefineStatement,
    EdgePattern,
    Literal,
    MatchStatement,
    NodePattern,
    PathPattern,
    PropertyRef,
    Statement,
    StatementType,
    VariableRef,
)


class CypherCompiler:
    """Compile DSL AST to Cypher query."""

    def compile(self, statement: Statement) -> str:
        """Compile statement to Cypher."""
        if statement.type == StatementType.MATCH:
            return self._compile_match(statement.body)
        elif statement.type == StatementType.DEFINE:
            return self._compile_define(statement.body)
        else:
            raise ValueError(f"Unknown statement type: {statement.type}")

    def _compile_match(self, match_stmt: MatchStatement) -> str:
        """Compile MATCH statement to Cypher."""
        parts = []

        # MATCH clause
        patterns = [self._compile_path_pattern(p) for p in match_stmt.patterns]
        parts.append(f"MATCH {', '.join(patterns)}")

        # WHERE clause
        if match_stmt.where:
            condition = self._compile_expr(match_stmt.where.condition)
            parts.append(f"WHERE {condition}")

        # RETURN clause
        if match_stmt.return_clause:
            items = [self._compile_expr(item) for item in match_stmt.return_clause.items]
            parts.append(f"RETURN {', '.join(items)}")

        return '\n'.join(parts)

    def _compile_define(self, define_stmt: DefineStatement) -> str:
        """Compile DEFINE statement to a Cypher query that creates derived relations.

        DEFINE (a:User)-[:IS_ACTIVE]->(b:App) WHERE a.loginCount > 10

        becomes:

        MATCH (a:User), (b:App)
        WHERE a.loginCount > 10
        CREATE (a)-[:IS_ACTIVE]->(b)
        """
        pattern = define_stmt.pattern

        # Extract nodes and edge from pattern
        nodes = []
        edge = None
        for elem in pattern.elements:
            if isinstance(elem, NodePattern):
                nodes.append(elem)
            elif isinstance(elem, EdgePattern):
                edge = elem

        if len(nodes) != 2 or edge is None:
            raise ValueError("DEFINE requires exactly 2 nodes and 1 edge")

        # Build MATCH clause for nodes
        node_patterns = [self._compile_node_pattern(n) for n in nodes]
        match_clause = f"MATCH {', '.join(node_patterns)}"

        # Build WHERE clause
        where_clause = ""
        if define_stmt.where:
            condition = self._compile_expr(define_stmt.where.condition)
            where_clause = f"WHERE {condition}"

        # Build CREATE clause for the derived relation
        source_var = nodes[0].variable
        target_var = nodes[1].variable
        edge_type = edge.types[0] if edge.types else "DERIVED"

        create_clause = f"CREATE ({source_var})-[:{edge_type}]->({target_var})"

        parts = [match_clause]
        if where_clause:
            parts.append(where_clause)
        parts.append(create_clause)

        return '\n'.join(parts)

    def _compile_path_pattern(self, pattern: PathPattern) -> str:
        """Compile path pattern to Cypher."""
        result = ""
        for elem in pattern.elements:
            if isinstance(elem, NodePattern):
                result += self._compile_node_pattern(elem)
            elif isinstance(elem, EdgePattern):
                result += self._compile_edge_pattern(elem)
        return result

    def _compile_node_pattern(self, node: NodePattern) -> str:
        """Compile node pattern to Cypher."""
        labels = ':'.join(node.labels) if node.labels else ''
        if labels:
            labels = ':' + labels

        props = []
        for key, value in node.properties.items():
            props.append(f"{key}: {self._format_literal(value)}")
        props_str = ', '.join(props)
        if props_str:
            props_str = ' {' + props_str + '}'

        return f"({node.variable}{labels}{props_str})"

    def _compile_edge_pattern(self, edge: EdgePattern) -> str:
        """Compile edge pattern to Cypher."""
        var = edge.variable if edge.variable else ''
        types = '|'.join(edge.types) if edge.types else ''
        if types:
            types = ':' + types

        props = []
        for key, value in edge.properties.items():
            props.append(f"{key}: {self._format_literal(value)}")
        props_str = ', '.join(props)
        if props_str:
            props_str = ' {' + props_str + '}'

        edge_str = f"[{var}{types}{props_str}]"

        if edge.direction == "->":
            return f"-{edge_str}->"
        elif edge.direction == "<-":
            return f"<-{edge_str}-"
        else:
            return f"-{edge_str}-"

    def _compile_expr(self, expr: Any) -> str:
        """Compile expression to Cypher."""
        if isinstance(expr, BinaryExpr):
            left = self._compile_expr(expr.left)
            right = self._compile_expr(expr.right)
            op = self._binary_op_to_cypher(expr.op)
            return f"({left} {op} {right})"
        elif isinstance(expr, PropertyRef):
            return f"{expr.variable}.{expr.property}"
        elif isinstance(expr, VariableRef):
            return expr.name
        elif isinstance(expr, Literal):
            return self._format_literal(expr.value)
        elif isinstance(expr, AggregateExpr):
            inner = self._compile_expr(expr.expr)
            return f"{expr.op.value}({inner})"
        else:
            raise ValueError(f"Unknown expression type: {type(expr)}")

    def _binary_op_to_cypher(self, op: BinaryOp) -> str:
        """Convert binary operator to Cypher syntax."""
        mapping = {
            BinaryOp.EQ: "=",
            BinaryOp.NEQ: "<>",
            BinaryOp.GT: ">",
            BinaryOp.GTE: ">=",
            BinaryOp.LT: "<",
            BinaryOp.LTE: "<=",
            BinaryOp.AND: "AND",
            BinaryOp.OR: "OR",
            BinaryOp.IN: "IN",
        }
        return mapping.get(op, op.value)

    def _format_literal(self, value: Any) -> str:
        """Format literal value for Cypher."""
        if isinstance(value, str):
            # Escape single quotes
            escaped = value.replace("'", "\\'")
            return f"'{escaped}'"
        elif isinstance(value, bool):
            return "true" if value else "false"
        elif isinstance(value, (int, float)):
            return str(value)
        elif isinstance(value, list):
            items = [self._format_literal(v) for v in value]
            return f"[{', '.join(items)}]"
        else:
            return str(value)
