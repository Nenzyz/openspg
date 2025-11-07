# OpenSPG Information Extraction Integration

**When and How OpenIE is Integrated into OpenSPG's Document Processing Pipeline**

**Version:** 1.0
**Date:** 2025-11-07
**Purpose:** Comprehensive guide to understanding when and how OpenIE and information extraction are integrated into OpenSPG's document loading and knowledge construction pipeline.

---

## Table of Contents

1. [Executive Summary](#executive-summary)
2. [When Extraction Happens](#when-extraction-happens)
3. [Extraction Processor Types](#extraction-processor-types)
4. [LLM-Based Extraction Flow](#llm-based-extraction-flow)
5. [Natural Language Extraction (Schema-Free)](#natural-language-extraction-schema-free)
6. [Python Operator Integration](#python-operator-integration)
7. [Complete Extraction Pipeline](#complete-extraction-pipeline)
8. [OpenIE Principles in OpenSPG](#openie-principles-in-openspg)
9. [Code Examples](#code-examples)
10. [Integration Points Summary](#integration-points-summary)

---

## Executive Summary

**OpenIE (Open Information Extraction) is NOT a single, explicitly named component in OpenSPG.** Instead, OpenIE principles and techniques are **integrated throughout the document processing pipeline** via multiple extraction processors that leverage LLMs, NLP tools, and custom operators to extract structured knowledge from unstructured text.

### Key Integration Points:

1. **LLMBasedExtractProcessor** - Uses LLMs for schema-aware entity and relation extraction
2. **LLMNlExtractProcessor** - Uses LLMs for schema-free natural language extraction (most flexible)
3. **UserDefinedExtractProcessor** - Custom extraction operators (can include OpenIE libraries)

### When It Happens:

Extraction occurs **during the Builder Pipeline execution**, specifically in the **processing layer** between source reading and graph storage:

```
Document Sources → [Read] → Document Records
                            ↓
[Chunking] → Document Chunks (ChunkRecords)
                            ↓
[EXTRACTION HAPPENS HERE] → SubGraphRecords (entities + relations)
                            ↓
[Mapping/Linking/Fusing] → SPGRecords
                            ↓
[Write] → Graph Store
```

---

## When Extraction Happens

### Timeline in Document Processing Pipeline

```
┌──────────────────────────────────────────────────────────────┐
│                     DOCUMENT LOADING PIPELINE                 │
└──────────────────────────────────────────────────────────────┘

1. SOURCE READING (No extraction yet)
   ├─ CsvFileSourceReader
   ├─ StringSourceReader
   └─ DatabaseSourceReader
   │
   └─→ Produces: BuilderRecords (raw data)

2. TYPE MAPPING (Simple field mapping, no IE)
   └─ SPGTypeMappingProcessor
      │
      └─→ Produces: EntityRecords (schema-compliant)

3. ⚡ CHUNKING (Prepares for extraction)
   └─ ParagraphSplitProcessor
      │
      └─→ Produces: ChunkRecords (text chunks)

4. ⭐ EXTRACTION (OpenIE INTEGRATION POINT) ⭐
   ├─ LLMBasedExtractProcessor      [Schema-aware LLM extraction]
   ├─ LLMNlExtractProcessor         [Schema-free NL extraction]
   └─ UserDefinedExtractProcessor   [Custom extraction]
      │
      └─→ Produces: SubGraphRecords (entities + relations extracted)

5. POST-EXTRACTION PROCESSING
   ├─ RelationMappingProcessor  [Create additional relations]
   ├─ EntityLinkingProcessor    [Resolve entity references]
   └─ EntityFusingProcessor     [Merge duplicate entities]
      │
      └─→ Produces: Linked SPGRecords

6. STORAGE
   └─ GraphStoreSinkWriter
      │
      └─→ Persists to: Graph Database
```

### Key Insight:

**Extraction happens AFTER chunking and BEFORE storage.** Documents are first split into manageable chunks, then extraction processors analyze each chunk to identify entities and relationships, producing SubGraphRecords that are subsequently processed and stored.

---

## Extraction Processor Types

OpenSPG provides **three main extraction processors**, each serving different use cases:

### 1. LLMBasedExtractProcessor

**File:** `builder/core/src/main/java/com/antgroup/openspg/builder/core/physical/process/LLMBasedExtractProcessor.java`

**Purpose:** Schema-aware extraction using LLMs with explicit instructions.

**When to use:**
- You have a well-defined SPG schema
- You want to extract specific entity types and relations
- You need guided extraction with instructions

**Input:** ChunkRecords (document chunks)
**Output:** SubGraphRecords (extracted entities and relations)

**Key Features:**
- Schema-aware prompting
- Custom extraction instructions
- Structured JSON output
- Parallel processing via thread pool

**Configuration Example:**
```json
{
  "id": "llm_extraction",
  "nodeType": "LLM_BASED_EXTRACT",
  "config": {
    "operatorConfig": {
      "module": "kag.builder.component.extractor.llm_extractor",
      "className": "LLMExtractor"
    },
    "extractionInstruction": "Extract all entities and relationships from the text"
  }
}
```

---

### 2. LLMNlExtractProcessor (Schema-Free)

**File:** `builder/core/src/main/java/com/antgroup/openspg/builder/core/physical/process/LLMNlExtractProcessor.java`

**Purpose:** Natural language extraction without predefined schema (OpenIE-style).

**When to use:**
- You don't have a fixed schema
- You want to discover entities and relations from text
- You need flexible, exploratory extraction
- **This is the closest to traditional OpenIE**

**Input:** ChunkRecords
**Output:** SubGraphRecords

**Key Features:**
- **Schema-free extraction** (`BuilderConstant.SCHEMA_FREE`)
- LLM-powered natural language understanding
- Dynamic entity and relation discovery
- Configurable LLM parameters

**Configuration Example:**
```json
{
  "id": "nl_extraction",
  "nodeType": "LLM_NL_EXTRACT",
  "config": {
    "operatorConfig": {
      "module": "kag.builder.component.extractor.nl_extractor",
      "className": "NLExtractor"
    }
  }
}
```

**How it works:**
1. Receives ChunkRecords with text content
2. Calls Python operator via `BuilderConstant.EXTRACTOR_ABC`
3. Passes LLM configuration and chunk content
4. Python operator prompts LLM to extract (subject, predicate, object) triples
5. Returns SubGraphRecords with discovered entities and relations

---

### 3. UserDefinedExtractProcessor

**File:** `builder/core/src/main/java/com/antgroup/openspg/builder/core/physical/process/UserDefinedExtractProcessor.java`

**Purpose:** Custom extraction using user-provided Python operators.

**When to use:**
- You have domain-specific extraction logic
- You want to integrate existing NLP/OpenIE libraries (Stanford OpenIE, AllenNLP, spaCy)
- You need fine-grained control over extraction

**Input:** BuilderRecords
**Output:** BuilderRecords or SubGraphRecords

**Key Features:**
- Fully customizable
- Can integrate any Python library
- Can use traditional OpenIE tools (Stanford OpenIE, OLLIE, ClausIE)
- Can implement custom NER, relation extraction, coreference resolution

**Configuration Example:**
```json
{
  "id": "custom_extraction",
  "nodeType": "USER_DEFINED_EXTRACT",
  "config": {
    "operatorConfig": {
      "module": "my_extractors",
      "className": "StanfordOpenIEExtractor"
    }
  }
}
```

---

## LLM-Based Extraction Flow

### Detailed Flow for LLMBasedExtractProcessor

```
┌─────────────────────────────────────────────────────────────┐
│  1. INPUT: ChunkRecords                                     │
│     Each chunk contains:                                     │
│     - Chunk ID                                               │
│     - Content (text)                                         │
│     - Metadata (document ID, page, section, etc.)           │
└─────────────────────────────────────────────────────────────┘
                      ↓
┌─────────────────────────────────────────────────────────────┐
│  2. PREPARE EXTRACTION PARAMETERS                           │
│     Map<String, Object> params = {                          │
│       "chunk": chunkRecord.getChunk().getContent(),         │
│       "schema": context.getCatalog().toSchemaPrompt(),      │
│       "instruction": config.getExtractionInstruction()      │
│     }                                                        │
└─────────────────────────────────────────────────────────────┘
                      ↓
┌─────────────────────────────────────────────────────────────┐
│  3. INVOKE PYTHON OPERATOR VIA PEMJA                        │
│     operatorFactory.invoke(                                 │
│       config.getOperatorConfig(),                           │
│       BuilderConstant.EXTRACTOR_ABC,                        │
│       params                                                 │
│     )                                                        │
└─────────────────────────────────────────────────────────────┘
                      ↓
┌─────────────────────────────────────────────────────────────┐
│  4. PYTHON OPERATOR (KAG Component)                         │
│     - Receives chunk text, schema, instruction              │
│     - Constructs LLM prompt                                 │
│     - Calls LLM API (OpenAI, Azure, etc.)                   │
│     - Parses LLM response (JSON)                            │
│     - Returns extracted entities and relations              │
└─────────────────────────────────────────────────────────────┘
                      ↓
┌─────────────────────────────────────────────────────────────┐
│  5. PARSE RESULT TO SubGraphRecords                         │
│     List<SubGraphRecord> subGraphs = JSON.parseObject(...)  │
│                                                              │
│     Each SubGraphRecord contains:                           │
│     - resultNodes: List<EntityRecord>                       │
│     - resultEdges: List<RelationRecord>                     │
└─────────────────────────────────────────────────────────────┘
                      ↓
┌─────────────────────────────────────────────────────────────┐
│  6. OUTPUT: SubGraphRecords                                 │
│     Ready for downstream processing (linking, fusing)       │
└─────────────────────────────────────────────────────────────┘
```

### Example LLM Prompt (Schema-Aware)

```
You are a knowledge extraction expert.

Schema:
- Entity Types: Person, Company, Product
- Relations:
  - Person.worksFor.Company
  - Company.produces.Product
  - Person.founded.Company

Instruction: Extract all entities and relationships from the text

Text:
"Elon Musk founded Tesla in 2003. Tesla produces electric vehicles
including the Model S, Model 3, Model X, and Model Y."

Extract entities and relationships in JSON format:
{
  "nodes": [
    {"type": "Person", "id": "elon_musk", "properties": {"name": "Elon Musk"}},
    {"type": "Company", "id": "tesla", "properties": {"name": "Tesla", "founded": "2003"}},
    {"type": "Product", "id": "model_s", "properties": {"name": "Model S"}},
    {"type": "Product", "id": "model_3", "properties": {"name": "Model 3"}},
    {"type": "Product", "id": "model_x", "properties": {"name": "Model X"}},
    {"type": "Product", "id": "model_y", "properties": {"name": "Model Y"}}
  ],
  "edges": [
    {"source": "elon_musk", "target": "tesla", "type": "founded"},
    {"source": "elon_musk", "target": "tesla", "type": "worksFor"},
    {"source": "tesla", "target": "model_s", "type": "produces"},
    {"source": "tesla", "target": "model_3", "type": "produces"},
    {"source": "tesla", "target": "model_x", "type": "produces"},
    {"source": "tesla", "target": "model_y", "type": "produces"}
  ]
}
```

---

## Natural Language Extraction (Schema-Free)

### Detailed Flow for LLMNlExtractProcessor

This is the **most OpenIE-like** approach in OpenSPG:

```java
// File: LLMNlExtractProcessor.java

@Override
public List<BaseRecord> process(List<BaseRecord> inputs) {
    node.setStatus(StatusEnum.RUNNING);
    node.addTraceLog("Start extract document chunk. chunk size:%s", inputs.size());

    List<BaseRecord> results = new ArrayList<>();
    List<Future<List<SubGraphRecord>>> futures = new ArrayList<>();

    // Process chunks in parallel
    for (BaseRecord record : inputs) {
        ChunkRecord chunkRecord = (ChunkRecord) record;

        // Submit to thread pool
        Future<List<SubGraphRecord>> future = executor.submit(
            new ExtractTaskCallable(node, chunkRecord, operatorFactory, config, project)
        );
        futures.add(future);
    }

    // Collect results
    for (Future<List<SubGraphRecord>> future : futures) {
        List<SubGraphRecord> result = future.get();
        results.addAll(result);
    }

    node.addTraceLog("extract document complete.");
    return results;
}

// Extraction task (runs in thread pool)
static class ExtractTaskCallable implements Callable<List<SubGraphRecord>> {
    @Override
    public List<SubGraphRecord> call() throws Exception {
        ChunkRecord.Chunk chunk = chunkRecord.getChunk();
        String projectConfig = project.getConfig();

        // Get LLM configuration from project
        JSONObject llm = JSONObject.parseObject(projectConfig).getJSONObject("llm");

        // Prepare config for SCHEMA-FREE extraction
        JSONObject pyConfig = new JSONObject();
        pyConfig.put(BuilderConstant.TYPE, BuilderConstant.SCHEMA_FREE);  // ⭐ KEY: Schema-free
        pyConfig.put(BuilderConstant.LLM, llm);

        // Convert chunk to map
        Map record = new ObjectMapper().convertValue(chunk, Map.class);

        // Invoke Python operator
        List<Object> result = (List<Object>) operatorFactory.invoke(
            config.getOperatorConfig(),
            BuilderConstant.EXTRACTOR_ABC,  // ⭐ Python operator identifier
            pyConfig.toJSONString(),
            record
        );

        // Parse to SubGraphRecords
        List<SubGraphRecord> records = JSON.parseObject(
            JSON.toJSONString(result),
            new TypeReference<List<SubGraphRecord>>() {}
        );

        return records;
    }
}
```

### Key Differences from Schema-Aware Extraction

| Aspect | Schema-Aware (LLMBasedExtract) | Schema-Free (LLMNlExtract) |
|--------|-------------------------------|---------------------------|
| **Schema Requirement** | Requires predefined SPG schema | No schema required |
| **Extraction Type** | Constrained to defined types | Open-ended discovery |
| **Configuration** | `BuilderConstant.SCHEMA_AWARE` | `BuilderConstant.SCHEMA_FREE` |
| **Prompt Style** | "Extract Person, Company..." | "Extract all entities and relations" |
| **Output Validation** | Validates against schema | Accepts any entity/relation type |
| **Use Case** | Structured data extraction | Exploratory knowledge discovery |
| **OpenIE Similarity** | Medium | **High** ⭐ |

### Example Schema-Free Prompt

```
You are a knowledge extraction expert.

Text:
"The Eiffel Tower, located in Paris, was designed by Gustave Eiffel
and completed in 1889. It stands 324 meters tall and is visited by
millions of tourists each year."

Extract ALL entities and relationships you can identify from the text.
Output in JSON format:
{
  "nodes": [
    {"type": "<discovered_type>", "id": "<unique_id>", "properties": {...}},
    ...
  ],
  "edges": [
    {"source": "<node_id>", "target": "<node_id>", "type": "<relation_type>"},
    ...
  ]
}
```

**LLM Response (Schema-Free Discovery):**
```json
{
  "nodes": [
    {"type": "Landmark", "id": "eiffel_tower", "properties": {"name": "Eiffel Tower", "height": "324 meters"}},
    {"type": "City", "id": "paris", "properties": {"name": "Paris"}},
    {"type": "Person", "id": "gustave_eiffel", "properties": {"name": "Gustave Eiffel", "profession": "Engineer"}},
    {"type": "Year", "id": "1889", "properties": {"value": 1889}},
    {"type": "Measurement", "id": "324m", "properties": {"value": 324, "unit": "meters"}}
  ],
  "edges": [
    {"source": "eiffel_tower", "target": "paris", "type": "locatedIn"},
    {"source": "eiffel_tower", "target": "gustave_eiffel", "type": "designedBy"},
    {"source": "eiffel_tower", "target": "1889", "type": "completedIn"},
    {"source": "eiffel_tower", "target": "324m", "type": "hasHeight"}
  ]
}
```

Notice how the entity types (`Landmark`, `Measurement`) and relation types (`locatedIn`, `designedBy`, `completedIn`, `hasHeight`) were **discovered by the LLM**, not predefined in a schema.

---

## Python Operator Integration

### How Java Calls Python for Extraction

OpenSPG uses **Pemja** (Python-Java bridge) to call Python operators:

```
┌───────────────────┐
│  Java Process     │
│  (OpenSPG Core)   │
│                   │
│  ┌─────────────┐  │
│  │ Processor   │  │
│  └──────┬──────┘  │
│         │         │
│         │ invoke()│
│         ↓         │
│  ┌─────────────┐  │
│  │ Operator    │  │
│  │ Factory     │  │
│  └──────┬──────┘  │
└─────────┼─────────┘
          │ Pemja Bridge
          ↓
┌─────────────────────┐
│  Python Interpreter │
│  (Embedded in JVM)  │
│                     │
│  ┌───────────────┐  │
│  │ KAG Module    │  │
│  │  - Extractor  │  │
│  │  - LLM Client │  │
│  │  - NLP Tools  │  │
│  └───────────────┘  │
└─────────────────────┘
```

### OperatorFactory.invoke() Implementation

```java
// File: builder/core/src/main/java/com/antgroup/openspg/builder/core/physical/operator/OperatorFactory.java

public Object invoke(
    OperatorConfig operatorConfig,
    String operatorIdentifier,  // e.g., BuilderConstant.EXTRACTOR_ABC
    Object... args
) {
    // Load Python module
    String module = operatorConfig.getModule();
    String className = operatorConfig.getClassName();

    // Get Python interpreter (Pemja)
    PythonInterpreter interpreter = PythonInterpreterManager.getInterpreter();

    // Import Python module
    interpreter.exec(String.format("import %s", module));

    // Invoke Python function
    Object result = interpreter.invoke(
        module,
        operatorIdentifier,  // Function name in Python
        args
    );

    return result;
}
```

### BuilderConstant.EXTRACTOR_ABC

**File:** `common/util/src/main/java/com/antgroup/openspg/common/constants/BuilderConstant.java`

```java
public class BuilderConstant {
    // ... other constants

    /**
     * Extractor ABC - Abstract base class/function identifier for extraction operators.
     * Python operators must implement this interface/function.
     */
    public static final String EXTRACTOR_ABC = "ExtractorABC";

    /**
     * Extraction types
     */
    public static final String SCHEMA_FREE = "schema_free";
    public static final String SCHEMA_AWARE = "schema_aware";

    /**
     * LLM configuration key
     */
    public static final String LLM = "llm";
    public static final String TYPE = "type";
}
```

### Python Operator Structure (Conceptual)

While the actual KAG Python code is not in the repository clone, the expected structure is:

```python
# kag/builder/component/extractor/base_extractor.py

class ExtractorABC:
    """Abstract base class for extraction operators."""

    def __init__(self, config: Dict):
        self.config = config
        self.llm_client = self._init_llm_client(config.get("llm"))

    def invoke(self, extraction_type: str, chunk: Dict) -> List[Dict]:
        """
        Main extraction method called from Java.

        Args:
            extraction_type: "schema_free" or "schema_aware"
            chunk: Document chunk with content and metadata

        Returns:
            List of SubGraphRecords (nodes + edges)
        """
        if extraction_type == "schema_free":
            return self._schema_free_extraction(chunk)
        elif extraction_type == "schema_aware":
            return self._schema_aware_extraction(chunk)
        else:
            raise ValueError(f"Unknown extraction type: {extraction_type}")

    def _schema_free_extraction(self, chunk: Dict) -> List[Dict]:
        """
        OpenIE-style extraction without predefined schema.

        This is where OpenIE happens!
        """
        content = chunk["content"]

        # Option 1: Use LLM for extraction
        prompt = self._build_openie_prompt(content)
        llm_response = self.llm_client.generate(prompt)
        extracted = self._parse_llm_response(llm_response)

        # Option 2: Use traditional OpenIE library (Stanford OpenIE, OLLIE, etc.)
        # from openie import StanfordOpenIE
        # with StanfordOpenIE() as client:
        #     triples = client.annotate(content)
        #     extracted = self._convert_triples_to_subgraph(triples)

        # Option 3: Use spaCy with custom relation extraction
        # doc = nlp(content)
        # extracted = self._extract_from_spacy(doc)

        return [
            {
                "nodes": extracted["entities"],
                "edges": extracted["relations"]
            }
        ]

    def _schema_aware_extraction(self, chunk: Dict) -> List[Dict]:
        """Schema-guided extraction."""
        content = chunk["content"]
        schema = chunk.get("schema", {})

        prompt = self._build_schema_aware_prompt(content, schema)
        llm_response = self.llm_client.generate(prompt)
        extracted = self._parse_llm_response(llm_response)

        return [
            {
                "nodes": extracted["entities"],
                "edges": extracted["relations"]
            }
        ]

    def _build_openie_prompt(self, content: str) -> str:
        """Build prompt for open information extraction."""
        return f"""
        You are an expert at extracting knowledge from text.

        Extract ALL entities and relationships from the following text.
        Do not limit yourself to predefined types - discover and extract
        any entities and relations you find.

        Text:
        {content}

        Output JSON format:
        {{
          "entities": [
            {{"id": "...", "type": "...", "name": "...", "properties": {{...}}}}
          ],
          "relations": [
            {{"source": "...", "target": "...", "type": "...", "properties": {{...}}}}
          ]
        }}
        """

    def _parse_llm_response(self, response: str) -> Dict:
        """Parse LLM JSON response."""
        import json
        try:
            return json.loads(response)
        except json.JSONDecodeError:
            # Handle malformed JSON
            return {"entities": [], "relations": []}
```

---

## Complete Extraction Pipeline

### End-to-End Flow with All Integration Points

```
┌──────────────────────────────────────────────────────────────────────┐
│                    COMPLETE DOCUMENT TO GRAPH FLOW                    │
│                  (Showing ALL extraction integration points)          │
└──────────────────────────────────────────────────────────────────────┘

INPUT: research_papers.csv
├─ paper_id, title, abstract, authors, year, journal

STAGE 1: SOURCE READING
├─ Processor: CsvFileSourceReader
├─ Output: BuilderRecords
│  └─ Example: {recordId: "line1", props: {paper_id: "P001", title: "...", ...}}

STAGE 2: TYPE MAPPING
├─ Processor: SPGTypeMappingProcessor
├─ Output: EntityRecords (Paper entities)
│  └─ Example: EntityRecord(type=Paper, id=P001, properties=[...])

STAGE 3: DOCUMENT CHUNKING
├─ Processor: ParagraphSplitProcessor
├─ Output: ChunkRecords
│  └─ Example: ChunkRecord(
│       parentId=P001,
│       chunk={
│         id: "P001_chunk_0",
│         content: "This paper presents a novel approach to...",
│         metadata: {section: "abstract"}
│       }
│     )

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
⭐ STAGE 4: KNOWLEDGE EXTRACTION (OPENIE INTEGRATION) ⭐
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

OPTION A: Schema-Free Extraction (OpenIE-style)
├─ Processor: LLMNlExtractProcessor
├─ Config: {type: "schema_free"}
├─ Python Operator: ExtractorABC (schema-free mode)
├─ Technique:
│  ├─ LLM-based open extraction
│  ├─ Traditional OpenIE libraries (Stanford, OLLIE, ClausIE)
│  └─ Custom NER + Relation Extraction
├─ Output: SubGraphRecords
│  └─ Example: SubGraphRecord(
│       resultNodes: [
│         EntityRecord(type=Technique, id=GNN, name="Graph Neural Networks"),
│         EntityRecord(type=Concept, id=attention, name="Attention Mechanism"),
│         EntityRecord(type=Application, id=node_class, name="Node Classification")
│       ],
│       resultEdges: [
│         RelationRecord(src=GNN, dst=attention, type="uses"),
│         RelationRecord(src=GNN, dst=node_class, type="appliesTo")
│       ]
│     )

OPTION B: Schema-Aware Extraction
├─ Processor: LLMBasedExtractProcessor
├─ Config: {schema: Paper schema, instruction: "Extract authors, methods, datasets"}
├─ Python Operator: ExtractorABC (schema-aware mode)
├─ Technique: Guided LLM extraction
├─ Output: SubGraphRecords
│  └─ Example: SubGraphRecord(
│       resultNodes: [
│         EntityRecord(type=Author, id=A001, name="Alice Smith"),
│         EntityRecord(type=Method, id=M001, name="Transformer Architecture"),
│         EntityRecord(type=Dataset, id=D001, name="COCO Dataset")
│       ],
│       resultEdges: [
│         RelationRecord(src=P001, dst=A001, type="hasAuthor"),
│         RelationRecord(src=P001, dst=M001, type="usesMethod"),
│         RelationRecord(src=P001, dst=D001, type="evaluatedOn")
│       ]
│     )

OPTION C: Custom Extraction
├─ Processor: UserDefinedExtractProcessor
├─ Config: {module: "my_extractors", className: "BioBERTNERExtractor"}
├─ Python Operator: Custom implementation
├─ Technique: Domain-specific models (BioBERT, SciBERT, etc.)
├─ Output: SubGraphRecords

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

STAGE 5: RELATION MAPPING
├─ Processor: RelationMappingProcessor
├─ Purpose: Create explicit relations based on extraction results
├─ Output: RelationRecords
│  └─ Example: RelationRecord(Paper, cites, Paper)

STAGE 6: ENTITY LINKING
├─ Processor: EntityLinkingProcessor
├─ Purpose: Resolve extracted entities to canonical entities in KG
├─ Technique:
│  ├─ Search-based linking (Elasticsearch/Neo4j)
│  ├─ Embedding-based similarity
│  └─ Custom linking operators
├─ Output: Linked EntityRecords
│  └─ Example: EntityRecord(id=A001) → Resolved to existing Author(id=author_alice_smith)

STAGE 7: ENTITY FUSING
├─ Processor: EntityFusingProcessor
├─ Purpose: Merge duplicate entities
├─ Technique:
│  ├─ Property-based matching
│  ├─ Embedding similarity
│  └─ Custom fusing rules
├─ Output: Fused EntityRecords

STAGE 8: GRAPH STORAGE
├─ Processor: GraphStoreSinkWriter
├─ Storage: TuGraph / Neo4j / Memgraph
├─ Index: Elasticsearch (full-text search)
└─ Output: Persisted Knowledge Graph

FINAL RESULT IN GRAPH:
(P001:Paper {title: "..."})-[:hasAuthor]->(A001:Author {name: "Alice Smith"})
(P001)-[:usesMethod]->(M001:Method {name: "Transformer"})
(P001)-[:evaluatedOn]->(D001:Dataset {name: "COCO"})
(M001)-[:uses]->(attention:Technique {name: "Attention Mechanism"})
(M001)-[:appliesTo]->(node_class:Application {name: "Node Classification"})
```

---

## OpenIE Principles in OpenSPG

### How OpenSPG Implements OpenIE Concepts

Traditional OpenIE systems extract (subject, predicate, object) triples from unstructured text. OpenSPG implements these principles through its extraction processors:

| OpenIE Concept | OpenSPG Implementation |
|----------------|------------------------|
| **Triple Extraction** | SubGraphRecords (nodes + edges) |
| **Open Vocabulary** | Schema-free extraction mode |
| **Entity Recognition** | LLM-based NER or custom NER operators |
| **Relation Detection** | LLM relation extraction or custom relation extractors |
| **Confidence Scoring** | LLM provides confidence, can be stored in edge properties |
| **N-ary Relations** | Edge properties can encode additional arguments |
| **Temporal Information** | Properties can capture temporal constraints |
| **Nested Relations** | SubGraphRecords support complex graph structures |

### Comparison with Traditional OpenIE Systems

| Aspect | Traditional OpenIE (Stanford, OLLIE) | OpenSPG Extraction |
|--------|--------------------------------------|-------------------|
| **Input** | Raw text | Document chunks (with metadata) |
| **Output** | (subject, predicate, object) triples | SubGraphRecords (full sub-graphs) |
| **Schema** | None (purely open) | Configurable (schema-free OR schema-aware) |
| **Technology** | Rule-based, dependency parsing | LLM-based + custom operators |
| **Customization** | Limited | Highly flexible (Python operators) |
| **Context** | Sentence-level | Document-level (with chunking) |
| **Integration** | Standalone tool | Integrated into full KG pipeline |
| **Post-processing** | External | Built-in linking, fusing, validation |
| **Storage** | None (output triples) | Direct graph storage |

### Example Comparison

**Input Text:**
```
"Steve Jobs co-founded Apple in 1976 along with Steve Wozniak."
```

**Traditional OpenIE Output (Stanford):**
```
(Steve Jobs; co-founded; Apple)
(Steve Jobs; co-founded; Apple; in 1976)
(Steve Jobs; co-founded; Apple; along with Steve Wozniak)
```

**OpenSPG Extraction Output:**
```json
{
  "nodes": [
    {"type": "Person", "id": "steve_jobs", "properties": {"name": "Steve Jobs"}},
    {"type": "Person", "id": "steve_wozniak", "properties": {"name": "Steve Wozniak"}},
    {"type": "Company", "id": "apple", "properties": {"name": "Apple", "founded": "1976"}}
  ],
  "edges": [
    {"source": "steve_jobs", "target": "apple", "type": "coFounded", "properties": {"year": "1976"}},
    {"source": "steve_wozniak", "target": "apple", "type": "coFounded", "properties": {"year": "1976"}},
    {"source": "steve_jobs", "target": "steve_wozniak", "type": "coFoundedWith", "properties": {"company": "apple"}}
  ]
}
```

**Key Differences:**
1. OpenSPG produces **typed entities** (Person, Company)
2. OpenSPG produces **typed relations** (coFounded, coFoundedWith)
3. OpenSPG captures **properties** on both nodes and edges
4. OpenSPG produces a **connected sub-graph**, not just triples
5. OpenSPG supports **follow-up linking** to resolve "Steve Jobs" → canonical entity

---

## Code Examples

### Example 1: Configuring Schema-Free Extraction Pipeline

```json
{
  "nodes": [
    {
      "id": "doc_reader",
      "nodeType": "STRING_SOURCE",
      "config": {
        "source": "documents.txt"
      }
    },
    {
      "id": "chunker",
      "nodeType": "PARAGRAPH_SPLIT",
      "config": {
        "chunkSize": 512,
        "overlap": 50
      }
    },
    {
      "id": "openie_extraction",
      "nodeType": "LLM_NL_EXTRACT",
      "config": {
        "operatorConfig": {
          "module": "kag.builder.component.extractor.nl_extractor",
          "className": "NLExtractor"
        },
        "llmConfig": {
          "provider": "openai",
          "model": "gpt-4",
          "temperature": 0.0
        }
      }
    },
    {
      "id": "entity_linking",
      "nodeType": "ENTITY_LINKING",
      "config": {
        "linkingStrategy": "search",
        "searchEngine": "elasticsearch",
        "topK": 5,
        "threshold": 0.8
      }
    },
    {
      "id": "graph_writer",
      "nodeType": "GRAPH_SINK",
      "config": {
        "graphStoreUrl": "bolt://localhost:7687"
      }
    }
  ],
  "edges": [
    {"from": "doc_reader", "to": "chunker"},
    {"from": "chunker", "to": "openie_extraction"},
    {"from": "openie_extraction", "to": "entity_linking"},
    {"from": "entity_linking", "to": "graph_writer"}
  ]
}
```

---

### Example 2: Custom OpenIE Operator (Python)

```python
# my_extractors/stanford_openie_extractor.py

from typing import Dict, List
import json

# Traditional OpenIE library
from openie import StanfordOpenIE


class StanfordOpenIEExtractor:
    """
    Custom extraction operator using Stanford OpenIE.

    This demonstrates how to integrate traditional OpenIE tools
    into OpenSPG's extraction pipeline.
    """

    def __init__(self, config: Dict):
        self.config = config
        self.openie_client = None

    def ExtractorABC(self, extraction_type: str, chunk: Dict) -> List[Dict]:
        """
        Main entry point called from Java via Pemja.

        Args:
            extraction_type: "schema_free" (OpenIE mode)
            chunk: Document chunk with content

        Returns:
            List of SubGraphRecords
        """
        content = chunk["content"]
        chunk_id = chunk["id"]

        # Use Stanford OpenIE for triple extraction
        with StanfordOpenIE() as client:
            triples = client.annotate(content)

        # Convert OpenIE triples to OpenSPG SubGraphRecords
        subgraph = self._convert_triples_to_subgraph(triples, chunk_id)

        return [subgraph]

    def _convert_triples_to_subgraph(self, triples: List[Dict], chunk_id: str) -> Dict:
        """
        Convert Stanford OpenIE triples to OpenSPG SubGraphRecord format.

        Stanford OpenIE triple format:
        {
          'subject': 'Steve Jobs',
          'relation': 'co-founded',
          'object': 'Apple',
          'confidence': 0.95
        }

        OpenSPG SubGraphRecord format:
        {
          'nodes': [{'type': '...', 'id': '...', 'properties': {...}}],
          'edges': [{'source': '...', 'target': '...', 'type': '...', 'properties': {...}}]
        }
        """
        nodes = {}  # id -> node
        edges = []

        for idx, triple in enumerate(triples):
            # Create subject entity
            subject_id = self._generate_entity_id(triple['subject'])
            if subject_id not in nodes:
                nodes[subject_id] = {
                    'type': 'Entity',  # Generic type (schema-free)
                    'id': subject_id,
                    'properties': {
                        'name': triple['subject'],
                        'source': 'openie',
                        'chunk_id': chunk_id
                    }
                }

            # Create object entity
            object_id = self._generate_entity_id(triple['object'])
            if object_id not in nodes:
                nodes[object_id] = {
                    'type': 'Entity',
                    'id': object_id,
                    'properties': {
                        'name': triple['object'],
                        'source': 'openie',
                        'chunk_id': chunk_id
                    }
                }

            # Create relation edge
            edges.append({
                'source': subject_id,
                'target': object_id,
                'type': self._normalize_relation(triple['relation']),
                'properties': {
                    'confidence': triple.get('confidence', 1.0),
                    'extraction_method': 'stanford_openie',
                    'chunk_id': chunk_id
                }
            })

        return {
            'nodes': list(nodes.values()),
            'edges': edges
        }

    def _generate_entity_id(self, entity_name: str) -> str:
        """Generate unique entity ID from entity name."""
        import hashlib
        normalized = entity_name.lower().strip().replace(' ', '_')
        hash_suffix = hashlib.md5(entity_name.encode()).hexdigest()[:8]
        return f"entity_{normalized}_{hash_suffix}"

    def _normalize_relation(self, relation: str) -> str:
        """Normalize relation name for consistency."""
        # Convert "co-founded" → "coFounded"
        # Convert "was born in" → "wasBornIn"
        words = relation.replace('-', ' ').split()
        if not words:
            return "relatedTo"
        return words[0].lower() + ''.join(w.capitalize() for w in words[1:])


# Java configuration to use this operator:
# {
#   "id": "openie_extraction",
#   "nodeType": "USER_DEFINED_EXTRACT",
#   "config": {
#     "operatorConfig": {
#       "module": "my_extractors.stanford_openie_extractor",
#       "className": "StanfordOpenIEExtractor"
#     }
#   }
# }
```

---

### Example 3: Hybrid Extraction (LLM + OpenIE)

```python
# my_extractors/hybrid_extractor.py

from typing import Dict, List
import json
from openai import OpenAI
from openie import StanfordOpenIE


class HybridExtractor:
    """
    Hybrid extractor combining LLM and traditional OpenIE.

    Strategy:
    1. Use Stanford OpenIE for initial triple extraction (fast, broad coverage)
    2. Use LLM for entity typing and property extraction (accurate, context-aware)
    3. Use LLM for relation refinement (normalize, add semantic info)
    """

    def __init__(self, config: Dict):
        self.config = config
        self.llm_client = OpenAI(api_key=config.get("openai_api_key"))

    def ExtractorABC(self, extraction_type: str, chunk: Dict) -> List[Dict]:
        """Extract knowledge using hybrid approach."""
        content = chunk["content"]
        chunk_id = chunk["id"]

        # Step 1: Extract triples with OpenIE (fast, broad)
        with StanfordOpenIE() as client:
            openie_triples = client.annotate(content)

        # Step 2: Refine with LLM (accurate, semantic)
        refined_subgraph = self._llm_refinement(content, openie_triples)

        return [refined_subgraph]

    def _llm_refinement(self, content: str, openie_triples: List[Dict]) -> Dict:
        """Use LLM to refine OpenIE extractions."""

        # Format OpenIE triples for LLM
        triples_str = "\n".join([
            f"- ({t['subject']}, {t['relation']}, {t['object']})"
            for t in openie_triples
        ])

        prompt = f"""
        Given the following text and initial entity-relation triples extracted by OpenIE,
        refine the extraction by:
        1. Assigning semantic types to entities (Person, Organization, Location, etc.)
        2. Extracting additional properties for entities
        3. Normalizing relation names to standard predicates
        4. Adding missing entities or relations

        Text:
        {content}

        Initial Triples:
        {triples_str}

        Output refined knowledge graph in JSON format:
        {{
          "nodes": [
            {{"type": "Person|Organization|Location|...", "id": "...", "properties": {{...}}}}
          ],
          "edges": [
            {{"source": "...", "target": "...", "type": "founded|locatedIn|...", "properties": {{...}}}}
          ]
        }}
        """

        response = self.llm_client.chat.completions.create(
            model="gpt-4",
            messages=[{"role": "user", "content": prompt}],
            temperature=0.0
        )

        try:
            refined = json.loads(response.choices[0].message.content)
            return refined
        except json.JSONDecodeError:
            # Fallback: use OpenIE triples as-is
            return self._convert_triples_to_subgraph(openie_triples)

    def _convert_triples_to_subgraph(self, triples: List[Dict]) -> Dict:
        """Fallback conversion without LLM refinement."""
        # ... (similar to StanfordOpenIEExtractor example)
        pass
```

---

### Example 4: Monitoring Extraction Progress

```java
// File: builder/core/src/main/java/com/antgroup/openspg/builder/core/physical/process/LLMNlExtractProcessor.java

@Override
public List<BaseRecord> process(List<BaseRecord> inputs) {
    // Start tracking
    node.setStatus(StatusEnum.RUNNING);
    node.addTraceLog("Start extract document chunk. chunk size:%s", inputs.size());

    long startTime = System.currentTimeMillis();
    List<BaseRecord> results = new ArrayList<>();
    List<Future<List<SubGraphRecord>>> futures = new ArrayList<>();

    // Submit extraction tasks
    for (int i = 0; i < inputs.size(); i++) {
        ChunkRecord chunkRecord = (ChunkRecord) inputs.get(i);

        // Log each chunk submission
        node.addTraceLog("Submitting chunk %d/%d: %s",
            i + 1, inputs.size(), chunkRecord.getChunk().getName());

        Future<List<SubGraphRecord>> future = executor.submit(
            new ExtractTaskCallable(node, chunkRecord, operatorFactory, config, project)
        );
        futures.add(future);
    }

    // Collect results with progress tracking
    int completed = 0;
    for (Future<List<SubGraphRecord>> future : futures) {
        try {
            List<SubGraphRecord> result = future.get();
            results.addAll(result);
            completed++;

            // Log progress
            node.addTraceLog("Completed chunk %d/%d", completed, futures.size());

            // Log extraction statistics
            int totalNodes = result.stream().mapToInt(sg -> sg.getResultNodes().size()).sum();
            int totalEdges = result.stream().mapToInt(sg -> sg.getResultEdges().size()).sum();
            node.addTraceLog("Extracted: %d nodes, %d edges", totalNodes, totalEdges);

        } catch (Exception e) {
            node.addTraceLog("ERROR: Failed to extract chunk %d: %s",
                completed + 1, e.getMessage());
            log.error("Extraction failed", e);
        }
    }

    // Final summary
    long duration = System.currentTimeMillis() - startTime;
    int totalNodes = results.stream()
        .filter(r -> r instanceof SubGraphRecord)
        .mapToInt(r -> ((SubGraphRecord) r).getResultNodes().size())
        .sum();
    int totalEdges = results.stream()
        .filter(r -> r instanceof SubGraphRecord)
        .mapToInt(r -> ((SubGraphRecord) r).getResultEdges().size())
        .sum();

    node.addTraceLog(
        "Extraction complete. Duration: %dms, Total: %d nodes, %d edges",
        duration, totalNodes, totalEdges
    );
    node.setStatus(StatusEnum.FINISH);

    return results;
}
```

---

## Integration Points Summary

### When OpenIE/Extraction is Integrated

| Pipeline Stage | Processor | OpenIE Integration? | Purpose |
|----------------|-----------|---------------------|---------|
| **Source Reading** | CsvFileSourceReader, StringSourceReader | ❌ No | Load raw data |
| **Type Mapping** | SPGTypeMappingProcessor | ❌ No | Map fields to schema |
| **Chunking** | ParagraphSplitProcessor | ❌ No | Prepare for extraction |
| **⭐ Extraction** | **LLMNlExtractProcessor** | **✅ YES (Schema-free)** | **OpenIE-style extraction** |
| **Extraction** | **LLMBasedExtractProcessor** | **✅ YES (Schema-aware)** | **Guided extraction** |
| **Extraction** | **UserDefinedExtractProcessor** | **✅ YES (Custom)** | **Integrate OpenIE tools** |
| **Relation Mapping** | RelationMappingProcessor | ⚠️ Partial | Create explicit relations |
| **Entity Linking** | EntityLinkingProcessor | ❌ No | Resolve entity references |
| **Entity Fusing** | EntityFusingProcessor | ❌ No | Merge duplicates |
| **Storage** | GraphStoreSinkWriter | ❌ No | Persist to graph |

### Summary of OpenIE Integration

1. **Primary Integration Point:** Extraction processors in the document processing pipeline
2. **Schema-Free Mode:** `LLMNlExtractProcessor` with `BuilderConstant.SCHEMA_FREE` - **most OpenIE-like**
3. **Schema-Aware Mode:** `LLMBasedExtractProcessor` for guided extraction
4. **Custom Integration:** `UserDefinedExtractProcessor` to integrate traditional OpenIE tools (Stanford, OLLIE, etc.)
5. **Technology:** Primarily LLM-based, but supports traditional NLP/OpenIE via Python operators
6. **Output:** SubGraphRecords (sub-graphs with entities and relations)
7. **Post-processing:** Extracted knowledge goes through linking, fusing, and validation before storage

### Key Constants

```java
// Builder constants for extraction
BuilderConstant.EXTRACTOR_ABC = "ExtractorABC"      // Python operator identifier
BuilderConstant.SCHEMA_FREE = "schema_free"         // OpenIE mode
BuilderConstant.SCHEMA_AWARE = "schema_aware"       // Guided extraction mode
BuilderConstant.LLM = "llm"                         // LLM config key
```

---

## Conclusion

**OpenIE in OpenSPG is NOT a single component, but a pattern integrated throughout the extraction pipeline.**

The key insight is:

> **LLMNlExtractProcessor with `SCHEMA_FREE` mode is the primary OpenIE integration point**, allowing discovery of entities and relations without predefined schemas. This is complemented by schema-aware extraction and custom operator support, providing flexibility to integrate any information extraction technique—from traditional OpenIE tools (Stanford, OLLIE) to modern LLM-based approaches.

### When to Use Each Extraction Mode

1. **Use Schema-Free (LLMNlExtractProcessor)** when:
   - Exploring new domains
   - No predefined schema exists
   - Maximum discovery is needed
   - This is true OpenIE

2. **Use Schema-Aware (LLMBasedExtractProcessor)** when:
   - You have a well-defined schema
   - Precision is more important than recall
   - You want to enforce type constraints

3. **Use Custom (UserDefinedExtractProcessor)** when:
   - You have domain-specific models
   - You want to integrate existing NLP/OpenIE tools
   - You need specialized extraction logic

### References

- **Source Code:**
  - `builder/core/src/main/java/com/antgroup/openspg/builder/core/physical/process/LLMNlExtractProcessor.java`
  - `builder/core/src/main/java/com/antgroup/openspg/builder/core/physical/process/LLMBasedExtractProcessor.java`
  - `builder/core/src/main/java/com/antgroup/openspg/builder/core/physical/process/UserDefinedExtractProcessor.java`
  - `common/util/src/main/java/com/antgroup/openspg/common/constants/BuilderConstant.java`

- **Related Documents:**
  - OPENSPG_DOCUMENT_LOADING_EXPLAINED.md - Complete document loading pipeline
  - OPENSPG_BOTTOM_UP_EXTRACTION.md - Core system extraction and architecture

---

*Document created: 2025-11-07*
*OpenSPG version: Based on commit ceeb3ef*
