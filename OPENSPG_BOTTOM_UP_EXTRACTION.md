# OpenSPG Bottom-Up System Extraction
## Complete Specification for Reimplementation

**Version:** 0.8
**Date:** 2025-11-05
**Purpose:** Comprehensive extraction of OpenSPG's core components, DSL specifications, architectural patterns, and functional elements for reimplementation in other languages/systems.

---

## Table of Contents

1. [Executive Summary](#executive-summary)
2. [KGDSL - Knowledge Graph Domain Specific Language](#kgdsl)
3. [SPG-Schema - Semantic Type System](#spg-schema)
4. [Builder Pipeline - Knowledge Construction](#builder-pipeline)
5. [Reasoner Engine - Query Processing](#reasoner-engine)
6. [Resolver Flow - Query Execution](#resolver-flow)
7. [Data Models & Type System](#data-models)
8. [LLM Integration Patterns](#llm-integration)
9. [Architecture Patterns](#architecture-patterns)
10. [Implementation Checklist](#implementation-checklist)

---

## Executive Summary

OpenSPG is an industrial-grade knowledge graph engine that combines:
- **LPG (Labeled Property Graph)** structural simplicity
- **RDF/OWL** semantic richness
- **Big Data** compatibility (Hadoop, Spark, Hive)
- **AI/ML** integration (LLM, Graph Learning)

### Core Value Proposition
SPG bridges the gap between property graphs and ontology-driven knowledge representations, enabling:
1. **Semantic-enhanced schema** with concepts, predicates, and rules
2. **Programmable knowledge construction** via operators
3. **Logic rule reasoning** with KGDSL
4. **Pluggable infrastructure** (graph stores, search engines, caches)

---

## 1. KGDSL - Knowledge Graph Domain Specific Language

### 1.1 Language Overview

KGDSL is an ANTLR4-based DSL for:
- **Graph pattern matching** (similar to Cypher/GQL)
- **Logic rule definition** (constraint propagation)
- **Knowledge construction** (derived properties/relations)
- **Query execution** (data retrieval)

**Grammar File:** `/reasoner/kgdsl-parser/src/main/antlr4/com/antgroup/openspg/reasoner/KGDSL.g4`

### 1.2 Core Syntax Structures

#### 1.2.1 Three Execution Modes

```antlr
script: (
    base_rule_define            // Compute mode
    | base_predicated_define    // Define mode
    | kgdsl_old_define          // KGDSL 1.0 compatibility
)*;
```

**Mode 1: Compute Mode (base_rule_define)**
```kgdsl
GraphStructure {
    path1: (s)-[p1:x]->(end:y)
}
Rule {
    R1('rule explanation'): path1
}
Action {
    get(s.name, end.id)
}
```

**Mode 2: Define Mode (base_predicated_define)**
```kgdsl
Define (s:label1)-[p:label2]->(o:concept/concept1) {
    GraphStructure {
        path1: (s)-[p1:x]->(end:y)
    }
    Rule {
        R1('xxx'): path1
    }
    Action {
        // Optional DDL operations
    }
}
```

**Mode 3: ISO GQL Compatibility**
```kgdsl
MATCH (s)-[]->(o)
WHERE s.id = 1
RETURN s.id, o.id
```

#### 1.2.2 Graph Pattern Syntax

**Node Patterns:**
```antlr
node_pattern: left_paren element_pattern_declaration_and_filler right_paren

element_pattern_declaration_and_filler:
    (element_variable_declaration)?     // Variable binding: (s:Type)
    element_lookup?                     // Type/label: :User, :Concept/instance
    (element_pattern_where_clause)?     // Inline filter: WHERE condition
```

**Examples:**
```kgdsl
// Entity type
(s:User)

// Concept type with instance
(o:`TaxonomyOfApp`/`GamblingApp`)

// With prefix namespace
(s:OpenSource.App)

// With WHERE clause
(s:User WHERE s.age > 18)

// Start node marker
(s:User where __start__='true')
```

**Edge Patterns:**
```antlr
full_edge_pointing_right:
    minus_sign left_bracket element_pattern_declaration_and_filler
    (edge_pattern_pernodelimit_clause)?
    right_bracket right_arrow

// Supports:
// -[e:type]->        directed
// <-[e:type]-        reverse
// -[e:type]-         bidirectional
// -[e:fn()]->        linked edge (function-based)
```

**Examples:**
```kgdsl
// Simple edge
(s)-[e:knows]->(o)

// Repeat/variable length path
(s)-[e:knows]-> (o) repeat(1,5)

// Per-node limit (top-K neighbors)
(s)-[e:follows per_node_limit 10]->(o)

// Linked edge (function-based connection)
(s:Park)-[e:nearby(s.boundary, o.center, 10)]->(o:Subway)
```

#### 1.2.3 Label Types

**Two types of labels:**

1. **Entity/Event Types:**
```kgdsl
User               // Simple type
OpenSource.App     // Namespaced type
```

2. **Concept Types (Taxonomy/Ontology):**
```kgdsl
TaxonomyOfApp/`GamblingApp`          // Single instance
TaxonomyOfApp/`App1`+TaxonomyOfApp/`App2`  // Multi-instance combination
```

**Format:**
```
<MetaConceptType>/<ConceptInstanceId>
```

#### 1.2.4 Rule Expressions

**Rule Types:**

1. **Logic Rules** (constraints):
```kgdsl
Rule {
    R1("explanation"): s.age > 18
    R2("must be male"): s.gender == 'M'
    R3("complex"): R1 && R2  // Rule composition
}
```

2. **Project Rules** (derived values):
```kgdsl
Rule {
    s.fullName = concat(s.firstName, s.lastName)
    o = rule_value(R1, 'VIP', 'Normal')  // Conditional value
}
```

3. **Aggregation Rules:**
```kgdsl
Rule {
    // Graph-based aggregation
    count = group(s).count(o)

    // List-based operations
    names = group(s).sum(o.amount)
    filtered = names.if(x > 100)
    sorted = names.desc().limit(10)
}
```

**Operators Available:**

**Comparison:** `==`, `!=`, `>`, `<`, `>=`, `<=`, `in`, `like`, `rlike`

**Logical:** `and`/`&&`, `or`/`||`, `not`/`!`, `xor`

**Arithmetic:** `+`, `-`, `*`, `/`, `%`

**Aggregation:** `sum`, `avg`, `count`, `min`, `max`, `sumif`, `avgif`, `countif`

**List Operations:**
- `filter`: `.if(condition)`
- `slice`: `.slice(start, end)`
- `limit`: `.limit(n)` or `.desc().limit(n)`
- `get`: `.get(index)`
- `reduce`: `.reduce((acc, x) => expression, init)`
- `nodes/edges`: `.nodes()`, `.edges()`
- `accumulate`: `.accumulate(+)` or `.accumulate(*)`

**Graph Aggregation:**
```kgdsl
group(A, B).count(C)            // Count C grouped by A, B
group(A).sum(B.amount)          // Sum amounts
group(A).if(condition).count(B) // Conditional aggregation
```

#### 1.2.5 Action Section

**Get Action (Data Retrieval):**
```kgdsl
Action {
    get(s.id, o.name as target_name)

    // With SQL post-processing
    get(s.id as sid, o.name)
    .sql(>>>
        SELECT sid, name
        FROM view
        WHERE sid > 100
    <<<)
}
```

**DDL Actions (Schema Evolution):**
```kgdsl
Action {
    // Create node
    node1 = createNodeInstance(
        type=ConceptType,
        value={
            propertyName=value,
            another="constant"
        }
    )

    // Create edge
    createEdgeInstance(
        src=node1,
        dst=existingNode,
        type=relationshipType,
        value={
            weight=0.8
        }
    )
}
```

### 1.3 Complete KGDSL Example

```kgdsl
// Define a derived predicate: high-value customer relationship
Define (s:User)-[p:isHighValueCustomer]->(o:Boolean) {
    GraphStructure {
        (s)<-[t:purchased]-(order:Order),
        (order)-[has:hasProduct]->(product:Product)
    }
    Rule {
        R1("Recent purchase"): date_diff(now(), t.purchaseDate) <= 30
        R2("Min amount"): t.amount > 1000

        totalAmount = group(s).sum(t.amount)
        productCount = group(s).count(product)

        R3("High value criteria"): totalAmount > 5000 && productCount > 5

        o = R3
    }
}

// Use the derived predicate
GraphStructure {
    (customer:User)-[p:isHighValueCustomer]->(result:Boolean)
}
Rule {
    R1: result == true
}
Action {
    get(customer.id, customer.name, customer.email)
}
```

### 1.4 KGDSL Parse Flow

```
Input DSL Text
    ↓
[LexerInit] → ANTLR4 Lexer/Parser
    ↓
[OpenSPGDslParser.parseKgDsl]
    ↓
Parse Tree (ANTLR Context Objects)
    ↓
[PatternParser] → Graph patterns → GraphPath, PatternElement
[RuleExprParser] → Rule expressions → Expr (AST)
    ↓
Block IR (Intermediate Representation)
    ├─ SourceBlock (graph topology)
    ├─ MatchBlock (pattern matching)
    ├─ FilterBlock (constraints)
    ├─ ProjectBlock (transformations)
    ├─ AggregationBlock (aggregations)
    ├─ OrderAndSliceBlock (sorting/limiting)
    ├─ TableResultBlock (output)
    └─ DDLBlock (schema changes)
    ↓
Logical Plan
    ↓
Physical Plan
    ↓
Execution
```

### 1.5 Expression AST

All rule expressions are parsed into an Expression AST:

```scala
// Base expression types
sealed trait Expr

// Values
case class Ref(refName: String) extends Expr
case class VString(value: String) extends Expr
case class VLong(value: String) extends Expr
case class VDouble(value: String) extends Expr
case class VBoolean(value: Boolean) extends Expr
case class VList(values: List[Expr]) extends Expr

// Operations
case class UnaryOpExpr(name: UnaryOp, arg: Expr) extends Expr
case class BinaryOpExpr(name: BinaryOp, left: Expr, right: Expr) extends Expr
case class FunctionExpr(name: String, args: List[Expr]) extends Expr

// Aggregation
case class AggOpExpr(name: AggOp, aggEleExpr: Expr) extends Expr
case class AggIfOpExpr(aggOpExpr: AggOpExpr, condition: Expr) extends Expr
case class GraphAggregatorExpr(pathName: String, by: List[Expr], op: Aggregator) extends Expr

// List operations
case class ListOpExpr(name: ListOp, expr: Expr) extends Expr
case class OpChainExpr(curExpr: Expr, preChainExpr: OpChainExpr) extends Expr
```

**Binary Operators:**
- `BEqual`, `BNotEqual`, `BGreaterThan`, `BLessThan`, `BNotSmallerThan`, `BNotBiggerThan`
- `BIn`, `BLike`, `BRLike`
- `BAnd`, `BOr`, `BXor`, `BNot`
- `BAdd`, `BSub`, `BMul`, `BDiv`, `BMod`

**Unary Operators:**
- `GetField(fieldName)` - Property access
- `Abs`, `Floor`, `Ceiling`
- `Exists`

---

## 2. SPG-Schema - Semantic Type System

### 2.1 Type Hierarchy

```
BaseSPGType (abstract)
├─ BasicType (Int, String, Boolean, Long, Float, Text)
├─ StandardType (Email, PhoneNumber, URL, etc.)
├─ EntityType (User, Company, Product)
├─ ConceptType (TaxonomyOfBrand, TaxonomyOfIndustry)
├─ EventType (Transaction, Login, Accident)
└─ IndexType (SummaryIndex, Chunk2QueryIndex)
```

### 2.2 Core Type Definitions

**SPGTypeEnum:**
```java
public enum SPGTypeEnum {
    BASIC_TYPE,      // Primitives
    ENTITY_TYPE,     // Domain entities
    INDEX_TYPE,      // KAG indices
    CONCEPT_TYPE,    // Taxonomy/ontology
    EVENT_TYPE,      // Temporal events
    STANDARD_TYPE    // Reusable standards
}
```

**BaseSPGType Structure:**
```java
public abstract class BaseSPGType {
    BasicInfo<SPGTypeIdentifier> basicInfo;  // ID, name, description
    ParentTypeInfo parentTypeInfo;            // Inheritance
    SPGTypeEnum spgTypeEnum;                  // Type category
    List<Property> properties;                // Attributes
    List<Relation> relations;                 // Relationships
    SPGTypeAdvancedConfig advancedConfig;     // Operators, visibility
}
```

### 2.3 Property & Relation Models

**Property (Attribute):**
```java
public class Property {
    PredicateIdentifier identifier;      // Unique ID
    SPGTypeRef objectTypeRef;            // Target type
    Constraint constraint;               // Validation rules
    PropertyAdvancedConfig advancedConfig; // Indexing, mounting
}
```

**Relation (Edge):**
```java
public class Relation {
    RelationIdentifier identifier;       // Unique ID
    SPGTypeRef subjectTypeRef;           // Source type
    SPGTypeRef objectTypeRef;            // Target type
    Map<String, Property> properties;    // Edge properties
    Direction direction;                 // OUT, IN, BOTH
}
```

### 2.4 Concept Modeling

**ConceptType:**
```java
public class ConceptType extends BaseAdvancedType {
    ConceptTaxonomicConfig taxonomicConfig;  // Hierarchy config
    ConceptLayerConfig layerConfig;          // Layer semantics
}
```

**Concept Instance:**
- Represents values in a taxonomy/ontology
- Can have parent-child relationships
- Supports multi-inheritance
- Examples: `Industry/Technology`, `Brand/Nike`

**Concept Mounting:**
Properties can "mount" concepts for semantic standardization:
```java
Property property = ...;
property.setMountedConceptConfig(
    new MountedConceptConfig(conceptType, dynamic=true)
);
```

### 2.5 Constraints

```java
public enum ConstraintTypeEnum {
    NOT_NULL,    // Required field
    UNIQUE,      // Unique values
    REGULAR,     // Regex pattern
    ENUM,        // Allowed values
    RANGE,       // Min/max bounds
    MULTI_VAL    // Multi-valued property
}
```

Example:
```java
RangeConstraint ageConstraint = new RangeConstraint(18, 120);
EnumConstraint genderConstraint = new EnumConstraint(List.of("M", "F", "Other"));
```

### 2.6 Semantic Predicates

**SystemPredicateEnum** (Built-in relations):
```java
public enum SystemPredicateEnum {
    BELONG_TO,           // Concept hierarchy
    IS_A,                // Type inheritance
    HAS_PROPERTY,        // Property attachment
    RELATED_TO,          // Generic relation
    HYPER_NYM,           // Parent concept
    HYPO_NYM,            // Child concept
    SAME_AS              // Equivalence
}
```

---

## 3. Builder Pipeline - Knowledge Construction

### 3.1 Pipeline Architecture

```
Raw Data Sources
    ↓
[Extract] → Structured Records
    ↓
[Mapping] → SPG-compliant records
    ↓
[Operator Chain]
    ├─ Predicting (property extraction)
    ├─ Linking (entity resolution)
    ├─ Fusing (entity merging)
    └─ Normalization
    ↓
[Writer] → Graph Store + Search Index
```

### 3.2 Operator Framework

**Base Operator Interface:**
```java
public interface Operator<IN, OUT> {
    OUT invoke(IN input);
}
```

**Operator Types:**

1. **PredictingOperator** - Extract/predict properties
2. **LinkingOperator** - Entity linking/resolution
3. **FusingOperator** - Entity fusion/merging
4. **NormalizationOperator** - Value standardization

### 3.3 Python Operator Integration

OpenSPG supports Python operators via **Pemja** (Python-Java bridge):

**PythonOperatorFactory:**
```java
public class PythonOperatorFactory {
    PythonInterpreter interpreter;

    public Operator createOperator(String pythonModule, String className) {
        // Load Python class
        // Bridge Java records to Python dicts
        // Execute Python operator
        // Convert results back to Java
    }
}
```

**Python Operator Example:**
```python
class EntityLinkingOperator:
    def invoke(self, record):
        # Extract entity mentions
        # Search existing entities
        # Compute similarity
        # Return linked entity ID
        return {"entityId": "E123", "confidence": 0.95}
```

### 3.4 Entity Linking Strategy

**SearchBasedLinking:**
1. Extract entity surface forms from text
2. Generate search queries
3. Query search engine (Elasticsearch/Neo4j)
4. Rank candidates by similarity
5. Return top-K matches

**OperatorLinking:**
1. Invoke custom Python/Java operator
2. Operator implements domain-specific linking logic
3. May use embeddings, rules, or ML models

### 3.5 Builder Configuration

**Pipeline Config:**
```json
{
  "source": {
    "type": "csv",
    "path": "/data/users.csv"
  },
  "mapping": {
    "User.id": "$.userId",
    "User.name": "$.userName",
    "User.age": "$.userAge"
  },
  "operators": [
    {
      "type": "predicting",
      "target": "User.sentiment",
      "impl": "python:SentimentAnalyzer"
    },
    {
      "type": "linking",
      "target": "User.company",
      "impl": "search"
    }
  ]
}
```

### 3.6 OpenIE Integration

While not explicitly labeled "OpenIE" in the codebase, the pattern extraction follows OpenIE principles:

1. **Relation Extraction from Text:**
   - Use NLP pipelines (dependency parsing)
   - Extract (subject, predicate, object) triples
   - Map to SPG schema

2. **Operator Pattern:**
```python
class RelationExtractor:
    def invoke(self, text):
        # Parse text
        doc = nlp(text)
        triples = []
        for sent in doc.sents:
            # Extract SPO triples
            triples.extend(extract_relations(sent))
        return triples
```

3. **Integration with Builder:**
   - Predicting operators extract relations
   - Linking operators resolve entities
   - Fusing operators merge duplicates

---

## 4. Reasoner Engine - Query Processing

### 4.1 Execution Model

```
KGDSL Query
    ↓
[Parser] → Block IR
    ↓
[Optimizer] → Optimized Logical Plan
    ↓
[Planner] → Physical Plan
    ↓
[Executor] → Result
```

### 4.2 Block IR (Intermediate Representation)

**Block Types:**

```scala
sealed trait Block {
    def dependencies: List[Block]
    def binds: BindingInfo  // Variables available
}

case class SourceBlock(graph: IRGraph) extends Block
case class MatchBlock(patterns: Map[String, GraphPath]) extends Block
case class FilterBlock(rules: Rule) extends Block
case class ProjectBlock(projects: ProjectFields) extends Block
case class AggregationBlock(aggregations: Aggregations, group: List[IRField]) extends Block
case class OrderAndSliceBlock(order: Seq[SortItem], limit: Option[Long], groupBy: List[String]) extends Block
case class TableResultBlock(selectList: OrderedFields, asList: List[String], distinct: Boolean) extends Block
case class DDLBlock(ddlOp: Set[DDLOp]) extends Block
```

**IRGraph (Internal Representation):**
```scala
case class KG(
    nodes: Map[String, IRNode],
    edges: Map[String, IREdge]
) extends IRGraph

case class IRNode(name: String, fields: Set[String]) extends IRField
case class IREdge(name: String, fields: Set[String]) extends IRField
case class IRProperty(name: String, field: String) extends IRField
case class IRVariable(name: String) extends IRField
case class IRPath(name: String, elements: List[IRField]) extends IRField
```

### 4.3 Pattern Matching

**GraphPattern:**
```scala
case class GraphPattern(
    rootAlias: String,                    // Start node
    nodes: Map[String, EntityElement],    // Node patterns
    edges: Map[String, Set[Connection]],  // Edge patterns
    properties: Map[String, Set[String]]  // Required properties
)
```

**PatternElement Types:**
```scala
sealed trait Element
case class EntityElement(
    id: String,
    typeNames: Set[String],
    alias: String,
    rule: Expr
) extends Element

case class ConceptElement(
    conceptType: String,
    conceptName: String,
    alias: String
) extends Element

case class PredicateElement(
    label: String,
    alias: String,
    source: Element,
    target: Element,
    fields: Map[String, Expr],
    direction: Direction
) extends Element
```

### 4.4 Rule Processing

**Rule Types:**
```scala
sealed trait Rule {
    def getName: String
    def getExpr: Expr
    def getOutput: IRField
}

case class LogicRule(name: String, desc: String, expr: Expr) extends Rule
case class ProjectRule(output: IRField, expr: Expr) extends Rule
```

**Rule Evaluation:**
1. Parse rule expression to AST
2. Resolve variable references
3. Apply transformations
4. Evaluate conditions
5. Compute derived values

### 4.5 Query Optimization

**Optimization Strategies:**

1. **Filter Pushdown:** Move filters closer to data source
2. **Projection Pruning:** Only fetch required properties
3. **Join Reordering:** Optimize multi-pattern joins
4. **Aggregation Merging:** Combine multiple aggregations
5. **Index Selection:** Choose appropriate indices

### 4.6 Physical Execution

**Execution Backends:**

1. **Local Runner:** In-memory execution (testing/small graphs)
2. **Cloud Warehouse:** Hadoop/Hive/Spark execution (big data)
3. **Graph Store Native:** TuGraph/Neo4j native queries

**Execution Flow:**
```
Physical Plan
    ↓
[Graph Scan] → Read from graph store
    ↓
[Filter] → Apply constraints
    ↓
[Expand] → Traverse edges
    ↓
[Join] → Combine patterns
    ↓
[Aggregate] → Compute aggregations
    ↓
[Project] → Select output fields
    ↓
[Return] → Result set
```

---

## 5. Resolver Flow - Query Execution

### 5.1 End-to-End Query Flow

```
User Query (KGDSL)
    ↓
[OpenSPGDslParser]
    ├─ Lexical Analysis (ANTLR4)
    ├─ Syntax Analysis
    ├─ Pattern Parsing (PatternParser)
    └─ Expression Parsing (RuleExprParser)
    ↓
Block IR
    ↓
[Catalog Lookup]
    ├─ Resolve type names
    ├─ Load schema metadata
    └─ Validate patterns
    ↓
Logical Plan
    ↓
[Optimizer]
    ├─ Cost-based optimization
    ├─ Rule-based rewriting
    └─ Index selection
    ↓
Physical Plan
    ↓
[Executor]
    ├─ Graph store queries
    ├─ Rule evaluation
    ├─ Aggregation computation
    └─ Result assembly
    ↓
Result Set (Table/Graph)
```

### 5.2 Pattern Resolution

**GraphPath Resolution:**
1. Identify root node (start node or arbitrary)
2. Expand patterns breadth-first
3. Apply filters at each level
4. Enforce cardinality constraints
5. Materialize paths

**Connection Types:**
```scala
sealed trait PatternConnection
case class VariablePatternConnection(
    alias: String,
    source: String,
    target: String,
    relTypes: Set[String],
    direction: Direction,
    rule: Expr,
    limit: Int,
    repeat: Option[(Int, Int)]
) extends PatternConnection

case class LinkedPatternConnection(
    alias: String,
    source: String,
    target: String,
    funcName: String,
    params: List[Expr],
    limit: Int
) extends PatternConnection
```

### 5.3 Rule Dependency Resolution

**Dependency Graph:**
```scala
def getRefRules(rule: Rule, ruleSet: List[Rule]): List[Rule] = {
    // 1. Extract variable references from rule expression
    val refs = getAllRefVariables(rule.getExpr)

    // 2. Find rules that produce those variables
    val dependencies = refs.filter(ruleMap.contains)

    // 3. Return dependency list
    dependencies.map(ruleMap)
}
```

**Execution Order:**
1. Build rule dependency DAG
2. Topological sort
3. Execute in dependency order
4. Materialize intermediate results

### 5.4 Aggregation Resolution

**Graph Aggregation:**
```kgdsl
group(A, B).count(C)
```

Resolves to:
```scala
AggregationBlock(
    aggregations = Map(result -> CountAgg(C)),
    group = List(IRNode("A"), IRNode("B"))
)
```

**Execution:**
1. Group records by (A, B)
2. For each group, count distinct C values
3. Return grouped results

### 5.5 DDL Resolution

**Define Statement:**
```kgdsl
Define (s:User)-[p:knows]->(o:User) { ... }
```

Resolves to:
```scala
DDLBlock(
    ddlOp = Set(AddPredicate(
        PredicateElement(
            label = "knows",
            source = EntityElement("User"),
            target = EntityElement("User"),
            direction = OUT
        )
    ))
)
```

**Execution:**
1. Validate schema change
2. Update schema repository
3. Propagate to graph store
4. Update search indices

---

## 6. Data Models & Type System

### 6.1 SPG Type Model

```
Thing (root type)
├─ Entity
│  ├─ User
│  ├─ Company
│  └─ Product
├─ Concept
│  ├─ TaxonomyOfIndustry
│  └─ TaxonomyOfBrand
└─ Event
   ├─ Transaction
   └─ LoginEvent
```

### 6.2 Identifier System

**SPGTypeIdentifier:**
```java
public class SPGTypeIdentifier {
    String namespace;  // e.g., "OpenSource"
    String name;       // e.g., "App"

    public String toString() {
        return namespace != null ? namespace + "." + name : name;
    }
}
```

**ConceptIdentifier:**
```java
public class ConceptIdentifier {
    String conceptType;     // e.g., "TaxonomyOfApp"
    String conceptInstance; // e.g., "GamblingApp"

    public String toString() {
        return conceptType + "/" + conceptInstance;
    }
}
```

### 6.3 Property Groups

```java
public enum PropertyGroupEnum {
    BASIC,      // Core properties
    STANDARD,   // Standardized properties
    EXTENDING   // Custom/extended properties
}
```

### 6.4 Advanced Configurations

**PropertyAdvancedConfig:**
```java
public class PropertyAdvancedConfig {
    IndexTypeEnum indexType;          // TEXT, KEYWORD, NUMERIC
    MountedConceptConfig conceptMount; // Concept standardization
    List<SubProperty> subProperties;   // Nested properties
}
```

**SPGTypeAdvancedConfig:**
```java
public class SPGTypeAdvancedConfig {
    VisibleScopeEnum visibleScope;     // PUBLIC, PRIVATE, PROJECT
    Map<OperatorKey, Operator> operators; // Bound operators
    MultiVersionConfig multiVersion;    // Version management
}
```

### 6.5 Storage Model

**Graph Store (LPG):**
- Vertices: Entity/Concept/Event instances
- Edges: Relation instances
- Properties: Attached to vertices/edges

**Search Index:**
- Documents: Flattened entity representations
- Fields: Properties + metadata
- Indices: Full-text, keyword, numeric

**Relational (Metadata):**
- Schema definitions
- Project configurations
- Job history

---

## 7. LLM Integration Patterns

### 7.1 KAG (Knowledge Augmented Generation)

**Architecture:**
```
User Question
    ↓
[Query Understanding]
    ├─ Intent classification
    ├─ Entity extraction
    └─ Relation extraction
    ↓
[KGDSL Generation]
    ├─ Schema-aware prompt
    ├─ LLM generates KGDSL
    └─ Validation & correction
    ↓
[Knowledge Retrieval]
    ├─ Execute KGDSL query
    ├─ Fetch graph context
    └─ Rank results
    ↓
[Answer Generation]
    ├─ Context + Question → LLM
    ├─ Generate answer
    └─ Cite sources
    ↓
Final Answer
```

### 7.2 KG2Prompt Pattern

**Convert KG to LLM Context:**
```python
def kg_to_prompt(graph_result):
    """Convert graph query results to LLM prompt context"""
    context = []

    for node in graph_result.nodes:
        context.append(f"Entity: {node.type}({node.id})")
        for prop, value in node.properties.items():
            context.append(f"  - {prop}: {value}")

    for edge in graph_result.edges:
        context.append(
            f"Relation: {edge.source} -[{edge.type}]-> {edge.target}"
        )

    return "\n".join(context)
```

### 7.3 Prompt Engineering

**Schema-Aware KGDSL Generation:**
```
System: You are a knowledge graph query expert.

Schema:
- Entity: User (properties: id, name, age, email)
- Entity: Product (properties: id, name, price, category)
- Relation: purchased (User -> Product, properties: date, quantity)

User Question: "Find users who purchased electronics in the last 30 days"

Generate KGDSL query:
```

**LLM Output:**
```kgdsl
GraphStructure {
    (u:User)<-[p:purchased]-(prod:Product)
}
Rule {
    R1: prod.category == 'Electronics'
    R2: date_diff(now(), p.date) <= 30
}
Action {
    get(u.id, u.name, u.email)
}
```

### 7.4 Operator Integration

**LLMExtractorOperator:**
```python
class LLMExtractorOperator:
    def __init__(self, llm_endpoint, schema):
        self.llm = LLMClient(llm_endpoint)
        self.schema = schema

    def invoke(self, text):
        """Extract structured data from unstructured text"""
        prompt = f"""
        Extract entities and relations from the text according to schema:
        {self.schema}

        Text: {text}

        Output JSON:
        """

        result = self.llm.generate(prompt)
        return parse_json(result)
```

---

## 8. Architecture Patterns

### 8.1 Layered Architecture

```
┌─────────────────────────────────────┐
│   Application Layer (Python SDK)    │
│   - Builder pipelines                │
│   - Reasoner queries                 │
│   - Schema management                │
└─────────────────────────────────────┘
           ↓ API/SDK
┌─────────────────────────────────────┐
│   Server Layer (Java/Spring)        │
│   - API Gateway (HTTP/RPC)           │
│   - Schema Service                   │
│   - Job Scheduler                    │
└─────────────────────────────────────┘
           ↓ Service Calls
┌─────────────────────────────────────┐
│   Core Layer (Java/Scala)           │
│   - Builder Engine                   │
│   - Reasoner Engine                  │
│   - KGDSL Parser                     │
└─────────────────────────────────────┘
           ↓ Storage APIs
┌─────────────────────────────────────┐
│   CloudExt Layer (Adapters)         │
│   - Graph Store Interface            │
│   - Search Engine Interface          │
│   - Cache Interface                  │
│   - Object Storage Interface         │
└─────────────────────────────────────┘
           ↓ Implementations
┌─────────────────────────────────────┐
│   Infrastructure (Pluggable)         │
│   - TuGraph / Neo4j                  │
│   - Elasticsearch / Neo4j Search     │
│   - Redis                            │
│   - MinIO / OSS                      │
└─────────────────────────────────────┘
```

### 8.2 Component Communication

**Schema Service:**
- Manages SPG type definitions
- Validates schema changes
- Propagates updates to storage

**Builder Service:**
- Orchestrates data pipelines
- Manages operators
- Tracks job execution

**Reasoner Service:**
- Parses KGDSL queries
- Optimizes execution plans
- Coordinates with graph store

**Job Scheduler:**
- Manages async tasks
- Handles retries
- Tracks progress

### 8.3 Extension Points

**Custom Operators:**
```java
@Component
public class MyCustomOperator implements Operator<Record, Record> {
    @Override
    public Record invoke(Record input) {
        // Custom logic
        return transformed;
    }
}
```

**Custom Graph Store:**
```java
public class MyGraphStore implements GraphStore {
    @Override
    public void upsertVertex(Vertex vertex) { ... }

    @Override
    public List<Vertex> queryVertices(Query query) { ... }

    @Override
    public void upsertEdge(Edge edge) { ... }
}
```

**Custom UDF (User-Defined Function):**
```scala
class MyUDF extends UdfMeta {
    override def invoke(params: List[Any]): Any = {
        // Custom function logic
    }
}
```

### 8.4 Data Flow Patterns

**Builder Pipeline:**
```
Source → Extract → Map → [Operators] → Validate → Write → Index
```

**Query Execution:**
```
Parse → Validate → Optimize → Plan → Execute → Materialize → Return
```

**Schema Evolution:**
```
Define → Validate → Persist → Propagate → Index → Notify
```

---

## 9. Implementation Checklist

### 9.1 Core Components

- [ ] **KGDSL Parser**
  - [ ] ANTLR4 grammar implementation
  - [ ] AST construction
  - [ ] Block IR generation
  - [ ] Error handling & validation

- [ ] **Type System**
  - [ ] BaseSPGType hierarchy
  - [ ] Property & Relation models
  - [ ] Concept taxonomy support
  - [ ] Constraint validation

- [ ] **Builder Engine**
  - [ ] Operator framework
  - [ ] Pipeline orchestration
  - [ ] Python operator bridge
  - [ ] Entity linking/fusing

- [ ] **Reasoner Engine**
  - [ ] Pattern matcher
  - [ ] Rule evaluator
  - [ ] Aggregation engine
  - [ ] Query optimizer

### 9.2 Storage Adapters

- [ ] **Graph Store Interface**
  - [ ] Vertex CRUD operations
  - [ ] Edge CRUD operations
  - [ ] Graph traversal APIs
  - [ ] Batch operations

- [ ] **Search Engine Interface**
  - [ ] Document indexing
  - [ ] Full-text search
  - [ ] Faceted search
  - [ ] Aggregations

- [ ] **Cache Interface**
  - [ ] Key-value operations
  - [ ] TTL support
  - [ ] Distributed caching

### 9.3 API Layer

- [ ] **HTTP API**
  - [ ] Schema management endpoints
  - [ ] Query execution endpoints
  - [ ] Job management endpoints
  - [ ] Authentication & authorization

- [ ] **SDK**
  - [ ] Python client library
  - [ ] Java client library
  - [ ] Query builder utilities

### 9.4 Integration Components

- [ ] **LLM Integration**
  - [ ] KG2Prompt conversion
  - [ ] KGDSL generation from NL
  - [ ] Answer generation with citations

- [ ] **ML Pipeline**
  - [ ] Embedding generation
  - [ ] Graph neural networks
  - [ ] Link prediction

### 9.5 Operational Features

- [ ] **Monitoring**
  - [ ] Query performance metrics
  - [ ] Storage utilization
  - [ ] Error tracking

- [ ] **Administration**
  - [ ] Schema versioning
  - [ ] Backup & restore
  - [ ] Multi-tenancy

---

## 10. Key Implementation Insights

### 10.1 Critical Design Decisions

1. **Hybrid LPG+RDF Model:**
   - Use property graph for storage efficiency
   - Add semantic layer (concepts, predicates) on top
   - Bridge using type system & reasoning rules

2. **Pluggable Infrastructure:**
   - Define abstract interfaces (graph store, search, cache)
   - Implement adapters for popular backends
   - Support custom implementations

3. **Programmable Operators:**
   - Separate logic from execution
   - Support Python for flexibility
   - Provide framework for custom operators

4. **Rule-Based Reasoning:**
   - Declarative KGDSL language
   - Compile to execution plans
   - Optimize using rule-based & cost-based techniques

### 10.2 Performance Considerations

1. **Query Optimization:**
   - Index selection critical for performance
   - Filter pushdown reduces data movement
   - Aggregation batching improves throughput

2. **Storage Layout:**
   - Vertex-centric partitioning for graph traversal
   - Property indexing for attribute filtering
   - Edge list optimization for high-degree vertices

3. **Caching Strategy:**
   - Schema metadata in-memory
   - Hot path results cached
   - Invalidation on schema changes

### 10.3 Common Pitfalls

1. **Over-normalization:** Balance semantic richness with query complexity
2. **Circular Dependencies:** Carefully design rule dependency graphs
3. **Type Explosion:** Limit concept hierarchy depth
4. **Operator Overhead:** Batch operations where possible

---

## Appendix A: KGDSL Grammar Reference

See complete grammar: `/reasoner/kgdsl-parser/src/main/antlr4/com/antgroup/openspg/reasoner/KGDSL.g4`

Key production rules:
- `script` - Top-level entry point
- `base_rule_define` - Compute mode
- `base_predicated_define` - Define mode
- `graph_structure` - Pattern definition
- `the_rule` - Rule section
- `the_action` - Action section
- `gql_query_statement` - ISO GQL support

---

## Appendix B: Block IR Reference

Core block types:
- `SourceBlock` - Data source
- `MatchBlock` - Pattern matching
- `FilterBlock` - Filtering
- `ProjectBlock` - Projection/transformation
- `AggregationBlock` - Aggregation
- `OrderAndSliceBlock` - Sorting/limiting
- `TableResultBlock` - Output
- `DDLBlock` - Schema modification

---

## Appendix C: Operator Taxonomy

**Builder Operators:**
- **Extracting:** Parse raw data
- **Mapping:** Map to schema
- **Predicting:** ML-based property prediction
- **Linking:** Entity resolution
- **Fusing:** Entity merging
- **Normalizing:** Value standardization

**Reasoner Operators:**
- **Scan:** Read from storage
- **Filter:** Apply conditions
- **Expand:** Traverse edges
- **Join:** Combine patterns
- **Aggregate:** Compute aggregations
- **Project:** Select fields
- **Sort:** Order results
- **Limit:** Paginate

---

## Appendix D: Python-Java Bridge

OpenSPG uses **Pemja** (https://github.com/alibaba/pemja) for Python integration:

```java
PythonInterpreter interpreter = new PythonInterpreter();
interpreter.exec("import my_module");
Object result = interpreter.invoke("my_module", "function_name", args);
```

Supports:
- Bidirectional data conversion
- Python module loading
- Exception propagation
- Multi-threading

---

## Conclusion

This extraction provides a complete specification for reimplementing OpenSPG's core functionality. Key takeaways:

1. **KGDSL** is the central DSL for graph queries and reasoning
2. **SPG Schema** provides semantic richness on top of property graphs
3. **Builder operators** enable flexible, programmable knowledge construction
4. **Reasoner engine** compiles KGDSL to optimized execution plans
5. **Pluggable architecture** supports multiple storage backends
6. **LLM integration** enables knowledge-augmented generation

For full implementation details, refer to the source code at:
- KGDSL Parser: `/reasoner/kgdsl-parser/`
- Schema Models: `/server/core/schema/model/`
- Builder: `/builder/core/`
- Reasoner: `/reasoner/`

**Version:** Based on OpenSPG v0.8 (commit: ceeb3ef)

---

*Document generated: 2025-11-05*
*For questions or clarifications, consult the OpenSPG documentation at: https://openspg.github.io/v2*
