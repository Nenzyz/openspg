"""Simple DSL parser for GraphSPG patterns."""

import re
from typing import Any, Dict, List, Optional, Tuple
from graphspg.dsl.ast import (
    AggregateExpr,
    AggregateOp,
    BinaryExpr,
    BinaryOp,
    DefineStatement,
    EdgePattern,
    Literal,
    MatchStatement,
    NodePattern,
    PathPattern,
    PropertyRef,
    ReturnClause,
    Statement,
    StatementType,
    VariableRef,
    WhereClause,
)


class ParseError(Exception):
    """Parser error."""
    pass


class DSLParser:
    """Simple DSL parser for graph patterns."""

    def __init__(self):
        self.text = ""
        self.pos = 0

    def parse(self, text: str) -> Statement:
        """Parse a DSL statement.

        Supports:
        - MATCH (a:Label)-[r:REL]->(b:Label) WHERE condition RETURN a, b
        - DEFINE (a:Label)-[r:REL]->(b:Label) WHERE condition
        """
        self.text = text.strip()
        self.pos = 0

        # Determine statement type
        if self.text.upper().startswith("MATCH"):
            return self._parse_match()
        elif self.text.upper().startswith("DEFINE"):
            return self._parse_define()
        else:
            raise ParseError(f"Unknown statement type: {self.text[:20]}")

    def _parse_match(self) -> Statement:
        """Parse MATCH statement."""
        self._consume_keyword("MATCH")
        patterns = self._parse_patterns()

        where = None
        if self._peek_keyword("WHERE"):
            self._consume_keyword("WHERE")
            condition = self._parse_condition()
            where = WhereClause(condition=condition)

        return_clause = None
        if self._peek_keyword("RETURN"):
            self._consume_keyword("RETURN")
            items = self._parse_return_items()
            return_clause = ReturnClause(items=items)

        match_stmt = MatchStatement(patterns=patterns, where=where, return_clause=return_clause)
        return Statement(type=StatementType.MATCH, body=match_stmt)

    def _parse_define(self) -> Statement:
        """Parse DEFINE statement."""
        self._consume_keyword("DEFINE")
        patterns = self._parse_patterns()

        if len(patterns) != 1:
            raise ParseError("DEFINE requires exactly one pattern")

        where = None
        if self._peek_keyword("WHERE"):
            self._consume_keyword("WHERE")
            condition = self._parse_condition()
            where = WhereClause(condition=condition)

        define_stmt = DefineStatement(pattern=patterns[0], where=where)
        return Statement(type=StatementType.DEFINE, body=define_stmt)

    def _parse_patterns(self) -> List[PathPattern]:
        """Parse comma-separated path patterns."""
        patterns = []
        pattern = self._parse_path_pattern()
        patterns.append(pattern)

        while self._peek(","):
            self._consume(",")
            pattern = self._parse_path_pattern()
            patterns.append(pattern)

        return patterns

    def _parse_path_pattern(self) -> PathPattern:
        """Parse a single path pattern: (a)-[r]->(b)"""
        elements = []

        # Must start with node
        node = self._parse_node_pattern()
        elements.append(node)

        # Parse edges and nodes
        while self._peek_edge():
            edge = self._parse_edge_pattern()
            elements.append(edge)

            node = self._parse_node_pattern()
            elements.append(node)

        return PathPattern(elements=elements)

    def _parse_node_pattern(self) -> NodePattern:
        """Parse node pattern: (var:Label {prop: value})"""
        self._skip_whitespace()
        if not self._peek("("):
            raise ParseError(f"Expected '(' at position {self.pos}")
        self._consume("(")

        # Parse variable
        variable = self._parse_identifier()

        # Parse labels
        labels = []
        while self._peek(":"):
            self._consume(":")
            label = self._parse_identifier()
            labels.append(label)

        # Parse properties
        properties = {}
        if self._peek("{"):
            properties = self._parse_properties()

        self._skip_whitespace()
        if not self._peek(")"):
            raise ParseError(f"Expected ')' at position {self.pos}")
        self._consume(")")

        return NodePattern(variable=variable, labels=labels, properties=properties)

    def _parse_edge_pattern(self) -> EdgePattern:
        """Parse edge pattern: -[r:TYPE]-> or <-[r:TYPE]- or -[r:TYPE]-"""
        self._skip_whitespace()

        # Determine direction
        direction = "->"
        if self._peek("<-"):
            direction = "<-"
            self._consume("<-")
        elif self._peek("-"):
            self._consume("-")
            # Check if it's -> at the end
        else:
            raise ParseError(f"Expected edge pattern at position {self.pos}")

        # Parse edge details [var:TYPE]
        variable = None
        types = []
        properties = {}

        if self._peek("["):
            self._consume("[")

            # Optional variable
            if not self._peek(":") and not self._peek("]"):
                variable = self._parse_identifier()

            # Parse types
            while self._peek(":"):
                self._consume(":")
                edge_type = self._parse_identifier()
                types.append(edge_type)
                if self._peek("|"):
                    self._consume("|")

            # Parse properties
            if self._peek("{"):
                properties = self._parse_properties()

            self._skip_whitespace()
            if not self._peek("]"):
                raise ParseError(f"Expected ']' at position {self.pos}")
            self._consume("]")

        # Parse direction ending
        self._skip_whitespace()
        if direction == "<-":
            if not self._peek("-"):
                raise ParseError(f"Expected '-' after '<-[...]' at position {self.pos}")
            self._consume("-")
        elif self._peek("->"):
            self._consume("->")
            direction = "->"
        elif self._peek("-"):
            self._consume("-")
            direction = "-"
        else:
            raise ParseError(f"Expected '->' or '-' at position {self.pos}")

        return EdgePattern(
            variable=variable,
            types=types,
            properties=properties,
            direction=direction
        )

    def _parse_properties(self) -> Dict[str, Any]:
        """Parse property map: {key1: value1, key2: value2}"""
        self._skip_whitespace()
        self._consume("{")
        properties = {}

        if not self._peek("}"):
            key = self._parse_identifier()
            self._skip_whitespace()
            self._consume(":")
            value = self._parse_literal()
            properties[key] = value

            while self._peek(","):
                self._consume(",")
                key = self._parse_identifier()
                self._skip_whitespace()
                self._consume(":")
                value = self._parse_literal()
                properties[key] = value

        self._skip_whitespace()
        self._consume("}")
        return properties

    def _parse_condition(self) -> Any:
        """Parse WHERE condition."""
        return self._parse_or_expr()

    def _parse_or_expr(self) -> Any:
        """Parse OR expression."""
        left = self._parse_and_expr()

        while self._peek_keyword("OR"):
            self._consume_keyword("OR")
            right = self._parse_and_expr()
            left = BinaryExpr(left=left, op=BinaryOp.OR, right=right)

        return left

    def _parse_and_expr(self) -> Any:
        """Parse AND expression."""
        left = self._parse_comparison()

        while self._peek_keyword("AND"):
            self._consume_keyword("AND")
            right = self._parse_comparison()
            left = BinaryExpr(left=left, op=BinaryOp.AND, right=right)

        return left

    def _parse_comparison(self) -> Any:
        """Parse comparison expression."""
        left = self._parse_primary()

        self._skip_whitespace()
        if self._peek(">="):
            self._consume(">=")
            right = self._parse_primary()
            return BinaryExpr(left=left, op=BinaryOp.GTE, right=right)
        elif self._peek("<="):
            self._consume("<=")
            right = self._parse_primary()
            return BinaryExpr(left=left, op=BinaryOp.LTE, right=right)
        elif self._peek("!="):
            self._consume("!=")
            right = self._parse_primary()
            return BinaryExpr(left=left, op=BinaryOp.NEQ, right=right)
        elif self._peek("="):
            self._consume("=")
            right = self._parse_primary()
            return BinaryExpr(left=left, op=BinaryOp.EQ, right=right)
        elif self._peek(">"):
            self._consume(">")
            right = self._parse_primary()
            return BinaryExpr(left=left, op=BinaryOp.GT, right=right)
        elif self._peek("<"):
            self._consume("<")
            right = self._parse_primary()
            return BinaryExpr(left=left, op=BinaryOp.LT, right=right)
        elif self._peek_keyword("IN"):
            self._consume_keyword("IN")
            right = self._parse_primary()
            return BinaryExpr(left=left, op=BinaryOp.IN, right=right)

        return left

    def _parse_primary(self) -> Any:
        """Parse primary expression."""
        self._skip_whitespace()

        # Check for aggregate functions
        for agg_op in AggregateOp:
            if self._peek_keyword(agg_op.value):
                self._consume_keyword(agg_op.value)
                self._consume("(")
                expr = self._parse_primary()
                self._consume(")")
                return AggregateExpr(op=agg_op, expr=expr)

        # Try to parse as literal first (numbers, strings, booleans)
        if self._is_literal_start():
            return Literal(value=self._parse_literal())

        # Check for property reference or variable
        identifier = self._parse_identifier()
        if self._peek("."):
            self._consume(".")
            prop = self._parse_identifier()
            return PropertyRef(variable=identifier, property=prop)
        else:
            return VariableRef(name=identifier)

    def _is_literal_start(self) -> bool:
        """Check if the current position starts a literal value."""
        self._skip_whitespace()
        if self.pos >= len(self.text):
            return False

        char = self.text[self.pos]
        # String literals
        if char in ('"', "'"):
            return True
        # Number literals (including negative)
        if char.isdigit() or char == '-':
            return True
        # Boolean literals
        if self._peek_keyword("true") or self._peek_keyword("false"):
            return True
        return False

    def _parse_return_items(self) -> List[Any]:
        """Parse RETURN items."""
        items = []
        item = self._parse_return_item()
        items.append(item)

        while self._peek(","):
            self._consume(",")
            item = self._parse_return_item()
            items.append(item)

        return items

    def _parse_return_item(self) -> Any:
        """Parse a single return item."""
        return self._parse_primary()

    def _parse_identifier(self) -> str:
        """Parse identifier."""
        self._skip_whitespace()
        match = re.match(r'[a-zA-Z_][a-zA-Z0-9_]*', self.text[self.pos:])
        if not match:
            raise ParseError(f"Expected identifier at position {self.pos}")
        identifier = match.group(0)
        self.pos += len(identifier)
        return identifier

    def _parse_literal(self) -> Any:
        """Parse literal value."""
        self._skip_whitespace()

        # String literal
        if self._peek("'") or self._peek('"'):
            quote = self.text[self.pos]
            self.pos += 1
            value = ""
            while self.pos < len(self.text) and self.text[self.pos] != quote:
                value += self.text[self.pos]
                self.pos += 1
            if self.pos >= len(self.text):
                raise ParseError("Unterminated string")
            self.pos += 1  # Skip closing quote
            return value

        # Number literal
        match = re.match(r'-?\d+\.?\d*', self.text[self.pos:])
        if match:
            num_str = match.group(0)
            self.pos += len(num_str)
            if '.' in num_str:
                return float(num_str)
            else:
                return int(num_str)

        # Boolean
        if self._peek_keyword("true"):
            self._consume_keyword("true")
            return True
        if self._peek_keyword("false"):
            self._consume_keyword("false")
            return False

        raise ParseError(f"Expected literal at position {self.pos}")

    def _skip_whitespace(self):
        """Skip whitespace."""
        while self.pos < len(self.text) and self.text[self.pos].isspace():
            self.pos += 1

    def _peek(self, s: str) -> bool:
        """Peek ahead for string."""
        self._skip_whitespace()
        return self.text[self.pos:self.pos + len(s)] == s

    def _peek_keyword(self, keyword: str) -> bool:
        """Peek ahead for keyword."""
        self._skip_whitespace()
        remaining = self.text[self.pos:].upper()
        if remaining.startswith(keyword.upper()):
            # Make sure it's followed by non-identifier character
            end_pos = len(keyword)
            if end_pos >= len(remaining) or not remaining[end_pos].isalnum():
                return True
        return False

    def _peek_edge(self) -> bool:
        """Check if next token is an edge pattern."""
        self._skip_whitespace()
        return self._peek("<-") or self._peek("-")

    def _consume(self, s: str):
        """Consume expected string."""
        self._skip_whitespace()
        if not self._peek(s):
            raise ParseError(f"Expected '{s}' at position {self.pos}")
        self.pos += len(s)

    def _consume_keyword(self, keyword: str):
        """Consume expected keyword."""
        if not self._peek_keyword(keyword):
            raise ParseError(f"Expected keyword '{keyword}' at position {self.pos}")
        self.pos += len(keyword)
