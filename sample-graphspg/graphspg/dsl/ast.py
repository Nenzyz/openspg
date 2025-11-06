"""Abstract Syntax Tree nodes for the GraphSPG DSL."""

from dataclasses import dataclass
from typing import Any, Dict, List, Optional
from enum import Enum


class StatementType(str, Enum):
    """Statement types in the DSL."""
    MATCH = "MATCH"
    DEFINE = "DEFINE"


class BinaryOp(str, Enum):
    """Binary operators."""
    EQ = "="
    NEQ = "!="
    GT = ">"
    GTE = ">="
    LT = "<"
    LTE = "<="
    AND = "AND"
    OR = "OR"
    IN = "IN"


class AggregateOp(str, Enum):
    """Aggregate operations."""
    COUNT = "count"
    SUM = "sum"
    AVG = "avg"
    MIN = "min"
    MAX = "max"


@dataclass
class Node:
    """Base AST node."""
    pass


@dataclass
class PropertyRef(Node):
    """Property reference: variable.property"""
    variable: str
    property: str

    def __str__(self):
        return f"{self.variable}.{self.property}"


@dataclass
class Literal(Node):
    """Literal value."""
    value: Any

    def __str__(self):
        if isinstance(self.value, str):
            return f"'{self.value}'"
        return str(self.value)


@dataclass
class BinaryExpr(Node):
    """Binary expression."""
    left: Node
    op: BinaryOp
    right: Node

    def __str__(self):
        return f"({self.left} {self.op.value} {self.right})"


@dataclass
class AggregateExpr(Node):
    """Aggregate expression: count(x), sum(x.prop), etc."""
    op: AggregateOp
    expr: Node

    def __str__(self):
        return f"{self.op.value}({self.expr})"


@dataclass
class VariableRef(Node):
    """Variable reference."""
    name: str

    def __str__(self):
        return self.name


@dataclass
class NodePattern(Node):
    """Graph node pattern: (var:Label {prop: value})"""
    variable: str
    labels: List[str]
    properties: Dict[str, Any]

    def __str__(self):
        labels_str = ':'.join(self.labels) if self.labels else ''
        if labels_str:
            labels_str = ':' + labels_str
        props_str = ', '.join(f"{k}: {v}" for k, v in self.properties.items())
        if props_str:
            props_str = ' {' + props_str + '}'
        return f"({self.variable}{labels_str}{props_str})"


@dataclass
class EdgePattern(Node):
    """Graph edge pattern: -[var:TYPE]->"""
    variable: Optional[str]
    types: List[str]
    properties: Dict[str, Any]
    direction: str  # "->", "<-", "-"

    def __str__(self):
        var_str = self.variable if self.variable else ''
        types_str = '|'.join(self.types) if self.types else ''
        if types_str:
            types_str = ':' + types_str
        props_str = ', '.join(f"{k}: {v}" for k, v in self.properties.items())
        if props_str:
            props_str = ' {' + props_str + '}'

        edge_str = f"[{var_str}{types_str}{props_str}]"

        if self.direction == "->":
            return f"-{edge_str}->"
        elif self.direction == "<-":
            return f"<-{edge_str}-"
        else:
            return f"-{edge_str}-"


@dataclass
class PathPattern(Node):
    """Complete path pattern: (a)-[r]->(b)"""
    elements: List[Node]  # Alternating NodePattern and EdgePattern

    def __str__(self):
        return ''.join(str(e) for e in self.elements)


@dataclass
class WhereClause(Node):
    """WHERE clause with conditions."""
    condition: Node

    def __str__(self):
        return f"WHERE {self.condition}"


@dataclass
class ReturnClause(Node):
    """RETURN clause with variables."""
    items: List[Node]  # PropertyRef, VariableRef, or AggregateExpr

    def __str__(self):
        items_str = ', '.join(str(item) for item in self.items)
        return f"RETURN {items_str}"


@dataclass
class MatchStatement(Node):
    """MATCH statement."""
    patterns: List[PathPattern]
    where: Optional[WhereClause] = None
    return_clause: Optional[ReturnClause] = None

    def __str__(self):
        patterns_str = ', '.join(str(p) for p in self.patterns)
        result = f"MATCH {patterns_str}"
        if self.where:
            result += f" {self.where}"
        if self.return_clause:
            result += f" {self.return_clause}"
        return result


@dataclass
class DefineStatement(Node):
    """DEFINE statement for derived relations."""
    pattern: PathPattern
    where: Optional[WhereClause] = None

    def __str__(self):
        result = f"DEFINE {self.pattern}"
        if self.where:
            result += f" {self.where}"
        return result


@dataclass
class Statement(Node):
    """Top-level statement."""
    type: StatementType
    body: Node  # MatchStatement or DefineStatement
