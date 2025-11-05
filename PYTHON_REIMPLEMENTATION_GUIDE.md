# OpenSPG Python Reimplementation Guide
## Software Architect's Guide to Building OpenSPG-Py with Memgraph

**Target Stack:**
- **Language:** Python 3.10+
- **Graph Database:** Memgraph
- **Parser:** ANTLR4 Python Runtime
- **Web Framework:** FastAPI
- **ORM/Data:** Pydantic, SQLAlchemy
- **Async:** asyncio, aiohttp

**Scope:** Core OpenSPG functionality (KGDSL, Schema, Builder, Reasoner)
**Excluded:** KAG (will be handled separately)

---

## Table of Contents

1. [Architecture Overview](#1-architecture-overview)
2. [Project Structure](#2-project-structure)
3. [KGDSL Parser Implementation](#3-kgdsl-parser)
4. [SPG Schema System](#4-spg-schema-system)
5. [Memgraph Integration Layer](#5-memgraph-integration)
6. [Builder Pipeline](#6-builder-pipeline)
7. [Reasoner Engine](#7-reasoner-engine)
8. [API Layer](#8-api-layer)
9. [Deployment Guide](#9-deployment)

---

## 1. Architecture Overview

### 1.1 Component Mapping

| OpenSPG (Java/Scala) | Python Equivalent | Library |
|---------------------|------------------|---------|
| ANTLR4 Grammar | ANTLR4 Python Runtime | `antlr4-python3-runtime` |
| Spring Boot | FastAPI | `fastapi` |
| Scala Case Classes | Pydantic Models | `pydantic` |
| Jackson/Gson | JSON serialization | `pydantic`, `orjson` |
| Scala Pattern Matching | Python match (3.10+) | Native |
| Neo4j Driver | Memgraph Driver | `neo4j` (compatible) |
| Pemja (Python-Java) | Not needed | N/A |
| Maven | Poetry/pip | `poetry` |
| Log4j | Python logging | `loguru` |

### 1.2 High-Level Architecture

```
┌─────────────────────────────────────────────────┐
│         FastAPI Application Layer               │
│  - REST API endpoints                           │
│  - Authentication/Authorization                  │
│  - Request validation (Pydantic)                │
└─────────────────────────────────────────────────┘
                    ↓
┌─────────────────────────────────────────────────┐
│            Core Services Layer                  │
│  - SchemaService                                │
│  - BuilderService                               │
│  - ReasonerService                              │
│  - JobScheduler (Celery/RQ)                     │
└─────────────────────────────────────────────────┘
                    ↓
┌─────────────────────────────────────────────────┐
│           Engine Layer (Pure Python)            │
│  ┌──────────────┐  ┌──────────────┐            │
│  │ KGDSL Parser │  │ Builder      │            │
│  │ (ANTLR4)     │  │ Pipeline     │            │
│  └──────────────┘  └──────────────┘            │
│  ┌──────────────┐  ┌──────────────┐            │
│  │ Reasoner     │  │ Schema       │            │
│  │ Engine       │  │ Manager      │            │
│  └──────────────┘  └──────────────┘            │
└─────────────────────────────────────────────────┘
                    ↓
┌─────────────────────────────────────────────────┐
│        Storage Adapter Layer                    │
│  - MemgraphAdapter (Cypher queries)            │
│  - ElasticsearchAdapter (search)               │
│  - RedisAdapter (cache)                        │
│  - PostgreSQL (metadata)                       │
└─────────────────────────────────────────────────┘
```

---

## 2. Project Structure

```
openspg-py/
├── pyproject.toml                 # Poetry dependencies
├── README.md
├── docker-compose.yml             # Memgraph + Redis + ES + PG
│
├── openspg/
│   ├── __init__.py
│   │
│   ├── core/                      # Core engines
│   │   ├── parser/                # KGDSL Parser
│   │   │   ├── __init__.py
│   │   │   ├── kgdsl_lexer.py    # ANTLR4 generated
│   │   │   ├── kgdsl_parser.py   # ANTLR4 generated
│   │   │   ├── dsl_parser.py     # High-level parser
│   │   │   ├── expr_parser.py    # Expression AST
│   │   │   └── pattern_parser.py # Pattern matching
│   │   │
│   │   ├── schema/                # Schema models
│   │   │   ├── __init__.py
│   │   │   ├── types.py          # SPGType hierarchy
│   │   │   ├── predicates.py     # Property/Relation
│   │   │   ├── constraints.py    # Validation rules
│   │   │   └── identifiers.py    # Type identifiers
│   │   │
│   │   ├── reasoner/              # Query engine
│   │   │   ├── __init__.py
│   │   │   ├── blocks.py         # Block IR
│   │   │   ├── logical_plan.py   # Logical planner
│   │   │   ├── physical_plan.py  # Physical planner
│   │   │   ├── operators.py      # Physical operators
│   │   │   ├── optimizer.py      # Query optimizer
│   │   │   └── executor.py       # Execution engine
│   │   │
│   │   └── builder/               # Knowledge construction
│   │       ├── __init__.py
│   │       ├── pipeline.py       # Pipeline orchestrator
│   │       ├── operators/        # Operator framework
│   │       │   ├── base.py
│   │       │   ├── predicting.py
│   │       │   ├── linking.py
│   │       │   └── fusing.py
│   │       └── record.py         # Record models
│   │
│   ├── adapters/                  # Storage adapters
│   │   ├── __init__.py
│   │   ├── memgraph.py           # Memgraph driver
│   │   ├── elasticsearch.py
│   │   ├── redis.py
│   │   └── postgres.py
│   │
│   ├── api/                       # FastAPI application
│   │   ├── __init__.py
│   │   ├── main.py               # FastAPI app
│   │   ├── routes/
│   │   │   ├── schema.py
│   │   │   ├── query.py
│   │   │   └── builder.py
│   │   └── models/               # API request/response
│   │
│   ├── services/                  # Business logic
│   │   ├── __init__.py
│   │   ├── schema_service.py
│   │   ├── reasoner_service.py
│   │   └── builder_service.py
│   │
│   └── utils/                     # Utilities
│       ├── __init__.py
│       ├── logging.py
│       └── config.py
│
├── tests/
│   ├── test_parser.py
│   ├── test_schema.py
│   ├── test_reasoner.py
│   └── fixtures/
│
└── scripts/
    ├── generate_antlr.sh          # Generate ANTLR4 parsers
    └── init_memgraph.py           # Initialize schema
```

---

## 3. KGDSL Parser Implementation

### 3.1 Setup ANTLR4

**Install ANTLR4:**
```bash
# Install ANTLR4 tool
cd /usr/local/lib
sudo curl -O https://www.antlr.org/download/antlr-4.13.1-complete.jar

# Add to .bashrc
export CLASSPATH=".:/usr/local/lib/antlr-4.13.1-complete.jar:$CLASSPATH"
alias antlr4='java -jar /usr/local/lib/antlr-4.13.1-complete.jar'

# Install Python runtime
pip install antlr4-python3-runtime==4.13.1
```

**Copy KGDSL Grammar:**
```bash
# Copy from OpenSPG
cp openspg/reasoner/kgdsl-parser/src/main/antlr4/com/antgroup/openspg/reasoner/KGDSL.g4 \
   openspg-py/grammars/KGDSL.g4

# Generate Python parser
cd openspg-py
antlr4 -Dlanguage=Python3 -visitor -no-listener \
       -o openspg/core/parser/ grammars/KGDSL.g4
```

### 3.2 Parser Implementation

**File: `openspg/core/parser/dsl_parser.py`**

```python
"""
KGDSL Parser - Main entry point for parsing KGDSL queries
Maps to: com.antgroup.openspg.reasoner.parser.OpenSPGDslParser
"""

from typing import List, Dict, Any, Optional
from antlr4 import InputStream, CommonTokenStream
from .kgdsl_lexer import KGDSLLexer
from .kgdsl_parser import KGDSLParser
from .pattern_parser import PatternParser
from .expr_parser import ExprParser
from ..reasoner.blocks import Block, DDLBlock, TableResultBlock


class OpenSPGDslParser:
    """
    Main KGDSL parser - converts DSL text to Block IR

    Equivalent to Scala's OpenSPGDslParser class
    """

    def __init__(self):
        self.pattern_parser = PatternParser()
        self.expr_parser = ExprParser()
        self.parameters: set[str] = set()

    def parse(self, text: str) -> Block:
        """
        Parse single KGDSL statement to Block

        Args:
            text: KGDSL query string

        Returns:
            Block: Parsed block IR

        Raises:
            KGDSLParseError: If parsing fails
        """
        blocks = self.parse_multiple_statement(text)
        if len(blocks) != 1:
            raise KGDSLParseError(
                f"Expected single statement, got {len(blocks)}"
            )
        return blocks[0]

    def parse_multiple_statement(
        self,
        text: str,
        params: Optional[Dict[str, Any]] = None
    ) -> List[Block]:
        """
        Parse multiple KGDSL statements (Define + Query)

        Maps to: parseMultipleStatement in Scala
        """
        # Create ANTLR4 parser
        input_stream = InputStream(text)
        lexer = KGDSLLexer(input_stream)
        token_stream = CommonTokenStream(lexer)
        parser = KGDSLParser(token_stream)

        # Parse to tree
        tree = parser.kg_dsl()

        # Visit tree and build blocks
        return self._parse_kg_dsl(tree, params or {})

    def _parse_kg_dsl(
        self,
        ctx: KGDSLParser.Kg_dslContext,
        params: Dict[str, Any]
    ) -> List[Block]:
        """
        Convert ANTLR4 parse tree to Block IR

        Maps to: parseKgDsl in Scala
        """
        blocks = []

        # Parse Define statements (DDL)
        if ctx.base_predicated_define():
            for define_ctx in ctx.base_predicated_define():
                block = self._parse_base_predicated_define(define_ctx)
                blocks.append(block)

        # Parse Query statement
        if ctx.base_job():
            query_block = self._parse_base_job(ctx.base_job(), params)
            blocks.append(query_block)

        return blocks

    def _parse_base_predicated_define(
        self,
        ctx: KGDSLParser.Base_predicated_defineContext
    ) -> DDLBlock:
        """
        Parse Define statement

        Example:
            Define (s:User)-[p:belongsTo]->(o:Concept/HighValue) {
                GraphStructure { ... }
                Rule { ... }
            }
        """
        define_ctx = ctx.the_define_structure()

        # Parse predicate definition: (s)-[p]->(o)
        predicate_info = self._parse_predicated_define(
            define_ctx.predicated_define()
        )

        # Parse graph structure and rules
        ddl_block = self._parse_define_structure(
            define_ctx,
            predicate_info
        )

        return ddl_block

    # ... Additional parsing methods


class KGDSLParseError(Exception):
    """KGDSL parsing error"""
    pass
```

### 3.3 Expression Parser

**File: `openspg/core/parser/expr_parser.py`**

```python
"""
Expression Parser - Builds expression AST from KGDSL rules

Maps to: com.antgroup.openspg.reasoner.parser.expr.RuleExprParser
"""

from dataclasses import dataclass
from typing import Any, List, Union
from enum import Enum


# ============= Expression AST =============

class Expr:
    """Base expression class"""
    def pretty(self) -> str:
        raise NotImplementedError


@dataclass
class Ref(Expr):
    """Variable reference: s, o, s.name"""
    name: str

    def pretty(self) -> str:
        return f"Ref({self.name})"


@dataclass
class VString(Expr):
    """String literal: 'value'"""
    value: str

    def pretty(self) -> str:
        return f"VString({self.value})"


@dataclass
class VLong(Expr):
    """Long literal: 123"""
    value: int

    def pretty(self) -> str:
        return f"VLong({self.value})"


@dataclass
class VDouble(Expr):
    """Double literal: 123.45"""
    value: float

    def pretty(self) -> str:
        return f"VDouble({self.value})"


@dataclass
class VBoolean(Expr):
    """Boolean literal: true/false"""
    value: bool

    def pretty(self) -> str:
        return f"VBoolean({self.value})"


# Binary operators
class BinaryOp(Enum):
    """Binary operator types"""
    EQUAL = "BEqual"
    NOT_EQUAL = "BNotEqual"
    GREATER_THAN = "BGreaterThan"
    LESS_THAN = "BLessThan"
    GREATER_EQUAL = "BNotSmallerThan"
    LESS_EQUAL = "BNotBiggerThan"
    IN = "BIn"
    LIKE = "BLike"
    RLIKE = "BRLike"
    AND = "BAnd"
    OR = "BOr"
    XOR = "BXor"
    ADD = "BAdd"
    SUB = "BSub"
    MUL = "BMul"
    DIV = "BDiv"
    MOD = "BMod"


@dataclass
class BinaryOpExpr(Expr):
    """Binary operation: left op right"""
    op: BinaryOp
    left: Expr
    right: Expr

    def pretty(self) -> str:
        return f"BinaryOpExpr({self.op.value}, {self.left.pretty()}, {self.right.pretty()})"


# Unary operators
class UnaryOp(Enum):
    """Unary operator types"""
    GET_FIELD = "GetField"
    ABS = "Abs"
    FLOOR = "Floor"
    CEILING = "Ceiling"
    EXISTS = "Exists"


@dataclass
class GetField(UnaryOp):
    """Get field operator"""
    field_name: str


@dataclass
class UnaryOpExpr(Expr):
    """Unary operation: op expr"""
    op: UnaryOp
    arg: Expr

    def pretty(self) -> str:
        return f"UnaryOpExpr({self.op}, {self.arg.pretty()})"


# Aggregation
class AggOp(Enum):
    """Aggregation operator"""
    SUM = "Sum"
    AVG = "Avg"
    COUNT = "Count"
    MIN = "Min"
    MAX = "Max"


@dataclass
class AggOpExpr(Expr):
    """Aggregation: sum(x), count(y)"""
    agg_op: AggOp
    agg_expr: Expr

    def pretty(self) -> str:
        return f"AggOpExpr({self.agg_op.value}, {self.agg_expr.pretty()})"


@dataclass
class GraphAggregatorExpr(Expr):
    """
    Graph aggregation: group(A, B).count(C)

    Corresponds to Scala's GraphAggregatorExpr
    """
    path_name: str
    by: List[Expr]  # Group by expressions
    op: AggOpExpr   # Aggregation operation

    def pretty(self) -> str:
        by_str = ", ".join(e.pretty() for e in self.by)
        return f"GraphAggregatorExpr(group({by_str}).{self.op.pretty()})"


@dataclass
class FunctionExpr(Expr):
    """Function call: func(arg1, arg2, ...)"""
    name: str
    args: List[Expr]

    def pretty(self) -> str:
        args_str = ", ".join(a.pretty() for a in self.args)
        return f"FunctionExpr({self.name}({args_str}))"


# ============= Expression Parser =============

class ExprParser:
    """
    Parses KGDSL rule expressions to expression AST

    Maps to: RuleExprParser in Scala
    """

    def __init__(self):
        self.parameters: set[str] = set()

    def parse_rule_expression(
        self,
        ctx  # ANTLR4 context
    ) -> 'Rule':
        """
        Parse rule expression

        Examples:
            R1("explanation"): s.age > 18
            count = group(s).count(o)
        """
        # Extract rule name and description
        rule_name = ctx.identifier().getText()

        # Parse right-hand side expression
        expr = self.parse_value_expression(ctx.value_expression())

        # Determine rule type
        if self._is_logic_rule(ctx):
            # LogicRule: boolean expression
            desc = self._extract_description(ctx)
            return LogicRule(rule_name, desc, expr)
        else:
            # ProjectRule: assignment
            output_var = IRVariable(rule_name)
            return ProjectRule(output_var, expr)

    def parse_value_expression(self, ctx) -> Expr:
        """
        Parse value expression (recursive)

        Handles: binary ops, unary ops, literals, functions
        """
        # Binary operation
        if ctx.getChildCount() == 3:
            left = self.parse_value_expression(ctx.getChild(0))
            op = self._parse_binary_op(ctx.getChild(1))
            right = self.parse_value_expression(ctx.getChild(2))
            return BinaryOpExpr(op, left, right)

        # Unary operation
        elif ctx.unary_operator():
            op = self._parse_unary_op(ctx.unary_operator())
            arg = self.parse_value_expression(ctx.value_expression())
            return UnaryOpExpr(op, arg)

        # Function call
        elif ctx.function_call():
            return self._parse_function_call(ctx.function_call())

        # Literal
        elif ctx.literal():
            return self._parse_literal(ctx.literal())

        # Variable reference
        elif ctx.identifier():
            var_name = ctx.identifier().getText()

            # Check for parameter: $varName
            if var_name.startswith('$'):
                self.parameters.add(var_name[1:])
                return Ref(var_name)

            # Check for property access: s.name
            if ctx.DOT():
                field = ctx.identifier(1).getText()
                return UnaryOpExpr(
                    GetField(field),
                    Ref(var_name)
                )

            return Ref(var_name)

        raise ExprParseError(f"Unsupported expression: {ctx.getText()}")

    def _parse_function_call(self, ctx) -> Expr:
        """Parse function call"""
        func_name = ctx.identifier().getText()
        args = [
            self.parse_value_expression(arg_ctx)
            for arg_ctx in ctx.value_expression()
        ]

        # Special handling for aggregations
        if func_name in ['sum', 'avg', 'count', 'min', 'max']:
            agg_op = AggOp[func_name.upper()]
            return AggOpExpr(agg_op, args[0])

        # Special handling for group()
        if func_name == 'group':
            # group(A, B).count(C)
            return self._parse_graph_aggregation(ctx, args)

        # Regular function
        return FunctionExpr(func_name, args)

    def _parse_graph_aggregation(self, ctx, group_by: List[Expr]) -> Expr:
        """
        Parse graph aggregation: group(A, B).count(C)
        """
        # Find chained aggregation method
        agg_ctx = ctx.aggregation_method()
        agg_name = agg_ctx.identifier().getText()
        agg_arg = self.parse_value_expression(agg_ctx.value_expression())

        agg_op = AggOpExpr(AggOp[agg_name.upper()], agg_arg)

        return GraphAggregatorExpr(
            path_name="default",
            by=group_by,
            op=agg_op
        )

    # ... Additional helper methods


class ExprParseError(Exception):
    """Expression parsing error"""
    pass
```

### 3.4 Pattern Parser

**File: `openspg/core/parser/pattern_parser.py`**

```python
"""
Pattern Parser - Parses graph patterns in GraphStructure block

Maps to: com.antgroup.openspg.reasoner.parser.pattern.PatternParser
"""

from dataclasses import dataclass
from typing import Set, Dict, List, Optional
from enum import Enum


# ============= Pattern Elements =============

class Direction(Enum):
    """Edge direction"""
    OUT = "OUT"
    IN = "IN"
    BOTH = "BOTH"


@dataclass
class Element:
    """Base pattern element"""
    alias: str
    type_names: Set[str]


@dataclass
class EntityElement(Element):
    """
    Entity pattern: (s:User)

    Maps to: com.antgroup.openspg.reasoner.lube.common.pattern.EntityElement
    """
    id: Optional[str] = None
    rule: Optional[Expr] = None

    def __repr__(self):
        return f"({self.alias}:{','.join(self.type_names)})"


@dataclass
class ConceptElement(Element):
    """
    Concept pattern: (o:`TaxOfRiskUser`/`HighRisk`)

    Maps to: ConceptElement in Scala
    """
    concept_type: str
    concept_instance: str

    def __repr__(self):
        return f"({self.alias}:{self.concept_type}/{self.concept_instance})"


@dataclass
class PredicateElement:
    """
    Predicate/edge pattern: -[e:knows]->

    Maps to: PredicateElement in Scala
    """
    label: str
    alias: str
    source: Element
    target: Element
    fields: Dict[str, Expr]
    direction: Direction

    def __repr__(self):
        arrow = "->" if self.direction == Direction.OUT else "<-"
        return f"{self.source}-[{self.alias}:{self.label}]{arrow}{self.target}"


@dataclass
class VariablePatternConnection:
    """
    Variable-length path connection: -[e:knows*1..5]->

    Maps to: VariablePatternConnection in Scala
    """
    alias: str
    source: str
    target: str
    rel_types: Set[str]
    direction: Direction
    rule: Optional[Expr] = None
    limit: int = -1  # per_node_limit
    repeat: Optional[tuple[int, int]] = None  # (min, max) for *1..5

    def __repr__(self):
        repeat_str = f"*{self.repeat[0]}..{self.repeat[1]}" if self.repeat else ""
        limit_str = f" per_node_limit {self.limit}" if self.limit > 0 else ""
        return f"-[{self.alias}:{','.join(self.rel_types)}{repeat_str}{limit_str}]->"


@dataclass
class LinkedPatternConnection:
    """
    Linked edge (function-based): -[e:nearby(s.boundary, o.center, 10)]->

    Maps to: LinkedPatternConnection in Scala
    """
    alias: str
    source: str
    target: str
    func_name: str
    params: List[Expr]
    limit: int = -1

    def __repr__(self):
        params_str = ", ".join(str(p) for p in self.params)
        return f"-[{self.alias}:{self.func_name}({params_str})]->"


@dataclass
class GraphPattern:
    """
    Complete graph pattern within GraphStructure { }

    Maps to: GraphPattern in Scala
    """
    root_alias: Optional[str]  # Start node (if specified)
    nodes: Dict[str, EntityElement]
    edges: Dict[str, Set[Union[VariablePatternConnection, LinkedPatternConnection]]]
    properties: Dict[str, Set[str]]  # Required properties per alias

    def __repr__(self):
        return f"GraphPattern(nodes={len(self.nodes)}, edges={len(self.edges)})"


@dataclass
class GraphPath:
    """
    Named graph path

    Maps to: GraphPath in Scala
    """
    path_name: str
    graph_pattern: GraphPattern
    optional: bool = False

    def __repr__(self):
        opt = "OPTIONAL " if self.optional else ""
        return f"{opt}Path({self.path_name})"


# ============= Pattern Parser =============

class PatternParser:
    """
    Parses graph patterns from GraphStructure block

    Maps to: PatternParser in Scala
    """

    def __init__(self):
        self.default_alias_counter = 0

    def parse_graph_structure_define(
        self,
        ctx,  # ANTLR4 context
        head: Optional[Element] = None,
        predicate: Optional[PredicateElement] = None
    ) -> 'MatchBlock':
        """
        Parse GraphStructure block

        Example:
            GraphStructure {
                (s:User)-[e:knows]->(o:User),
                (s)-[f:likes]->(p:Product)
            }
        """
        patterns = {}

        # Parse path patterns
        for path_ctx in ctx.path_pattern():
            path = self.parse_path_pattern(path_ctx, head, predicate)
            patterns[path.path_name] = path

        # Build MatchBlock
        return MatchBlock(patterns=patterns)

    def parse_node_pattern(self, ctx) -> EntityElement:
        """
        Parse node pattern: (s:User where id==$userId)
        """
        # Parse alias
        alias = None
        if ctx.identifier():
            alias = ctx.identifier().getText()
        else:
            alias = self.get_default_name()

        # Parse type labels
        type_names = set()
        if ctx.label_expression():
            type_names = self._parse_label_expression(ctx.label_expression())

        # Parse WHERE clause
        rule = None
        if ctx.element_pattern_where_clause():
            rule = self._parse_where_clause(ctx.element_pattern_where_clause())

        return EntityElement(
            alias=alias,
            type_names=type_names,
            rule=rule
        )

    def parse_edge_pattern(
        self,
        ctx,
        direction: Direction
    ) -> Union[VariablePatternConnection, LinkedPatternConnection]:
        """
        Parse edge pattern

        Examples:
            -[e:knows]->
            -[e:knows*1..5 per_node_limit 10]->
            -[e:nearby(s.boundary, o.center, 10)]->
        """
        alias = self.get_default_name()
        if ctx.identifier():
            alias = ctx.identifier().getText()

        # Check for linked edge (function-based)
        if ctx.function_call():
            return self._parse_linked_edge(ctx, alias, direction)

        # Parse relation types
        rel_types = self._parse_label_expression(ctx.label_expression())

        # Parse repeat (variable-length path)
        repeat = None
        if ctx.repeat_clause():
            repeat = self._parse_repeat_clause(ctx.repeat_clause())

        # Parse per-node limit
        limit = -1
        if ctx.per_node_limit_clause():
            limit = int(ctx.per_node_limit_clause().NUMBER().getText())

        return VariablePatternConnection(
            alias=alias,
            source="",  # Will be filled later
            target="",  # Will be filled later
            rel_types=rel_types,
            direction=direction,
            limit=limit,
            repeat=repeat
        )

    def _parse_linked_edge(
        self,
        ctx,
        alias: str,
        direction: Direction
    ) -> LinkedPatternConnection:
        """
        Parse linked edge: -[e:nearby(s.boundary, o.center, 10)]->
        """
        func_ctx = ctx.function_call()
        func_name = func_ctx.identifier().getText()

        # Parse function parameters
        params = [
            self.expr_parser.parse_value_expression(arg_ctx)
            for arg_ctx in func_ctx.value_expression()
        ]

        return LinkedPatternConnection(
            alias=alias,
            source="",
            target="",
            func_name=func_name,
            params=params
        )

    def _parse_label_expression(self, ctx) -> Set[str]:
        """
        Parse label expression

        Examples:
            User
            OpenSource.User
            TaxOfRiskUser/HighRisk  (concept)
        """
        labels = set()

        # Handle concept labels: TaxOfRiskUser/Instance
        if '/' in ctx.getText():
            # This is a concept type
            parts = ctx.getText().split('/')
            concept_type = parts[0]
            concept_instance = parts[1].strip('`')
            labels.add(f"{concept_type}/{concept_instance}")
        else:
            # Regular entity type
            labels.add(ctx.getText())

        return labels

    def get_default_name(self) -> str:
        """Generate default alias name"""
        self.default_alias_counter += 1
        return f"_auto_{self.default_alias_counter}"

    # ... Additional helper methods
```

---

## 4. SPG Schema System

### 4.1 Schema Type Models

**File: `openspg/core/schema/types.py`**

```python
"""
SPG Schema Types

Maps to: com.antgroup.openspg.core.schema.model.type.*
"""

from pydantic import BaseModel, Field
from typing import Optional, List, Set, Dict
from enum import Enum
from datetime import datetime


# ============= Type Enums =============

class SPGTypeEnum(str, Enum):
    """
    Type category enum

    Maps to: SPGTypeEnum in Java
    """
    BASIC_TYPE = "BASIC_TYPE"
    ENTITY_TYPE = "ENTITY_TYPE"
    INDEX_TYPE = "INDEX_TYPE"
    CONCEPT_TYPE = "CONCEPT_TYPE"
    EVENT_TYPE = "EVENT_TYPE"
    STANDARD_TYPE = "STANDARD_TYPE"


class BasicTypeEnum(str, Enum):
    """Basic primitive types"""
    TEXT = "Text"
    INTEGER = "Integer"
    LONG = "Long"
    FLOAT = "Float"
    DOUBLE = "Double"
    BOOLEAN = "Boolean"


# ============= Identifiers =============

class SPGTypeIdentifier(BaseModel):
    """
    Type identifier with namespace

    Maps to: SPGTypeIdentifier in Java
    """
    namespace: Optional[str] = None
    name: str

    def __str__(self) -> str:
        if self.namespace:
            return f"{self.namespace}.{self.name}"
        return self.name

    @classmethod
    def parse(cls, identifier_str: str) -> 'SPGTypeIdentifier':
        """Parse from string: 'Namespace.TypeName' or 'TypeName'"""
        if '.' in identifier_str:
            namespace, name = identifier_str.rsplit('.', 1)
            return cls(namespace=namespace, name=name)
        return cls(name=identifier_str)


class ConceptIdentifier(BaseModel):
    """
    Concept instance identifier

    Format: TaxonomyType/InstanceName
    Maps to: ConceptIdentifier in Java
    """
    concept_type: str
    concept_instance: str

    def __str__(self) -> str:
        return f"{self.concept_type}/{self.concept_instance}"

    @classmethod
    def parse(cls, identifier_str: str) -> 'ConceptIdentifier':
        """Parse from string: 'TaxType/Instance'"""
        concept_type, concept_instance = identifier_str.split('/', 1)
        return cls(
            concept_type=concept_type,
            concept_instance=concept_instance.strip('`')
        )


# ============= Basic Info =============

class BasicInfo(BaseModel):
    """
    Basic metadata for schema types

    Maps to: BasicInfo<T> in Java
    """
    identifier: SPGTypeIdentifier
    name_zh: Optional[str] = None  # Chinese name
    description: Optional[str] = None
    creator: Optional[str] = None
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None


# ============= Parent Type Info =============

class ParentTypeInfo(BaseModel):
    """
    Parent type information for inheritance

    Maps to: ParentTypeInfo in Java
    """
    parent_type_identifier: SPGTypeIdentifier
    inherited_properties: List[str] = Field(default_factory=list)
    inherited_relations: List[str] = Field(default_factory=list)


# ============= Base SPG Type =============

class BaseSPGType(BaseModel):
    """
    Abstract base class for all SPG types

    Maps to: BaseSPGType in Java

    Hierarchy:
        BaseSPGType
        ├─ BasicType
        ├─ StandardType
        ├─ EntityType
        ├─ ConceptType
        ├─ EventType
        └─ IndexType
    """
    basic_info: BasicInfo
    spg_type_enum: SPGTypeEnum
    parent_type_info: Optional[ParentTypeInfo] = None
    properties: List['Property'] = Field(default_factory=list)
    relations: List['Relation'] = Field(default_factory=list)
    advanced_config: Optional['SPGTypeAdvancedConfig'] = None

    class Config:
        use_enum_values = True

    def get_identifier(self) -> SPGTypeIdentifier:
        """Get type identifier"""
        return self.basic_info.identifier

    def get_property(self, property_name: str) -> Optional['Property']:
        """Find property by name"""
        for prop in self.properties:
            if prop.identifier.name == property_name:
                return prop
        return None

    def get_relation(self, relation_name: str) -> Optional['Relation']:
        """Find relation by name"""
        for rel in self.relations:
            if rel.identifier.name == relation_name:
                return rel
        return None


# ============= Specific Type Classes =============

class EntityType(BaseSPGType):
    """
    Entity type: User, Company, Product

    Maps to: EntityType in Java
    """
    spg_type_enum: SPGTypeEnum = SPGTypeEnum.ENTITY_TYPE

    def __init__(self, **data):
        super().__init__(**data)
        self.spg_type_enum = SPGTypeEnum.ENTITY_TYPE


class ConceptType(BaseSPGType):
    """
    Concept type (taxonomy): TaxOfRiskUser, TaxOfIndustry

    Maps to: ConceptType in Java
    """
    spg_type_enum: SPGTypeEnum = SPGTypeEnum.CONCEPT_TYPE
    layer_config: Optional['ConceptLayerConfig'] = None
    taxonomic_config: Optional['ConceptTaxonomicConfig'] = None

    def __init__(self, **data):
        super().__init__(**data)
        self.spg_type_enum = SPGTypeEnum.CONCEPT_TYPE


class EventType(BaseSPGType):
    """
    Event type: Transaction, Login, Accident

    Maps to: EventType in Java
    """
    spg_type_enum: SPGTypeEnum = SPGTypeEnum.EVENT_TYPE

    def __init__(self, **data):
        super().__init__(**data)
        self.spg_type_enum = SPGTypeEnum.EVENT_TYPE


class IndexType(BaseSPGType):
    """
    Index type (for KAG): SummaryIndex, Chunk2QueryIndex

    Maps to: IndexType in Java
    """
    spg_type_enum: SPGTypeEnum = SPGTypeEnum.INDEX_TYPE

    def __init__(self, **data):
        super().__init__(**data)
        self.spg_type_enum = SPGTypeEnum.INDEX_TYPE


# ============= Advanced Configs =============

class SPGTypeAdvancedConfig(BaseModel):
    """
    Advanced configuration for SPG types

    Maps to: SPGTypeAdvancedConfig in Java
    """
    visible_scope: str = "PUBLIC"  # PUBLIC, PRIVATE, PROJECT
    bound_operators: Dict[str, str] = Field(default_factory=dict)
    multi_version_enabled: bool = False


class ConceptLayerConfig(BaseModel):
    """Concept layer configuration"""
    layer_predicate: str = "isA"
    layer_names: List[str] = Field(default_factory=list)


class ConceptTaxonomicConfig(BaseModel):
    """Concept taxonomy configuration"""
    taxonomic_type_identifier: SPGTypeIdentifier


# Forward references
from .predicates import Property, Relation
BaseSPGType.update_forward_refs()
```

### 4.2 Predicates (Properties & Relations)

**File: `openspg/core/schema/predicates.py`**

```python
"""
Predicates: Properties and Relations

Maps to: com.antgroup.openspg.core.schema.model.predicate.*
"""

from pydantic import BaseModel, Field
from typing import Optional, Dict, Any
from enum import Enum
from .types import SPGTypeIdentifier, BasicInfo
from .constraints import Constraint


# ============= Property =============

class PropertyGroupEnum(str, Enum):
    """Property group classification"""
    BASIC = "BASIC"
    STANDARD = "STANDARD"
    EXTENDING = "EXTENDING"


class IndexTypeEnum(str, Enum):
    """Index type for properties"""
    NONE = "NONE"
    TEXT = "TEXT"
    KEYWORD = "KEYWORD"
    NUMERIC = "NUMERIC"
    VECTOR = "VECTOR"


class Property(BaseModel):
    """
    Property (attribute) definition

    Maps to: Property in Java

    Example: User.age, User.email
    """
    identifier: SPGTypeIdentifier
    basic_info: BasicInfo
    object_type_ref: 'SPGTypeRef'  # Target type
    property_group: PropertyGroupEnum = PropertyGroupEnum.BASIC
    constraint: Optional[Constraint] = None
    advanced_config: Optional['PropertyAdvancedConfig'] = None

    def is_semantic_property(self) -> bool:
        """Check if property points to concept/entity"""
        return self.object_type_ref.is_advanced_type()


class PropertyAdvancedConfig(BaseModel):
    """Advanced property configuration"""
    index_type: IndexTypeEnum = IndexTypeEnum.NONE
    mounted_concept: Optional['MountedConceptConfig'] = None
    sub_properties: list['SubProperty'] = Field(default_factory=list)


class MountedConceptConfig(BaseModel):
    """
    Concept mounting configuration

    Enables semantic standardization of property values
    """
    concept_type_identifier: SPGTypeIdentifier
    dynamic: bool = True  # Allow dynamic concept creation


class SubProperty(BaseModel):
    """Nested property for complex objects"""
    name: str
    object_type_ref: 'SPGTypeRef'


# ============= Relation =============

class Direction(str, Enum):
    """Edge direction"""
    OUT = "OUT"
    IN = "IN"
    BOTH = "BOTH"


class Relation(BaseModel):
    """
    Relation (edge) definition

    Maps to: Relation in Java

    Example: User-[purchased]->Product
    """
    identifier: SPGTypeIdentifier
    basic_info: BasicInfo
    subject_type_ref: 'SPGTypeRef'  # Source type
    object_type_ref: 'SPGTypeRef'   # Target type
    direction: Direction = Direction.OUT
    properties: Dict[str, Property] = Field(default_factory=dict)

    def get_reverse(self) -> 'Relation':
        """Get reverse relation"""
        reverse_dir = {
            Direction.OUT: Direction.IN,
            Direction.IN: Direction.OUT,
            Direction.BOTH: Direction.BOTH
        }[self.direction]

        return Relation(
            identifier=self.identifier,
            basic_info=self.basic_info,
            subject_type_ref=self.object_type_ref,
            object_type_ref=self.subject_type_ref,
            direction=reverse_dir,
            properties=self.properties
        )


# ============= Type Reference =============

class SPGTypeRef(BaseModel):
    """
    Reference to another SPG type

    Maps to: SPGTypeRef in Java
    """
    identifier: SPGTypeIdentifier
    spg_type_enum: 'SPGTypeEnum'

    def is_basic_type(self) -> bool:
        """Check if basic type (String, Int, etc.)"""
        from .types import SPGTypeEnum
        return self.spg_type_enum == SPGTypeEnum.BASIC_TYPE

    def is_advanced_type(self) -> bool:
        """Check if advanced type (Entity, Concept, Event)"""
        from .types import SPGTypeEnum
        return self.spg_type_enum in [
            SPGTypeEnum.ENTITY_TYPE,
            SPGTypeEnum.CONCEPT_TYPE,
            SPGTypeEnum.EVENT_TYPE
        ]


# Forward references
Property.update_forward_refs()
Relation.update_forward_refs()
SPGTypeRef.update_forward_refs()
```

### 4.3 Constraints

**File: `openspg/core/schema/constraints.py`**

```python
"""
Schema Constraints

Maps to: com.antgroup.openspg.core.schema.model.constraint.*
"""

from pydantic import BaseModel
from typing import Optional, List, Any
from enum import Enum


class ConstraintTypeEnum(str, Enum):
    """Constraint type enumeration"""
    NOT_NULL = "NOT_NULL"
    UNIQUE = "UNIQUE"
    REGULAR = "REGULAR"
    ENUM = "ENUM"
    RANGE = "RANGE"
    MULTI_VAL = "MULTI_VAL"


class Constraint(BaseModel):
    """
    Base constraint class

    Maps to: Constraint in Java
    """
    constraint_type: ConstraintTypeEnum

    def validate(self, value: Any) -> bool:
        """Validate value against constraint"""
        raise NotImplementedError


class NotNullConstraint(Constraint):
    """Value must not be null"""
    constraint_type: ConstraintTypeEnum = ConstraintTypeEnum.NOT_NULL

    def validate(self, value: Any) -> bool:
        return value is not None


class UniqueConstraint(Constraint):
    """Value must be unique"""
    constraint_type: ConstraintTypeEnum = ConstraintTypeEnum.UNIQUE

    # Uniqueness checked at database level
    def validate(self, value: Any) -> bool:
        return True


class RegularConstraint(Constraint):
    """Value must match regex pattern"""
    constraint_type: ConstraintTypeEnum = ConstraintTypeEnum.REGULAR
    pattern: str

    def validate(self, value: Any) -> bool:
        import re
        return bool(re.match(self.pattern, str(value)))


class EnumConstraint(Constraint):
    """Value must be in allowed set"""
    constraint_type: ConstraintTypeEnum = ConstraintTypeEnum.ENUM
    allowed_values: List[Any]

    def validate(self, value: Any) -> bool:
        return value in self.allowed_values


class RangeConstraint(Constraint):
    """Value must be within range"""
    constraint_type: ConstraintTypeEnum = ConstraintTypeEnum.RANGE
    min_value: Optional[float] = None
    max_value: Optional[float] = None

    def validate(self, value: Any) -> bool:
        if self.min_value is not None and value < self.min_value:
            return False
        if self.max_value is not None and value > self.max_value:
            return False
        return True


class MultiValConstraint(Constraint):
    """Property can have multiple values"""
    constraint_type: ConstraintTypeEnum = ConstraintTypeEnum.MULTI_VAL

    def validate(self, value: Any) -> bool:
        # Multi-value is structural, not a validation
        return True
```

---

## 5. Memgraph Integration Layer

### 5.1 Memgraph Adapter

**File: `openspg/adapters/memgraph.py`**

```python
"""
Memgraph Adapter

Provides low-level graph database operations using Memgraph
Memgraph is API-compatible with Neo4j but optimized for real-time streaming
"""

from typing import List, Dict, Any, Optional
from neo4j import GraphDatabase, Session, Transaction
from neo4j.exceptions import ServiceUnavailable
import logging

logger = logging.getLogger(__name__)


class MemgraphAdapter:
    """
    Memgraph database adapter

    Maps to: GraphStoreClient interface in OpenSPG
    Uses Neo4j driver (compatible with Memgraph)
    """

    def __init__(self, uri: str, username: str, password: str):
        """
        Initialize Memgraph connection

        Args:
            uri: Memgraph URI (bolt://localhost:7687)
            username: Database username
            password: Database password
        """
        self.driver = GraphDatabase.driver(uri, auth=(username, password))
        self._verify_connectivity()

    def _verify_connectivity(self):
        """Verify connection to Memgraph"""
        try:
            with self.driver.session() as session:
                result = session.run("RETURN 1 AS num")
                record = result.single()
                if record["num"] != 1:
                    raise ConnectionError("Memgraph connectivity check failed")
            logger.info("Memgraph connection established")
        except ServiceUnavailable as e:
            logger.error(f"Failed to connect to Memgraph: {e}")
            raise

    def close(self):
        """Close driver connection"""
        self.driver.close()

    # =========== Schema Operations ===========

    def create_node_label(self, label: str, properties: Dict[str, str]):
        """
        Create node label with property schema

        Args:
            label: Node label (e.g., "User", "Product")
            properties: Property definitions {name: type}
        """
        with self.driver.session() as session:
            # Memgraph doesn't enforce schema, but we can create indexes
            for prop_name, prop_type in properties.items():
                if prop_type in ['KEYWORD', 'TEXT']:
                    # Create index for string properties
                    query = f"CREATE INDEX ON :{label}({prop_name})"
                    try:
                        session.run(query)
                        logger.info(f"Created index on {label}.{prop_name}")
                    except Exception as e:
                        logger.warning(f"Index creation failed: {e}")

    def create_edge_type(
        self,
        edge_type: str,
        from_label: str,
        to_label: str,
        properties: Dict[str, str]
    ):
        """
        Create edge type schema

        Args:
            edge_type: Edge type name
            from_label: Source node label
            to_label: Target node label
            properties: Edge property definitions
        """
        # Memgraph doesn't enforce edge schema
        # Just log the schema definition
        logger.info(
            f"Edge schema registered: ({from_label})"
            f"-[:{edge_type}]->({to_label})"
        )

    # =========== Vertex Operations ===========

    def upsert_vertex(
        self,
        vertex_id: str,
        labels: List[str],
        properties: Dict[str, Any]
    ) -> str:
        """
        Upsert (insert or update) vertex

        Args:
            vertex_id: Unique vertex ID
            labels: Node labels
            properties: Node properties

        Returns:
            Vertex ID
        """
        with self.driver.session() as session:
            labels_str = ':'.join(labels)

            # Build property map
            props = {'id': vertex_id, **properties}

            # MERGE creates or updates
            query = f"""
            MERGE (n:{labels_str} {{id: $vertex_id}})
            SET n += $properties
            RETURN n.id AS id
            """

            result = session.run(query, vertex_id=vertex_id, properties=props)
            record = result.single()
            return record["id"]

    def get_vertex(
        self,
        vertex_id: str,
        label: Optional[str] = None
    ) -> Optional[Dict[str, Any]]:
        """
        Get vertex by ID

        Args:
            vertex_id: Vertex ID
            label: Optional label filter

        Returns:
            Vertex properties or None
        """
        with self.driver.session() as session:
            label_clause = f":{label}" if label else ""
            query = f"""
            MATCH (n{label_clause} {{id: $vertex_id}})
            RETURN n, labels(n) AS labels
            """

            result = session.run(query, vertex_id=vertex_id)
            record = result.single()

            if not record:
                return None

            node = record["n"]
            return {
                'id': node['id'],
                'labels': record['labels'],
                'properties': dict(node)
            }

    def query_vertices(
        self,
        label: str,
        filters: Optional[Dict[str, Any]] = None,
        limit: int = 100
    ) -> List[Dict[str, Any]]:
        """
        Query vertices by label and filters

        Args:
            label: Node label
            filters: Property filters {key: value}
            limit: Max results

        Returns:
            List of vertex properties
        """
        with self.driver.session() as session:
            where_clauses = []
            params = {}

            if filters:
                for key, value in filters.items():
                    where_clauses.append(f"n.{key} = ${key}")
                    params[key] = value

            where_str = " AND ".join(where_clauses) if where_clauses else "1=1"

            query = f"""
            MATCH (n:{label})
            WHERE {where_str}
            RETURN n, labels(n) AS labels
            LIMIT {limit}
            """

            result = session.run(query, **params)

            vertices = []
            for record in result:
                node = record["n"]
                vertices.append({
                    'id': node['id'],
                    'labels': record['labels'],
                    'properties': dict(node)
                })

            return vertices

    # =========== Edge Operations ===========

    def upsert_edge(
        self,
        edge_id: str,
        edge_type: str,
        from_id: str,
        to_id: str,
        properties: Dict[str, Any]
    ) -> str:
        """
        Upsert edge

        Args:
            edge_id: Unique edge ID
            edge_type: Edge type name
            from_id: Source vertex ID
            to_id: Target vertex ID
            properties: Edge properties

        Returns:
            Edge ID
        """
        with self.driver.session() as session:
            props = {'id': edge_id, **properties}

            query = f"""
            MATCH (a {{id: $from_id}})
            MATCH (b {{id: $to_id}})
            MERGE (a)-[r:{edge_type} {{id: $edge_id}}]->(b)
            SET r += $properties
            RETURN r.id AS id
            """

            result = session.run(
                query,
                from_id=from_id,
                to_id=to_id,
                edge_id=edge_id,
                properties=props
            )

            record = result.single()
            return record["id"]

    def get_edge(self, edge_id: str) -> Optional[Dict[str, Any]]:
        """Get edge by ID"""
        with self.driver.session() as session:
            query = """
            MATCH (a)-[r {id: $edge_id}]->(b)
            RETURN r, type(r) AS type, a.id AS from_id, b.id AS to_id
            """

            result = session.run(query, edge_id=edge_id)
            record = result.single()

            if not record:
                return None

            rel = record["r"]
            return {
                'id': rel['id'],
                'type': record['type'],
                'from_id': record['from_id'],
                'to_id': record['to_id'],
                'properties': dict(rel)
            }

    # =========== Graph Traversal ===========

    def expand(
        self,
        start_id: str,
        edge_types: List[str],
        direction: str = "OUT",
        limit: int = -1
    ) -> List[Dict[str, Any]]:
        """
        Expand from start node

        Args:
            start_id: Start vertex ID
            edge_types: Edge type filters
            direction: OUT, IN, or BOTH
            limit: Max neighbors (-1 = unlimited)

        Returns:
            List of neighbor vertices with edges
        """
        with self.driver.session() as session:
            # Build edge type filter
            type_filter = '|'.join(edge_types) if edge_types else ''

            # Build direction pattern
            if direction == "OUT":
                pattern = f"-[r:{type_filter}]->"
            elif direction == "IN":
                pattern = f"<-[r:{type_filter}]-"
            else:  # BOTH
                pattern = f"-[r:{type_filter}]-"

            limit_clause = f"LIMIT {limit}" if limit > 0 else ""

            query = f"""
            MATCH (a {{id: $start_id}}){pattern}(b)
            RETURN b, r, labels(b) AS labels
            {limit_clause}
            """

            result = session.run(query, start_id=start_id)

            neighbors = []
            for record in result:
                node = record["b"]
                edge = record["r"]
                neighbors.append({
                    'vertex': {
                        'id': node['id'],
                        'labels': record['labels'],
                        'properties': dict(node)
                    },
                    'edge': {
                        'id': edge.get('id'),
                        'type': edge.type,
                        'properties': dict(edge)
                    }
                })

            return neighbors

    # =========== Cypher Query ===========

    def execute_cypher(
        self,
        query: str,
        parameters: Optional[Dict[str, Any]] = None
    ) -> List[Dict[str, Any]]:
        """
        Execute raw Cypher query

        Args:
            query: Cypher query string
            parameters: Query parameters

        Returns:
            Query results as list of records
        """
        with self.driver.session() as session:
            result = session.run(query, parameters or {})

            records = []
            for record in result:
                records.append(dict(record))

            return records

    # =========== Batch Operations ===========

    def batch_upsert_vertices(
        self,
        vertices: List[Dict[str, Any]],
        batch_size: int = 1000
    ):
        """
        Batch upsert vertices

        Args:
            vertices: List of vertex dicts with 'id', 'labels', 'properties'
            batch_size: Batch size for transaction
        """
        with self.driver.session() as session:
            with session.begin_transaction() as tx:
                for i, vertex in enumerate(vertices):
                    labels_str = ':'.join(vertex['labels'])
                    props = {'id': vertex['id'], **vertex['properties']}

                    query = f"""
                    MERGE (n:{labels_str} {{id: $vertex_id}})
                    SET n += $properties
                    """

                    tx.run(query, vertex_id=vertex['id'], properties=props)

                    # Commit in batches
                    if (i + 1) % batch_size == 0:
                        tx.commit()
                        tx = session.begin_transaction()

                # Commit remaining
                tx.commit()

    def batch_upsert_edges(
        self,
        edges: List[Dict[str, Any]],
        batch_size: int = 1000
    ):
        """Batch upsert edges"""
        with self.driver.session() as session:
            with session.begin_transaction() as tx:
                for i, edge in enumerate(edges):
                    props = {'id': edge['id'], **edge['properties']}

                    query = f"""
                    MATCH (a {{id: $from_id}})
                    MATCH (b {{id: $to_id}})
                    MERGE (a)-[r:{edge['type']} {{id: $edge_id}}]->(b)
                    SET r += $properties
                    """

                    tx.run(
                        query,
                        from_id=edge['from_id'],
                        to_id=edge['to_id'],
                        edge_id=edge['id'],
                        properties=props
                    )

                    if (i + 1) % batch_size == 0:
                        tx.commit()
                        tx = session.begin_transaction()

                tx.commit()


# =========== Memgraph-Specific Features ===========

class MemgraphStreamAdapter(MemgraphAdapter):
    """
    Extended adapter with Memgraph streaming features

    Memgraph supports:
    - Kafka integration
    - Real-time graph updates
    - Temporal graph queries
    """

    def create_kafka_stream(
        self,
        stream_name: str,
        topics: List[str],
        bootstrap_servers: str
    ):
        """
        Create Kafka stream in Memgraph

        Memgraph-specific feature for real-time ingestion
        """
        with self.driver.session() as session:
            query = f"""
            CREATE KAFKA STREAM {stream_name}
            TOPICS {', '.join(topics)}
            TRANSFORM transform_procedure
            BOOTSTRAP_SERVERS '{bootstrap_servers}'
            """

            session.run(query)
            logger.info(f"Kafka stream created: {stream_name}")

    def start_stream(self, stream_name: str):
        """Start Kafka stream"""
        with self.driver.session() as session:
            session.run(f"START STREAM {stream_name}")

    def stop_stream(self, stream_name: str):
        """Stop Kafka stream"""
        with self.driver.session() as session:
            session.run(f"STOP STREAM {stream_name}")
```

---

## 6. Builder Pipeline

### 6.1 Builder Core

**File: `openspg/core/builder/pipeline.py`**

```python
"""
Builder Pipeline - Knowledge construction orchestrator

Maps to: com.antgroup.openspg.builder.core.pipeline.*
"""

from typing import List, Dict, Any, Optional
from dataclasses import dataclass
from enum import Enum
import logging

from .operators.base import Operator, OperatorConfig
from .record import SPGRecord
from ..schema.types import BaseSPGType

logger = logging.getLogger(__name__)


# =========== Pipeline Configuration ===========

class PipelineStage(str, Enum):
    """Pipeline execution stages"""
    EXTRACT = "EXTRACT"
    MAPPING = "MAPPING"
    PREDICTING = "PREDICTING"
    LINKING = "LINKING"
    FUSING = "FUSING"
    NORMALIZE = "NORMALIZE"
    VALIDATE = "VALIDATE"
    WRITE = "WRITE"


@dataclass
class PipelineConfig:
    """
    Pipeline configuration

    Maps to: BuilderPipelineConfig in Java
    """
    project_id: str
    pipeline_name: str
    source_config: Dict[str, Any]
    mapping_config: Dict[str, Any]
    operator_configs: List[OperatorConfig]
    sink_config: Dict[str, Any]
    parallel_degree: int = 1
    batch_size: int = 1000


# =========== Pipeline Executor ===========

class BuilderPipeline:
    """
    Main builder pipeline executor

    Orchestrates data flow through operators:
    Source -> Extract -> Map -> [Operators] -> Validate -> Sink

    Maps to: BuilderPipelineExecutor in Java
    """

    def __init__(
        self,
        config: PipelineConfig,
        schema_registry: 'SchemaRegistry',
        graph_adapter: 'MemgraphAdapter'
    ):
        self.config = config
        self.schema_registry = schema_registry
        self.graph_adapter = graph_adapter
        self.operators: Dict[PipelineStage, List[Operator]] = {}

        # Build operator chain
        self._build_operators()

    def _build_operators(self):
        """Build operator chain from config"""
        from .operators.predicting import PredictingOperator
        from .operators.linking import LinkingOperator
        from .operators.fusing import FusingOperator

        operator_map = {
            'predicting': PredictingOperator,
            'linking': LinkingOperator,
            'fusing': FusingOperator
        }

        for op_config in self.config.operator_configs:
            op_class = operator_map.get(op_config.operator_type)
            if not op_class:
                logger.warning(f"Unknown operator: {op_config.operator_type}")
                continue

            operator = op_class(op_config)
            stage = PipelineStage[op_config.operator_type.upper()]

            if stage not in self.operators:
                self.operators[stage] = []
            self.operators[stage].append(operator)

        logger.info(f"Built {len(self.operators)} operator stages")

    def execute(self) -> Dict[str, Any]:
        """
        Execute complete pipeline

        Returns:
            Execution statistics
        """
        stats = {
            'records_processed': 0,
            'records_success': 0,
            'records_failed': 0,
            'stages': {}
        }

        try:
            # Stage 1: Extract
            records = self._extract()
            stats['records_processed'] = len(records)

            # Stage 2: Map to schema
            records = self._map_records(records)
            stats['stages']['mapping'] = len(records)

            # Stage 3: Apply operators
            for stage in [
                PipelineStage.PREDICTING,
                PipelineStage.LINKING,
                PipelineStage.FUSING,
                PipelineStage.NORMALIZE
            ]:
                if stage in self.operators:
                    records = self._apply_operators(stage, records)
                    stats['stages'][stage.value] = len(records)

            # Stage 4: Validate
            records = self._validate(records)
            stats['stages']['validation'] = len(records)

            # Stage 5: Write to graph
            self._write_to_graph(records)
            stats['records_success'] = len(records)

            logger.info(f"Pipeline completed: {stats}")
            return stats

        except Exception as e:
            logger.error(f"Pipeline failed: {e}")
            stats['error'] = str(e)
            raise

    def _extract(self) -> List[Dict[str, Any]]:
        """Extract data from source"""
        source_type = self.config.source_config['type']

        if source_type == 'csv':
            return self._extract_csv()
        elif source_type == 'json':
            return self._extract_json()
        elif source_type == 'database':
            return self._extract_database()
        else:
            raise ValueError(f"Unsupported source type: {source_type}")

    def _extract_csv(self) -> List[Dict[str, Any]]:
        """Extract from CSV file"""
        import csv

        file_path = self.config.source_config['path']
        records = []

        with open(file_path, 'r') as f:
            reader = csv.DictReader(f)
            for row in reader:
                records.append(dict(row))

        logger.info(f"Extracted {len(records)} records from CSV")
        return records

    def _map_records(
        self,
        raw_records: List[Dict[str, Any]]
    ) -> List[SPGRecord]:
        """
        Map raw records to SPG schema

        Uses JSONPath-style mapping:
        {
            "User.id": "$.userId",
            "User.name": "$.userName",
            "User.age": "$.userAge"
        }
        """
        from jsonpath_ng import parse

        mapping = self.config.mapping_config
        spg_records = []

        for raw in raw_records:
            record = SPGRecord()

            for spg_path, json_path in mapping.items():
                # Parse SPG path: "User.id"
                type_name, prop_name = spg_path.split('.', 1)

                # Extract value using JSONPath
                jsonpath_expr = parse(json_path)
                matches = jsonpath_expr.find(raw)

                if matches:
                    value = matches[0].value
                    record.set_property(type_name, prop_name, value)

            spg_records.append(record)

        logger.info(f"Mapped {len(spg_records)} records")
        return spg_records

    def _apply_operators(
        self,
        stage: PipelineStage,
        records: List[SPGRecord]
    ) -> List[SPGRecord]:
        """Apply operators for given stage"""
        operators = self.operators.get(stage, [])

        if not operators:
            return records

        logger.info(f"Applying {len(operators)} operators for {stage.value}")

        result_records = records
        for operator in operators:
            result_records = [
                operator.invoke(record)
                for record in result_records
            ]

        return result_records

    def _validate(self, records: List[SPGRecord]) -> List[SPGRecord]:
        """Validate records against schema"""
        valid_records = []

        for record in records:
            if self._validate_record(record):
                valid_records.append(record)
            else:
                logger.warning(f"Invalid record: {record}")

        logger.info(f"Validated {len(valid_records)}/{len(records)} records")
        return valid_records

    def _validate_record(self, record: SPGRecord) -> bool:
        """Validate single record"""
        # Get schema type
        spg_type = self.schema_registry.get_type(record.get_type_name())

        if not spg_type:
            return False

        # Validate constraints
        for prop in spg_type.properties:
            value = record.get_property(prop.identifier.name)

            if prop.constraint:
                if not prop.constraint.validate(value):
                    return False

        return True

    def _write_to_graph(self, records: List[SPGRecord]):
        """Write records to Memgraph"""
        vertices = []
        edges = []

        for record in records:
            # Extract vertices
            vertex = record.to_vertex()
            vertices.append(vertex)

            # Extract edges (from semantic properties)
            edges.extend(record.to_edges())

        # Batch write
        logger.info(f"Writing {len(vertices)} vertices, {len(edges)} edges")
        self.graph_adapter.batch_upsert_vertices(vertices)
        self.graph_adapter.batch_upsert_edges(edges)
```

### 6.2 Operator Base

**File: `openspg/core/builder/operators/base.py`**

```python
"""
Operator base classes

Maps to: com.antgroup.openspg.builder.core.operator.*
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Generic, TypeVar, Dict, Any

IN = TypeVar('IN')
OUT = TypeVar('OUT')


@dataclass
class OperatorConfig:
    """Operator configuration"""
    operator_type: str  # predicting, linking, fusing
    target_property: str  # Which property to operate on
    implementation: str  # python:module.ClassName or builtin
    params: Dict[str, Any] = None

    def __post_init__(self):
        if self.params is None:
            self.params = {}


class Operator(ABC, Generic[IN, OUT]):
    """
    Base operator interface

    Maps to: Operator<IN, OUT> in Java
    """

    def __init__(self, config: OperatorConfig):
        self.config = config

    @abstractmethod
    def invoke(self, input_data: IN) -> OUT:
        """
        Execute operator logic

        Args:
            input_data: Input record/value

        Returns:
            Transformed output
        """
        pass
```

---

Due to length constraints, I'll now create the complete guide document and commit it.

<function_calls>
<invoke name="TodoWrite">
<parameter name="todos">[{"content": "Design Python architecture mapping", "status": "completed", "activeForm": "Designing Python architecture"}, {"content": "Create KGDSL parser implementation guide", "status": "completed", "activeForm": "Creating parser guide"}, {"content": "Design schema system in Python", "status": "completed", "activeForm": "Designing schema system"}, {"content": "Map Builder pipeline to Python", "status": "completed", "activeForm": "Mapping Builder pipeline"}, {"content": "Design Reasoner engine architecture", "status": "in_progress", "activeForm": "Designing Reasoner engine"}, {"content": "Create Memgraph integration layer", "status": "completed", "activeForm": "Creating Memgraph integration"}, {"content": "Write comprehensive guide document", "status": "in_progress", "activeForm": "Writing guide document"}]
---

## 7. Reasoner Engine

### 7.1 Block IR

**File: `openspg/core/reasoner/blocks.py`**

```python
"""
Block IR (Intermediate Representation)

Logical plan representation for KGDSL queries

Maps to: com.antgroup.openspg.reasoner.lube.block.*
"""

from dataclasses import dataclass, field
from typing import List, Dict, Optional, Set, Any
from abc import ABC, abstractmethod


# =========== IR Fields ===========

class IRField(ABC):
    """Base IR field"""
    name: str


@dataclass
class IRNode(IRField):
    """Node field in IR"""
    name: str
    fields: Set[str] = field(default_factory=set)


@dataclass
class IREdge(IRField):
    """Edge field in IR"""
    name: str
    fields: Set[str] = field(default_factory=set)


@dataclass
class IRProperty(IRField):
    """Property field: s.name"""
    name: str  # Alias (s)
    field: str  # Property name (name)

    def __str__(self):
        return f"{self.name}.{self.field}"


@dataclass
class IRVariable(IRField):
    """Variable field"""
    name: str


@dataclass
class IRPath(IRField):
    """Path field for variable-length paths"""
    name: str
    elements: List[IRField]


@dataclass
class IRGraph:
    """IR Graph structure"""
    nodes: Dict[str, IRNode] = field(default_factory=dict)
    edges: Dict[str, IREdge] = field(default_factory=dict)


# =========== Block Base Class ===========

class Block(ABC):
    """
    Base block class - unresolved logical plan

    Maps to: Block in Scala
    """

    @abstractmethod
    def get_dependencies(self) -> List['Block']:
        """Get dependent blocks"""
        pass

    @abstractmethod
    def get_binds(self) -> 'Binds':
        """Get output bindings"""
        pass

    def pretty(self, indent: int = 0) -> str:
        """Pretty print block tree"""
        raise NotImplementedError


@dataclass
class Binds:
    """Output field bindings"""
    fields: List[IRField] = field(default_factory=list)


# =========== Block Types ===========

@dataclass
class SourceBlock(Block):
    """
    Source block - graph topology definition

    Maps to: SourceBlock in Scala
    """
    graph: IRGraph

    def get_dependencies(self) -> List[Block]:
        return []

    def get_binds(self) -> Binds:
        fields = list(self.graph.nodes.values()) + list(self.graph.edges.values())
        return Binds(fields)

    def pretty(self, indent: int = 0) -> str:
        ind = "    " * indent
        nodes = ", ".join(f"{k}:{v.fields}" for k, v in self.graph.nodes.items())
        edges = ", ".join(self.graph.edges.keys())
        return f"{ind}SourceBlock(nodes=[{nodes}], edges=[{edges}])"


@dataclass
class MatchBlock(Block):
    """
    Match block - pattern matching

    Maps to: MatchBlock in Scala
    """
    patterns: Dict[str, 'GraphPath']
    dependencies: List[Block] = field(default_factory=list)

    def get_dependencies(self) -> List[Block]:
        return self.dependencies

    def get_binds(self) -> Binds:
        # Collect fields from all patterns
        fields = []
        for path in self.patterns.values():
            for node in path.graph_pattern.nodes.values():
                fields.append(IRNode(node.alias, set()))
        return Binds(fields)

    def pretty(self, indent: int = 0) -> str:
        ind = "    " * indent
        patterns_str = ", ".join(self.patterns.keys())
        deps = "\n".join(d.pretty(indent + 1) for d in self.dependencies)
        return f"{ind}MatchBlock(patterns=[{patterns_str}])\n{deps}"


@dataclass
class FilterBlock(Block):
    """
    Filter block - apply constraints

    Maps to: FilterBlock in Scala
    """
    rule: 'Rule'
    dependencies: List[Block]

    def get_dependencies(self) -> List[Block]:
        return self.dependencies

    def get_binds(self) -> Binds:
        return self.dependencies[0].get_binds()

    def pretty(self, indent: int = 0) -> str:
        ind = "    " * indent
        deps = "\n".join(d.pretty(indent + 1) for d in self.dependencies)
        return f"{ind}FilterBlock(rule={self.rule.name})\n{deps}"


@dataclass
class ProjectBlock(Block):
    """
    Project block - transformations and assignments

    Maps to: ProjectBlock in Scala
    """
    projects: 'ProjectFields'
    dependencies: List[Block]

    def get_dependencies(self) -> List[Block]:
        return self.dependencies

    def get_binds(self) -> Binds:
        # Add new projected fields to existing bindings
        existing = self.dependencies[0].get_binds()
        new_fields = list(self.projects.fields.keys())
        return Binds(existing.fields + new_fields)

    def pretty(self, indent: int = 0) -> str:
        ind = "    " * indent
        fields_str = ", ".join(str(f) for f in self.projects.fields.keys())
        deps = "\n".join(d.pretty(indent + 1) for d in self.dependencies)
        return f"{ind}ProjectBlock(fields=[{fields_str}])\n{deps}"


@dataclass
class AggregationBlock(Block):
    """
    Aggregation block - group by aggregations

    Maps to: AggregationBlock in Scala
    """
    aggregations: 'Aggregations'
    group_by: List[IRField]
    dependencies: List[Block]

    def get_dependencies(self) -> List[Block]:
        return self.dependencies

    def get_binds(self) -> Binds:
        # Group fields + aggregation results
        fields = self.group_by + list(self.aggregations.pairs.keys())
        return Binds(fields)

    def pretty(self, indent: int = 0) -> str:
        ind = "    " * indent
        group_str = ", ".join(str(g) for g in self.group_by)
        agg_str = ", ".join(str(k) for k in self.aggregations.pairs.keys())
        deps = "\n".join(d.pretty(indent + 1) for d in self.dependencies)
        return f"{ind}AggregationBlock(group=[{group_str}], agg=[{agg_str}])\n{deps}"


@dataclass
class TableResultBlock(Block):
    """
    Table result block - final output

    Maps to: TableResultBlock in Scala
    """
    select_list: List[IRField]
    output_columns: List[str]
    distinct: bool
    dependencies: List[Block]

    def get_dependencies(self) -> List[Block]:
        return self.dependencies

    def get_binds(self) -> Binds:
        return Binds(self.select_list)

    def pretty(self, indent: int = 0) -> str:
        ind = "    " * indent
        cols = ", ".join(self.output_columns)
        deps = "\n".join(d.pretty(indent + 1) for d in self.dependencies)
        return f"{ind}TableResultBlock(columns=[{cols}], distinct={self.distinct})\n{deps}"


@dataclass
class DDLBlock(Block):
    """
    DDL block - schema modification (Define statements)

    Maps to: DDLBlock in Scala
    """
    ddl_ops: Set['DDLOp']
    dependencies: List[Block]

    def get_dependencies(self) -> List[Block]:
        return self.dependencies

    def get_binds(self) -> Binds:
        return Binds()

    def pretty(self, indent: int = 0) -> str:
        ind = "    " * indent
        ops_str = ", ".join(type(op).__name__ for op in self.ddl_ops)
        deps = "\n".join(d.pretty(indent + 1) for d in self.dependencies)
        return f"{ind}DDLBlock(ops=[{ops_str}])\n{deps}"


# =========== Rules ===========

class Rule(ABC):
    """Base rule class"""
    name: str

    @abstractmethod
    def get_expr(self) -> 'Expr':
        pass

    @abstractmethod
    def get_output(self) -> IRField:
        pass


@dataclass
class LogicRule(Rule):
    """Logic rule - boolean constraint"""
    name: str
    description: str
    expr: 'Expr'

    def get_expr(self) -> 'Expr':
        return self.expr

    def get_output(self) -> IRField:
        return IRVariable(self.name)


@dataclass
class ProjectRule(Rule):
    """Project rule - assignment"""
    output: IRField
    expr: 'Expr'

    @property
    def name(self) -> str:
        return self.output.name

    def get_expr(self) -> 'Expr':
        return self.expr

    def get_output(self) -> IRField:
        return self.output


# =========== Supporting Classes ===========

@dataclass
class ProjectFields:
    """Project field mappings"""
    fields: Dict[IRField, ProjectRule]


@dataclass
class Aggregations:
    """Aggregation pairs"""
    pairs: Dict[IRField, 'AggOpExpr']


@dataclass
class DDLOp(ABC):
    """Base DDL operation"""
    pass


@dataclass
class AddVertex(DDLOp):
    """Add vertex type"""
    element: 'EntityElement'
    properties: Dict[str, 'Expr']


@dataclass
class AddPredicate(DDLOp):
    """Add predicate (edge type)"""
    predicate: 'PredicateElement'
    is_define: bool = False


@dataclass
class AddProperty(DDLOp):
    """Add property"""
    element: 'EntityElement'
    property_name: str
    property_type: 'KgType'
    is_define: bool = False
```

### 7.2 Physical Plan & Execution

**File: `openspg/core/reasoner/executor.py`**

```python
"""
Query Executor - Executes physical plan against Memgraph

Maps to: com.antgroup.openspg.reasoner.runner.*
"""

from typing import List, Dict, Any, Optional
import logging

from .blocks import *
from .physical_plan import PhysicalPlan, PhysicalOperator
from ..parser.expr_parser import *
from ...adapters.memgraph import MemgraphAdapter

logger = logging.getLogger(__name__)


class QueryExecutor:
    """
    Execute KGDSL query against Memgraph

    Flow:
        Block IR -> Logical Plan -> Physical Plan -> Cypher -> Execute
    """

    def __init__(self, graph_adapter: MemgraphAdapter):
        self.graph = graph_adapter
        self.planner = PhysicalPlanner(graph_adapter)

    def execute_query(self, block: Block) -> List[Dict[str, Any]]:
        """
        Execute KGDSL query

        Args:
            block: Parsed block IR

        Returns:
            Query results
        """
        # Generate physical plan
        physical_plan = self.planner.plan(block)

        # Compile to Cypher
        cypher_query = self._compile_to_cypher(physical_plan)

        logger.info(f"Executing Cypher:\n{cypher_query}")

        # Execute against Memgraph
        results = self.graph.execute_cypher(cypher_query)

        return results

    def _compile_to_cypher(self, plan: PhysicalPlan) -> str:
        """
        Compile physical plan to Cypher query

        OpenSPG Block IR -> Cypher translation
        """
        compiler = CypherCompiler()
        return compiler.compile(plan.root_operator)


class CypherCompiler:
    """
    Compile physical operators to Cypher

    Maps OpenSPG patterns to Memgraph Cypher
    """

    def compile(self, operator: PhysicalOperator) -> str:
        """Compile operator tree to Cypher"""

        # Dispatch based on operator type
        if isinstance(operator, ScanOperator):
            return self._compile_scan(operator)
        elif isinstance(operator, ExpandOperator):
            return self._compile_expand(operator)
        elif isinstance(operator, FilterOperator):
            return self._compile_filter(operator)
        elif isinstance(operator, ProjectOperator):
            return self._compile_project(operator)
        elif isinstance(operator, AggregateOperator):
            return self._compile_aggregate(operator)
        elif isinstance(operator, JoinOperator):
            return self._compile_join(operator)
        else:
            raise NotImplementedError(f"Operator {type(operator)} not supported")

    def _compile_scan(self, op: 'ScanOperator') -> str:
        """
        Compile scan operator

        Block: SourceBlock + MatchBlock
        Cypher: MATCH (n:Label)
        """
        labels = ":".join(op.labels)
        alias = op.alias

        # Build WHERE clause from filters
        where_clauses = []
        if op.filters:
            for field, value in op.filters.items():
                where_clauses.append(f"{alias}.{field} = {self._to_cypher_value(value)}")

        where_str = " AND ".join(where_clauses) if where_clauses else ""
        where_clause = f"WHERE {where_str}" if where_str else ""

        return f"MATCH ({alias}:{labels}) {where_clause}"

    def _compile_expand(self, op: 'ExpandOperator') -> str:
        """
        Compile expand operator

        Block: MatchBlock with edges
        Cypher: MATCH (a)-[r:TYPE]->(b)
        """
        source_alias = op.source_alias
        edge_alias = op.edge_alias
        target_alias = op.target_alias
        edge_types = "|".join(op.edge_types)

        # Direction
        if op.direction == "OUT":
            pattern = f"({source_alias})-[{edge_alias}:{edge_types}]->({target_alias})"
        elif op.direction == "IN":
            pattern = f"({source_alias})<-[{edge_alias}:{edge_types}]-({target_alias})"
        else:  # BOTH
            pattern = f"({source_alias})-[{edge_alias}:{edge_types}]-({target_alias})"

        # Variable-length path
        if op.min_hops or op.max_hops:
            min_h = op.min_hops or 1
            max_h = op.max_hops or 5
            pattern = pattern.replace(
                f"[{edge_alias}:{edge_types}]",
                f"[{edge_alias}:{edge_types}*{min_h}..{max_h}]"
            )

        # Per-node limit (not standard Cypher, needs workaround)
        limit_clause = ""
        if op.per_node_limit > 0:
            # Use subquery for per-node limit
            limit_clause = f"WITH {source_alias}, collect({target_alias})[..{op.per_node_limit}] AS limited_{target_alias} UNWIND limited_{target_alias} AS {target_alias}"

        return f"MATCH {pattern} {limit_clause}"

    def _compile_filter(self, op: 'FilterOperator') -> str:
        """
        Compile filter operator

        Block: FilterBlock
        Cypher: WHERE expression
        """
        condition = self._compile_expr(op.condition)
        return f"WHERE {condition}"

    def _compile_project(self, op: 'ProjectOperator') -> str:
        """
        Compile project operator

        Block: ProjectBlock
        Cypher: WITH/RETURN with expressions
        """
        projections = []
        for output_field, expr in op.projections.items():
            cypher_expr = self._compile_expr(expr)
            projections.append(f"{cypher_expr} AS {output_field}")

        return "WITH " + ", ".join(projections)

    def _compile_aggregate(self, op: 'AggregateOperator') -> str:
        """
        Compile aggregate operator

        Block: AggregationBlock
        Cypher: aggregation with GROUP BY
        """
        # Group by fields
        group_fields = [str(f) for f in op.group_by]

        # Aggregations
        agg_exprs = []
        for output, agg in op.aggregations.items():
            cypher_agg = self._compile_aggregation(agg)
            agg_exprs.append(f"{cypher_agg} AS {output}")

        group_str = ", ".join(group_fields)
        agg_str = ", ".join(agg_exprs)

        if group_fields:
            return f"WITH {group_str}, {agg_str}"
        else:
            return f"WITH {agg_str}"

    def _compile_expr(self, expr: Expr) -> str:
        """Compile expression to Cypher"""
        if isinstance(expr, Ref):
            return expr.name

        elif isinstance(expr, UnaryOpExpr):
            if isinstance(expr.op, GetField):
                arg = self._compile_expr(expr.arg)
                return f"{arg}.{expr.op.field_name}"
            else:
                arg = self._compile_expr(expr.arg)
                return f"{expr.op.value}({arg})"

        elif isinstance(expr, BinaryOpExpr):
            left = self._compile_expr(expr.left)
            right = self._compile_expr(expr.right)

            op_map = {
                BinaryOp.EQUAL: "=",
                BinaryOp.NOT_EQUAL: "<>",
                BinaryOp.GREATER_THAN: ">",
                BinaryOp.LESS_THAN: "<",
                BinaryOp.GREATER_EQUAL: ">=",
                BinaryOp.LESS_EQUAL: "<=",
                BinaryOp.AND: "AND",
                BinaryOp.OR: "OR",
                BinaryOp.ADD: "+",
                BinaryOp.SUB: "-",
                BinaryOp.MUL: "*",
                BinaryOp.DIV: "/",
                BinaryOp.IN: "IN"
            }

            op_str = op_map.get(expr.op, expr.op.value)
            return f"({left} {op_str} {right})"

        elif isinstance(expr, VString):
            return f"'{expr.value}'"

        elif isinstance(expr, VLong):
            return str(expr.value)

        elif isinstance(expr, VDouble):
            return str(expr.value)

        elif isinstance(expr, VBoolean):
            return "true" if expr.value else "false"

        elif isinstance(expr, FunctionExpr):
            args = ", ".join(self._compile_expr(a) for a in expr.args)
            return f"{expr.name}({args})"

        else:
            raise NotImplementedError(f"Expression {type(expr)} not supported")

    def _compile_aggregation(self, agg: AggOpExpr) -> str:
        """Compile aggregation expression"""
        arg = self._compile_expr(agg.agg_expr)

        agg_map = {
            AggOp.SUM: "sum",
            AggOp.AVG: "avg",
            AggOp.COUNT: "count",
            AggOp.MIN: "min",
            AggOp.MAX: "max"
        }

        func = agg_map[agg.agg_op]
        return f"{func}({arg})"

    def _to_cypher_value(self, value: Any) -> str:
        """Convert Python value to Cypher literal"""
        if isinstance(value, str):
            return f"'{value}'"
        elif isinstance(value, bool):
            return "true" if value else "false"
        else:
            return str(value)


# =========== Physical Operators ===========

@dataclass
class PhysicalOperator:
    """Base physical operator"""
    pass


@dataclass
class ScanOperator(PhysicalOperator):
    """Scan nodes by label"""
    alias: str
    labels: List[str]
    filters: Dict[str, Any] = field(default_factory=dict)


@dataclass
class ExpandOperator(PhysicalOperator):
    """Expand edges"""
    source_alias: str
    edge_alias: str
    target_alias: str
    edge_types: List[str]
    direction: str = "OUT"
    min_hops: Optional[int] = None
    max_hops: Optional[int] = None
    per_node_limit: int = -1


@dataclass
class FilterOperator(PhysicalOperator):
    """Filter rows"""
    condition: Expr


@dataclass
class ProjectOperator(PhysicalOperator):
    """Project/transform fields"""
    projections: Dict[str, Expr]


@dataclass
class AggregateOperator(PhysicalOperator):
    """Aggregate with group by"""
    group_by: List[IRField]
    aggregations: Dict[str, AggOpExpr]


@dataclass
class JoinOperator(PhysicalOperator):
    """Join two streams"""
    left: PhysicalOperator
    right: PhysicalOperator
    join_keys: List[tuple[str, str]]


class PhysicalPlanner:
    """Convert logical plan to physical operators"""

    def __init__(self, graph_adapter: MemgraphAdapter):
        self.graph = graph_adapter

    def plan(self, block: Block) -> PhysicalPlan:
        """Generate physical plan from block"""
        root_op = self._plan_block(block)
        return PhysicalPlan(root_operator=root_op)

    def _plan_block(self, block: Block) -> PhysicalOperator:
        """Recursively plan block tree"""
        if isinstance(block, SourceBlock):
            # Generate scan operators
            ops = []
            for alias, node in block.graph.nodes.items():
                ops.append(ScanOperator(alias=alias, labels=list(node.name)))
            return ops[0] if ops else None

        elif isinstance(block, MatchBlock):
            # Generate expand operators
            # Simplified: just return scan for now
            return self._plan_block(block.dependencies[0])

        elif isinstance(block, FilterBlock):
            dep_op = self._plan_block(block.dependencies[0])
            return FilterOperator(condition=block.rule.get_expr())

        elif isinstance(block, ProjectBlock):
            dep_op = self._plan_block(block.dependencies[0])
            projections = {
                str(field): rule.get_expr()
                for field, rule in block.projects.fields.items()
            }
            return ProjectOperator(projections=projections)

        elif isinstance(block, AggregationBlock):
            dep_op = self._plan_block(block.dependencies[0])
            return AggregateOperator(
                group_by=block.group_by,
                aggregations=block.aggregations.pairs
            )

        else:
            # Fallback: plan dependencies
            if block.get_dependencies():
                return self._plan_block(block.get_dependencies()[0])
            return None


@dataclass
class PhysicalPlan:
    """Complete physical execution plan"""
    root_operator: PhysicalOperator
```

---

## 8. API Layer

### 8.1 FastAPI Application

**File: `openspg/api/main.py`**

```python
"""
FastAPI Application - REST API for OpenSPG

Provides HTTP endpoints for:
- Schema management
- Query execution
- Builder jobs
"""

from fastapi import FastAPI, HTTPException, Depends
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import List, Dict, Any, Optional
import logging

from ..core.parser.dsl_parser import OpenSPGDslParser
from ..core.reasoner.executor import QueryExecutor
from ..services.schema_service import SchemaService
from ..services.reasoner_service import ReasonerService
from ..adapters.memgraph import MemgraphAdapter
from ..utils.config import settings

logger = logging.getLogger(__name__)

# Create FastAPI app
app = FastAPI(
    title="OpenSPG-Py",
    description="Python implementation of OpenSPG Knowledge Graph Engine",
    version="0.1.0"
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# =========== Dependencies ===========

def get_graph_adapter() -> MemgraphAdapter:
    """Get Memgraph adapter instance"""
    return MemgraphAdapter(
        uri=settings.MEMGRAPH_URI,
        username=settings.MEMGRAPH_USER,
        password=settings.MEMGRAPH_PASSWORD
    )


def get_reasoner_service(
    graph: MemgraphAdapter = Depends(get_graph_adapter)
) -> ReasonerService:
    """Get reasoner service"""
    return ReasonerService(graph)


# =========== Request/Response Models ===========

class KGDSLQueryRequest(BaseModel):
    """KGDSL query request"""
    query: str
    parameters: Optional[Dict[str, Any]] = None


class KGDSLQueryResponse(BaseModel):
    """KGDSL query response"""
    success: bool
    results: List[Dict[str, Any]]
    row_count: int
    execution_time_ms: float


class SchemaTypeRequest(BaseModel):
    """Schema type creation request"""
    type_name: str
    type_category: str  # ENTITY_TYPE, CONCEPT_TYPE, etc.
    properties: List[Dict[str, Any]]
    relations: Optional[List[Dict[str, Any]]] = None


# =========== Health Check ===========

@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {"status": "healthy", "service": "openspg-py"}


# =========== Query Endpoints ===========

@app.post("/api/v1/query", response_model=KGDSLQueryResponse)
async def execute_query(
    request: KGDSLQueryRequest,
    reasoner: ReasonerService = Depends(get_reasoner_service)
):
    """
    Execute KGDSL query

    Example:
        POST /api/v1/query
        {
            "query": "GraphStructure { (s:User)-[e:knows]->(o:User) } Rule {} Action { get(s.id, o.id) }",
            "parameters": {"userId": "123"}
        }
    """
    try:
        import time
        start_time = time.time()

        # Execute query
        results = reasoner.execute_query(
            request.query,
            request.parameters or {}
        )

        execution_time = (time.time() - start_time) * 1000

        return KGDSLQueryResponse(
            success=True,
            results=results,
            row_count=len(results),
            execution_time_ms=execution_time
        )

    except Exception as e:
        logger.error(f"Query execution failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/v1/query/parse")
async def parse_query(request: KGDSLQueryRequest):
    """
    Parse KGDSL query without execution (validation)
    """
    try:
        parser = OpenSPGDslParser()
        block = parser.parse(request.query)

        return {
            "success": True,
            "block_type": type(block).__name__,
            "parameters": list(parser.parameters),
            "pretty": block.pretty()
        }

    except Exception as e:
        logger.error(f"Query parsing failed: {e}")
        raise HTTPException(status_code=400, detail=str(e))


# =========== Schema Endpoints ===========

@app.post("/api/v1/schema/types")
async def create_schema_type(
    request: SchemaTypeRequest,
    graph: MemgraphAdapter = Depends(get_graph_adapter)
):
    """
    Create new schema type

    Example:
        POST /api/v1/schema/types
        {
            "type_name": "User",
            "type_category": "ENTITY_TYPE",
            "properties": [
                {"name": "id", "type": "String"},
                {"name": "age", "type": "Integer"}
            ]
        }
    """
    try:
        schema_service = SchemaService(graph)

        schema_type = schema_service.create_type(
            type_name=request.type_name,
            type_category=request.type_category,
            properties=request.properties,
            relations=request.relations or []
        )

        return {
            "success": True,
            "type_id": str(schema_type.get_identifier()),
            "message": f"Type {request.type_name} created"
        }

    except Exception as e:
        logger.error(f"Schema type creation failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/v1/schema/types/{type_name}")
async def get_schema_type(
    type_name: str,
    graph: MemgraphAdapter = Depends(get_graph_adapter)
):
    """Get schema type definition"""
    try:
        schema_service = SchemaService(graph)
        schema_type = schema_service.get_type(type_name)

        if not schema_type:
            raise HTTPException(status_code=404, detail=f"Type {type_name} not found")

        return schema_type.dict()

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get schema type: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# =========== Builder Endpoints ===========

@app.post("/api/v1/builder/jobs")
async def create_builder_job(
    config: Dict[str, Any],
    graph: MemgraphAdapter = Depends(get_graph_adapter)
):
    """
    Create and execute builder job

    Example:
        POST /api/v1/builder/jobs
        {
            "pipeline_name": "UserImport",
            "source": {"type": "csv", "path": "/data/users.csv"},
            "mapping": {"User.id": "$.userId", ...},
            "operators": [...]
        }
    """
    try:
        from ..core.builder.pipeline import BuilderPipeline, PipelineConfig

        pipeline_config = PipelineConfig(**config)
        pipeline = BuilderPipeline(pipeline_config, None, graph)

        stats = pipeline.execute()

        return {
            "success": True,
            "job_id": "generated_job_id",
            "statistics": stats
        }

    except Exception as e:
        logger.error(f"Builder job failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# =========== Startup/Shutdown ===========

@app.on_event("startup")
async def startup_event():
    """Initialize on startup"""
    logger.info("OpenSPG-Py starting up...")

    # Test Memgraph connection
    try:
        graph = get_graph_adapter()
        logger.info("Memgraph connection successful")
        graph.close()
    except Exception as e:
        logger.error(f"Failed to connect to Memgraph: {e}")


@app.on_event("shutdown")
async def shutdown_event():
    """Cleanup on shutdown"""
    logger.info("OpenSPG-Py shutting down...")
```

---

## 9. Deployment Guide

### 9.1 Docker Compose Setup

**File: `docker-compose.yml`**

```yaml
version: '3.8'

services:
  # Memgraph - Graph Database
  memgraph:
    image: memgraph/memgraph-platform:latest
    ports:
      - "7687:7687"  # Bolt protocol
      - "3000:3000"  # Memgraph Lab UI
      - "7444:7444"  # Monitoring
    environment:
      - MEMGRAPH_CONFIG=--storage-parallel-schema-recovery=true
    volumes:
      - memgraph_data:/var/lib/memgraph
      - memgraph_log:/var/log/memgraph
    command: ["--log-level=INFO"]
    networks:
      - openspg-net

  # Redis - Caching
  redis:
    image: redis:7-alpine
    ports:
      - "6379:6379"
    volumes:
      - redis_data:/data
    networks:
      - openspg-net

  # Elasticsearch - Full-text search
  elasticsearch:
    image: docker.elastic.co/elasticsearch/elasticsearch:8.11.0
    environment:
      - discovery.type=single-node
      - "ES_JAVA_OPTS=-Xms512m -Xmx512m"
      - xpack.security.enabled=false
    ports:
      - "9200:9200"
    volumes:
      - es_data:/usr/share/elasticsearch/data
    networks:
      - openspg-net

  # PostgreSQL - Metadata storage
  postgres:
    image: postgres:15-alpine
    environment:
      POSTGRES_DB: openspg
      POSTGRES_USER: openspg
      POSTGRES_PASSWORD: openspg123
    ports:
      - "5432:5432"
    volumes:
      - postgres_data:/var/lib/postgresql/data
    networks:
      - openspg-net

  # OpenSPG-Py API
  openspg-api:
    build:
      context: .
      dockerfile: Dockerfile
    ports:
      - "8000:8000"
    environment:
      - MEMGRAPH_URI=bolt://memgraph:7687
      - MEMGRAPH_USER=
      - MEMGRAPH_PASSWORD=
      - REDIS_URL=redis://redis:6379/0
      - ELASTICSEARCH_URL=http://elasticsearch:9200
      - DATABASE_URL=postgresql://openspg:openspg123@postgres:5432/openspg
    depends_on:
      - memgraph
      - redis
      - elasticsearch
      - postgres
    networks:
      - openspg-net
    command: uvicorn openspg.api.main:app --host 0.0.0.0 --port 8000 --reload

volumes:
  memgraph_data:
  memgraph_log:
  redis_data:
  es_data:
  postgres_data:

networks:
  openspg-net:
    driver: bridge
```

### 9.2 Dockerfile

**File: `Dockerfile`**

```dockerfile
FROM python:3.11-slim

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    build-essential \
    curl \
    git \
    && rm -rf /var/lib/apt/lists/*

# Install ANTLR4 runtime
RUN pip install --no-cache-dir antlr4-python3-runtime==4.13.1

# Copy requirements
COPY pyproject.toml poetry.lock ./

# Install Poetry
RUN pip install poetry==1.7.0

# Install dependencies
RUN poetry config virtualenvs.create false \
    && poetry install --no-interaction --no-ansi

# Copy application
COPY . .

# Generate ANTLR parsers
RUN ./scripts/generate_antlr.sh

# Expose port
EXPOSE 8000

# Run application
CMD ["uvicorn", "openspg.api.main:app", "--host", "0.0.0.0", "--port", "8000"]
```

### 9.3 Python Dependencies

**File: `pyproject.toml`**

```toml
[tool.poetry]
name = "openspg-py"
version = "0.1.0"
description = "Python implementation of OpenSPG Knowledge Graph Engine"
authors = ["Your Name <your.email@example.com>"]

[tool.poetry.dependencies]
python = "^3.10"

# Web framework
fastapi = "^0.104.0"
uvicorn = {extras = ["standard"], version = "^0.24.0"}
pydantic = "^2.5.0"

# ANTLR4 parser
antlr4-python3-runtime = "4.13.1"

# Graph database
neo4j = "^5.14.0"  # Compatible with Memgraph

# Search
elasticsearch = "^8.11.0"

# Cache
redis = "^5.0.0"
hiredis = "^2.2.3"

# Database
sqlalchemy = "^2.0.0"
alembic = "^1.12.0"
psycopg2-binary = "^2.9.9"

# Data processing
pandas = "^2.1.0"
jsonpath-ng = "^1.6.0"
orjson = "^3.9.0"

# Utilities
python-dotenv = "^1.0.0"
loguru = "^0.7.0"
tenacity = "^8.2.0"

# Background jobs
celery = {extras = ["redis"], version = "^5.3.0"}

[tool.poetry.dev-dependencies]
pytest = "^7.4.0"
pytest-asyncio = "^0.21.0"
pytest-cov = "^4.1.0"
black = "^23.11.0"
ruff = "^0.1.0"
mypy = "^1.7.0"

[build-system]
requires = ["poetry-core>=1.0.0"]
build-backend = "poetry.core.masonry.api"
```

### 9.4 Configuration

**File: `openspg/utils/config.py`**

```python
"""
Configuration management
"""

from pydantic_settings import BaseSettings
from typing import Optional


class Settings(BaseSettings):
    """Application settings"""

    # Memgraph
    MEMGRAPH_URI: str = "bolt://localhost:7687"
    MEMGRAPH_USER: str = ""
    MEMGRAPH_PASSWORD: str = ""

    # Redis
    REDIS_URL: str = "redis://localhost:6379/0"

    # Elasticsearch
    ELASTICSEARCH_URL: str = "http://localhost:9200"

    # PostgreSQL
    DATABASE_URL: str = "postgresql://openspg:openspg123@localhost:5432/openspg"

    # API
    API_HOST: str = "0.0.0.0"
    API_PORT: int = 8000
    API_WORKERS: int = 4

    # Logging
    LOG_LEVEL: str = "INFO"

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"


settings = Settings()
```

### 9.5 Startup Scripts

**File: `scripts/init_system.py`**

```python
"""
Initialize OpenSPG-Py system

- Create database tables
- Initialize schema registry
- Load sample data
"""

import asyncio
from openspg.adapters.memgraph import MemgraphAdapter
from openspg.utils.config import settings
import logging

logger = logging.getLogger(__name__)


async def init_memgraph():
    """Initialize Memgraph schema"""
    logger.info("Initializing Memgraph...")

    graph = MemgraphAdapter(
        uri=settings.MEMGRAPH_URI,
        username=settings.MEMGRAPH_USER,
        password=settings.MEMGRAPH_PASSWORD
    )

    # Create indexes for common node types
    base_types = ["User", "Company", "Product", "Entity", "Concept", "Event"]

    for node_type in base_types:
        try:
            graph.execute_cypher(f"CREATE INDEX ON :{node_type}(id)")
            logger.info(f"Created index on {node_type}.id")
        except Exception as e:
            logger.warning(f"Index creation failed for {node_type}: {e}")

    graph.close()
    logger.info("Memgraph initialization complete")


async def init_postgres():
    """Initialize PostgreSQL tables"""
    logger.info("Initializing PostgreSQL...")

    # Use Alembic for migrations
    from alembic import command
    from alembic.config import Config

    alembic_cfg = Config("alembic.ini")
    command.upgrade(alembic_cfg, "head")

    logger.info("PostgreSQL initialization complete")


async def load_sample_data():
    """Load sample schema and data"""
    logger.info("Loading sample data...")

    graph = MemgraphAdapter(
        uri=settings.MEMGRAPH_URI,
        username=settings.MEMGRAPH_USER,
        password=settings.MEMGRAPH_PASSWORD
    )

    # Sample: Create some users
    sample_users = [
        {"id": "u1", "name": "Alice", "age": 30},
        {"id": "u2", "name": "Bob", "age": 25},
        {"id": "u3", "name": "Charlie", "age": 35}
    ]

    for user in sample_users:
        graph.upsert_vertex(
            vertex_id=user["id"],
            labels=["User"],
            properties=user
        )

    # Sample: Create relationships
    graph.upsert_edge(
        edge_id="e1",
        edge_type="knows",
        from_id="u1",
        to_id="u2",
        properties={"since": 2020}
    )

    graph.upsert_edge(
        edge_id="e2",
        edge_type="knows",
        from_id="u2",
        to_id="u3",
        properties={"since": 2021}
    )

    graph.close()
    logger.info("Sample data loaded")


async def main():
    """Main initialization"""
    await init_memgraph()
    await init_postgres()
    await load_sample_data()
    logger.info("System initialization complete!")


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    asyncio.run(main())
```

---

## 10. Complete Example: End-to-End

### 10.1 Define Schema

```python
from openspg.core.schema.types import EntityType, BasicInfo, SPGTypeIdentifier
from openspg.core.schema.predicates import Property, Relation, SPGTypeRef
from openspg.services.schema_service import SchemaService

# Create schema service
schema_service = SchemaService(graph_adapter)

# Define User entity type
user_type = EntityType(
    basic_info=BasicInfo(
        identifier=SPGTypeIdentifier(name="User"),
        description="User entity"
    ),
    properties=[
        Property(
            identifier=SPGTypeIdentifier(name="id"),
            object_type_ref=SPGTypeRef(
                identifier=SPGTypeIdentifier(name="String"),
                spg_type_enum=SPGTypeEnum.BASIC_TYPE
            )
        ),
        Property(
            identifier=SPGTypeIdentifier(name="age"),
            object_type_ref=SPGTypeRef(
                identifier=SPGTypeIdentifier(name="Integer"),
                spg_type_enum=SPGTypeEnum.BASIC_TYPE
            )
        )
    ],
    relations=[
        Relation(
            identifier=SPGTypeIdentifier(name="knows"),
            subject_type_ref=SPGTypeRef(
                identifier=SPGTypeIdentifier(name="User"),
                spg_type_enum=SPGTypeEnum.ENTITY_TYPE
            ),
            object_type_ref=SPGTypeRef(
                identifier=SPGTypeIdentifier(name="User"),
                spg_type_enum=SPGTypeEnum.ENTITY_TYPE
            )
        )
    ]
)

# Register schema
schema_service.register_type(user_type)
```

### 10.2 Load Data

```python
from openspg.core.builder.pipeline import BuilderPipeline, PipelineConfig

# Configure pipeline
config = PipelineConfig(
    project_id="demo",
    pipeline_name="user_import",
    source_config={
        "type": "csv",
        "path": "/data/users.csv"
    },
    mapping_config={
        "User.id": "$.user_id",
        "User.name": "$.full_name",
        "User.age": "$.age"
    },
    operator_configs=[],
    sink_config={"type": "memgraph"}
)

# Execute pipeline
pipeline = BuilderPipeline(config, schema_service, graph_adapter)
stats = pipeline.execute()

print(f"Loaded {stats['records_success']} users")
```

### 10.3 Execute Query

```python
from openspg.core.parser.dsl_parser import OpenSPGDslParser
from openspg.core.reasoner.executor import QueryExecutor

# Parse KGDSL query
dsl_query = """
GraphStructure {
    (s:User)-[e:knows]->(o:User)
}
Rule {
    R1: s.age > 25
}
Action {
    get(s.id, s.name, o.id, o.name)
}
"""

parser = OpenSPGDslParser()
block = parser.parse(dsl_query)

# Execute query
executor = QueryExecutor(graph_adapter)
results = executor.execute_query(block)

# Print results
for row in results:
    print(f"{row['s.id']} ({row['s.name']}) knows {row['o.id']} ({row['o.name']})")
```

---

## 11. Testing

**File: `tests/test_integration.py`**

```python
"""
Integration test
"""

import pytest
from openspg.core.parser.dsl_parser import OpenSPGDslParser
from openspg.core.reasoner.executor import QueryExecutor
from openspg.adapters.memgraph import MemgraphAdapter


@pytest.fixture
def graph_adapter():
    """Setup test graph adapter"""
    adapter = MemgraphAdapter(
        uri="bolt://localhost:7687",
        username="",
        password=""
    )

    # Clear test data
    adapter.execute_cypher("MATCH (n) DETACH DELETE n")

    yield adapter

    adapter.close()


def test_simple_query(graph_adapter):
    """Test simple KGDSL query"""
    # Insert test data
    graph_adapter.upsert_vertex("u1", ["User"], {"name": "Alice", "age": 30})
    graph_adapter.upsert_vertex("u2", ["User"], {"name": "Bob", "age": 25})
    graph_adapter.upsert_edge("e1", "knows", "u1", "u2", {})

    # Parse query
    parser = OpenSPGDslParser()
    query = """
    GraphStructure {
        (s:User)-[e:knows]->(o:User)
    }
    Rule {}
    Action {
        get(s.name, o.name)
    }
    """

    block = parser.parse(query)

    # Execute
    executor = QueryExecutor(graph_adapter)
    results = executor.execute_query(block)

    # Verify
    assert len(results) == 1
    assert results[0]["s.name"] == "Alice"
    assert results[0]["o.name"] == "Bob"
```

---

## Summary

This guide provides a complete roadmap for reimplementing OpenSPG in Python with Memgraph:

1. **ANTLR4 Parser** - Reuse OpenSPG's grammar, generate Python parser
2. **Pydantic Models** - Type-safe schema definitions replacing Java classes
3. **Memgraph Adapter** - Cypher-based graph operations (Neo4j compatible)
4. **Block IR** - Logical plan representation matching Scala's design
5. **Reasoner Engine** - Compile KGDSL to Cypher, execute on Memgraph
6. **Builder Pipeline** - ETL framework with operator pattern
7. **FastAPI** - Modern async REST API
8. **Docker Compose** - Complete stack deployment

**Next Steps:**
1. Generate ANTLR parsers from grammar
2. Implement core Block IR classes
3. Build Memgraph adapter with Cypher compiler
4. Create schema service with persistence
5. Implement basic operators
6. Add FastAPI endpoints
7. Write integration tests

**Key Differences from OpenSPG:**
- Python vs Java/Scala (simpler, more accessible)
- Memgraph vs TuGraph/Neo4j (faster, real-time streaming)
- Pydantic vs Java POJO (runtime validation)
- FastAPI vs Spring Boot (modern async)
- No KAG (handled separately)

The architecture maintains OpenSPG's core design while leveraging Python's ecosystem advantages.
