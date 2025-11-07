# How OpenSPG Loads Documents: Complete Technical Deep Dive

This document provides an in-depth explanation of OpenSPG's document loading and processing pipeline, from HTTP API to graph storage.

## Table of Contents
1. [Architecture Overview](#architecture-overview)
2. [Pipeline Execution Model](#pipeline-execution-model)
3. [Document Reading Layer](#document-reading-layer)
4. [Processing Layer](#processing-layer)
5. [Storage Layer](#storage-layer)
6. [Complete Example Flow](#complete-example-flow)
7. [Code Examples](#code-examples)

---

## Architecture Overview

### High-Level Flow

```
┌──────────────────────────────────────────────────────────────────────┐
│                        1. API LAYER                                   │
│  POST /public/v1/builder/kag/submit                                  │
│  - Receives KagBuilderRequest                                        │
│  - Creates BuilderJob                                                │
│  - Submits to SchedulerService                                       │
└──────────────────────────────────────────────────────────────────────┘
                                │
                                ▼
┌──────────────────────────────────────────────────────────────────────┐
│                   2. PIPELINE CONFIGURATION                           │
│  Pipeline (JSON) → LogicalPlan (DAG) → PhysicalPlan (DAG)           │
│  - Nodes: source, processors, sink                                   │
│  - Edges: data flow between nodes                                    │
└──────────────────────────────────────────────────────────────────────┘
                                │
                                ▼
┌──────────────────────────────────────────────────────────────────────┐
│                   3. EXECUTION ORCHESTRATION                          │
│  LocalBuilderRunner                                                   │
│  - Parallel thread pool execution                                    │
│  - Batch processing                                                   │
│  - Error handling & metrics                                           │
└──────────────────────────────────────────────────────────────────────┘
        │                       │                       │
        ▼                       ▼                       ▼
┌──────────────┐    ┌─────────────────────┐    ┌───────────────┐
│ SOURCE READER│ ───│    PROCESSORS       │───│  SINK WRITER  │
│              │    │                     │    │               │
│ - CSV        │    │ - SPGTypeMapping   │    │ - GraphStore  │
│ - String/Doc │    │ - RelationMapping  │    │ - Neo4j       │
│ - Database   │    │ - ParagraphSplit   │    │ - Elasticsearch│
│              │    │ - LLMExtract       │    │               │
│              │    │ - Vectorizer       │    │               │
└──────────────┘    └─────────────────────┘    └───────────────┘
```

### Key Components

1. **API Layer** - HTTP endpoints for job submission
2. **Pipeline Configuration** - DAG-based execution plan
3. **Execution Orchestration** - Parallel batch processing
4. **Source Readers** - Read documents from various sources
5. **Processors** - Transform and enrich data
6. **Sink Writers** - Persist to graph database

---

## Pipeline Execution Model

### 1. Pipeline Definition (JSON)

OpenSPG uses a **JSON-based pipeline configuration** to define how documents flow through the system:

```json
{
  "nodes": [
    {
      "id": "source_1",
      "name": "CSV Reader",
      "nodeType": "CSV_SOURCE",
      "config": {
        "url": "/path/to/documents.csv",
        "startRow": 2,
        "columns": ["id", "content", "author"]
      }
    },
    {
      "id": "processor_1",
      "name": "Entity Mapping",
      "nodeType": "SPG_TYPE_MAPPING",
      "config": {
        "mappings": [
          {
            "spgType": "Document",
            "mappingConfigs": [
              {"source": "id", "target": "id"},
              {"source": "content", "target": "content"},
              {"source": "author", "target": "author"}
            ]
          }
        ]
      }
    },
    {
      "id": "sink_1",
      "name": "Graph Store Writer",
      "nodeType": "GRAPH_SINK",
      "config": {
        "graphStoreUrl": "bolt://localhost:7687"
      }
    }
  ],
  "edges": [
    {"from": "source_1", "to": "processor_1"},
    {"from": "processor_1", "to": "sink_1"}
  ]
}
```

### 2. LogicalPlan (Abstract DAG)

**File:** `builder/core/src/main/java/com/antgroup/openspg/builder/core/logical/LogicalPlan.java`

The Pipeline JSON is parsed into a **LogicalPlan** - a directed acyclic graph (DAG) of logical operations:

```java
public class LogicalPlan implements Serializable {
  private final Graph<BaseLogicalNode<?>, DefaultEdge> dag;

  public static LogicalPlan parse(Pipeline pipeline) {
    Graph<BaseLogicalNode<?>, DefaultEdge> graph = new DefaultDirectedGraph<>(DefaultEdge.class);

    // Add nodes
    for (Node node : pipeline.getNodes()) {
      BaseLogicalNode<?> logicalNode = parseNode(node);
      graph.addVertex(logicalNode);
    }

    // Add edges
    for (Edge edge : pipeline.getEdges()) {
      BaseLogicalNode<?> from = findNode(edge.getFrom());
      BaseLogicalNode<?> to = findNode(edge.getTo());
      graph.addEdge(from, to);
    }

    return new LogicalPlan(graph);
  }

  public Set<BaseLogicalNode<?>> sourceNodes() {
    // Returns nodes with no incoming edges
    return dag.vertexSet().stream()
        .filter(node -> dag.inDegreeOf(node) == 0)
        .collect(Collectors.toSet());
  }

  public Set<BaseLogicalNode<?>> sinkNodes() {
    // Returns nodes with no outgoing edges
    return dag.vertexSet().stream()
        .filter(node -> dag.outDegreeOf(node) == 0)
        .collect(Collectors.toSet());
  }
}
```

**Logical Node Types:**
- `CsvSourceNode` - CSV file reading
- `StringSourceNode` - Raw document text
- `SPGTypeMappingNode` - Entity type mapping
- `RelationMappingNode` - Relationship mapping
- `ParagraphSplitNode` - Document chunking
- `UserDefinedExtractNode` - Custom extraction
- `LLMBasedExtractNode` - LLM extraction
- `GraphStoreSinkNode` - Graph database writing

### 3. PhysicalPlan (Executable DAG)

**File:** `builder/core/src/main/java/com/antgroup/openspg/builder/core/physical/PhysicalPlan.java`

The LogicalPlan is converted to a **PhysicalPlan** - executable processor instances:

```java
public class PhysicalPlan implements Serializable {
  private final Graph<BaseProcessor<?>, DefaultEdge> dag;

  public static PhysicalPlan plan(LogicalPlan logicalPlan) {
    // Remove source/sink nodes (handled separately by runner)
    logicalPlan = logicalPlan.removeSourceAndSinkNodes();

    Graph<BaseProcessor<?>, DefaultEdge> graph = new DefaultDirectedGraph<>(DefaultEdge.class);

    // Convert logical nodes to physical processors
    for (BaseLogicalNode<?> logicalNode : logicalPlan.dag.vertexSet()) {
      BaseProcessor<?> processor = createProcessor(logicalNode);
      graph.addVertex(processor);
    }

    // Copy edges
    for (DefaultEdge edge : logicalPlan.dag.edgeSet()) {
      BaseLogicalNode<?> source = logicalPlan.dag.getEdgeSource(edge);
      BaseLogicalNode<?> target = logicalPlan.dag.getEdgeTarget(edge);
      graph.addEdge(
          findProcessor(source),
          findProcessor(target)
      );
    }

    return new PhysicalPlan(graph);
  }
}
```

---

## Document Reading Layer

### Base Source Reader Architecture

**File:** `builder/runner/local/src/main/java/com/antgroup/openspg/builder/runner/local/physical/source/BaseSourceReader.java`

```java
public abstract class BaseSourceReader<C> extends BasePhysicalNode {
  protected final C config;

  /**
   * Read data from source and return batch of records.
   * Returns empty list when no more data available.
   */
  public abstract List<BaseRecord> read();

  /**
   * Initialize reader with context (parallelism, batch size, etc.)
   */
  public abstract void doInit(BuilderContext context) throws BuilderException;

  /**
   * Cleanup resources
   */
  public abstract void close() throws Exception;
}
```

### 1. CSV File Source Reader

**File:** `builder/runner/local/src/main/java/com/antgroup/openspg/builder/runner/local/physical/source/impl/CsvFileSourceReader.java`

Reads documents from CSV files with configurable columns and starting row:

```java
public class CsvFileSourceReader extends BaseSourceReader<CsvSourceNodeConfig> {

  private Queue<BaseRecord> queue;
  private CSVReader csvReader;
  private Iterator<String[]> lines;
  private AtomicLong lineNumber;

  @Override
  public void doInit(BuilderContext context) throws BuilderException {
    // Create blocking queue for batch processing
    queue = new ArrayBlockingQueue<>(
        context.getBatchSize() * context.getParallelism()
    );

    // Open CSV file with skip rows
    csvReader = new CSVReaderBuilder(new FileReader(config.getUrl()))
        .withSkipLines(config.getStartRow() - 1)
        .build();

    lineNumber = new AtomicLong(config.getStartRow() - 1);
    lines = csvReader.iterator();
  }

  @Override
  public List<BaseRecord> read() {
    // Fill queue with next batch
    putQueue();

    // Drain batch from queue
    List<BaseRecord> results = new ArrayList<>(context.getBatchSize());
    for (int i = 0; i < context.getBatchSize(); i++) {
      BaseRecord record = queue.poll();
      if (record != null) {
        results.add(record);
      }
    }
    return results;
  }

  private void putQueue() {
    while (lines.hasNext() && queue.size() < context.getBatchSize()) {
      String[] fields = lines.next();
      lineNumber.incrementAndGet();

      // Parse CSV row to BuilderRecord
      BuilderRecord record = parse(fields);
      queue.offer(record);
    }
  }

  private BuilderRecord parse(String[] fields) {
    Map<String, String> props = new HashMap<>();

    // Map CSV columns to properties
    for (int i = 0; i < config.getColumns().size(); i++) {
      String column = config.getColumns().get(i);
      String value = i >= fields.length ? null : fields[i];
      props.put(column, value);
    }

    return new BuilderRecord(
        "line" + lineNumber.get(),  // Record ID
        null,                        // SPG Type (determined later)
        props                        // Properties
    );
  }
}
```

**Configuration Example:**
```java
CsvSourceNodeConfig config = new CsvSourceNodeConfig(
    2,                                    // Start from row 2
    "/data/documents.csv",                // File path
    Arrays.asList("id", "title", "content", "author")  // Columns
);
```

### 2. String Source Reader (Raw Documents)

**File:** `builder/runner/local/src/main/java/com/antgroup/openspg/builder/runner/local/physical/source/impl/StringSourceReader.java`

Reads raw document text (typically from API or file):

```java
public class StringSourceReader extends BaseSourceReader<StringSourceNodeConfig> {

  private String document;
  private ExecuteNode node = new ExecuteNode();

  @Override
  public void doInit(BuilderContext context) throws BuilderException {
    this.document = config.getDocument();
    if (node != null) {
      node.setStatus(StatusEnum.RUNNING);
      node.addTraceLog("Start reading document...");
    }
  }

  @Override
  public List<BaseRecord> read() {
    List<BaseRecord> results = new ArrayList<>();

    if (StringUtils.isBlank(document)) {
      return results; // No more data
    }

    // Create StringRecord with raw document content
    BaseRecord record = new StringRecord(document);
    results.add(record);

    // Clear document (read once only)
    document = null;

    return results;
  }
}
```

**StringRecord Model:**
```java
@Getter
@AllArgsConstructor
public class StringRecord extends BaseRecord {
  private final String document; // Raw document text
}
```

### 3. Source Reader Factory

**File:** `builder/runner/local/src/main/java/com/antgroup/openspg/builder/runner/local/physical/source/SourceReaderFactory.java`

Creates appropriate reader based on node type:

```java
public class SourceReaderFactory {

  public static BaseSourceReader<?> getSourceReader(BaseLogicalNode<?> node) {
    switch (node.getType()) {
      case CSV_SOURCE:
        CsvSourceNode csvNode = (CsvSourceNode) node;
        return new CsvFileSourceReader(
            csvNode.getId(),
            csvNode.getName(),
            csvNode.getNodeConfig()
        );

      case STRING_SOURCE:
        StringSourceNode stringNode = (StringSourceNode) node;
        return new StringSourceReader(
            stringNode.getId(),
            stringNode.getName(),
            stringNode.getNodeConfig()
        );

      default:
        throw new IllegalArgumentException("Unknown source type: " + node.getType());
    }
  }
}
```

---

## Processing Layer

### Base Processor Architecture

**File:** `builder/core/src/main/java/com/antgroup/openspg/builder/core/physical/process/BaseProcessor.java`

```java
public abstract class BaseProcessor<C> extends BasePhysicalNode {
  protected final C config;

  /**
   * Process input records and return transformed records.
   * @param inputs - Records from upstream processor
   * @return Processed records to send downstream
   */
  public abstract List<BaseRecord> process(List<BaseRecord> inputs);

  /**
   * Initialize processor with context
   */
  public void doInit(BuilderContext context) throws BuilderException {}

  /**
   * Cleanup resources
   */
  public void close() throws Exception {}
}
```

### 1. SPG Type Mapping Processor (Entity Extraction)

**File:** `builder/core/src/main/java/com/antgroup/openspg/builder/core/physical/process/SPGTypeMappingProcessor.java`

Maps raw records to typed SPG entities (Document, Person, Organization, etc.):

```java
public class SPGTypeMappingProcessor extends BaseProcessor<SPGTypeMappingNodeConfigs> {

  private final List<SPGTypeMappingHelper> mappingHelpers;

  @Override
  public List<BaseRecord> process(List<BaseRecord> inputs) {
    List<BaseSPGRecord> resultSpgRecords = new ArrayList<>();

    // Group records by SPG type
    Map<SPGTypeIdentifier, List<BuilderRecord>> groupedRecords = groupByType(inputs);

    // Apply mapping for each type
    for (SPGTypeMappingHelper helper : mappingHelpers) {
      SPGTypeIdentifier typeId = helper.getTypeIdentifier();
      List<BuilderRecord> records = groupedRecords.get(typeId);

      if (records == null) continue;

      for (BuilderRecord record : records) {
        // Filter based on conditions
        if (helper.isFiltered(record)) {
          continue;
        }

        // Convert BuilderRecord → EntityRecord/ConceptRecord
        List<BaseSPGRecord> spgRecords = helper.toSPGRecords(record, true);
        resultSpgRecords.addAll(spgRecords);
      }
    }

    return (List) resultSpgRecords;
  }
}
```

**SPGTypeMappingHelper:**
```java
public class SPGTypeMappingHelper {

  private final SPGTypeIdentifier typeIdentifier;
  private final List<MappingConfig> mappingConfigs;
  private final List<FilterCondition> filterConditions;

  public List<BaseSPGRecord> toSPGRecords(BuilderRecord record,
                                          boolean includeId) {
    // Map source fields to target SPG properties
    Map<String, String> mappedProps = new HashMap<>();
    for (MappingConfig config : mappingConfigs) {
      String sourceValue = record.getPropValue(config.getSource());
      if (sourceValue != null) {
        mappedProps.put(config.getTarget(), sourceValue);
      }
    }

    // Create EntityRecord or ConceptRecord based on type
    BaseSPGRecord spgRecord;
    if (typeIdentifier.isEntityType()) {
      spgRecord = new EntityRecord(
          typeIdentifier,
          record.getRecordId(),  // Entity ID
          mappedProps            // Properties
      );
    } else if (typeIdentifier.isConceptType()) {
      spgRecord = new ConceptRecord(
          typeIdentifier,
          record.getRecordId(),
          mappedProps
      );
    }

    return Arrays.asList(spgRecord);
  }

  public boolean isFiltered(BuilderRecord record) {
    for (FilterCondition condition : filterConditions) {
      if (!condition.evaluate(record)) {
        return true;  // Filtered out
      }
    }
    return false;  // Passed all filters
  }
}
```

**Example Configuration:**
```json
{
  "nodeType": "SPG_TYPE_MAPPING",
  "config": {
    "mappings": [
      {
        "spgType": "Document",
        "mappingConfigs": [
          {"source": "id", "target": "id"},
          {"source": "title", "target": "title"},
          {"source": "content", "target": "content"},
          {"source": "author", "target": "author"}
        ],
        "filterConditions": [
          {"field": "content", "operator": "NOT_NULL"}
        ]
      }
    ]
  }
}
```

### 2. Paragraph Split Processor (Document Chunking)

**File:** `builder/core/src/main/java/com/antgroup/openspg/builder/core/physical/process/ParagraphSplitProcessor.java`

Splits documents into smaller chunks/paragraphs using Python-based text splitters:

```java
public class ParagraphSplitProcessor extends BasePythonProcessor<ParagraphSplitNodeConfig> {

  private ExecuteNode node = new ExecuteNode();

  @Override
  public List<BaseRecord> process(List<BaseRecord> inputs) {
    node.setStatus(StatusEnum.RUNNING);
    node.addTraceLog("Start splitting documents...");

    List<BaseRecord> results = new ArrayList<>();

    for (BaseRecord record : inputs) {
      StringRecord stringRecord = (StringRecord) record;
      String documentText = stringRecord.getDocument();

      // Call Python splitter operator
      Map<String, Object> params = new HashMap<>();
      params.put("document", documentText);
      params.put("chunk_size", config.getChunkSize());
      params.put("overlap", config.getOverlap());

      List<Object> splitResult = operatorFactory.invoke(
          config.getOperatorConfig(),
          BuilderConstant.SPLITTER_ABC,  // Python splitter module
          params
      );

      // Parse result to ChunkRecords
      List<ChunkRecord.Chunk> chunks = JSON.parseObject(
          JSON.toJSONString(splitResult),
          new TypeReference<List<ChunkRecord.Chunk>>() {}
      );

      for (ChunkRecord.Chunk chunk : chunks) {
        ChunkRecord chunkRecord = new ChunkRecord(chunk);
        results.add(chunkRecord);
      }
    }

    node.setStatus(StatusEnum.FINISH);
    return results;
  }
}
```

**ChunkRecord Model:**
```java
@Getter
@AllArgsConstructor
public class ChunkRecord extends BaseRecord {
  private final Chunk chunk;

  @Data
  public static class Chunk {
    private String id;           // Chunk ID
    private String name;          // Chunk name/title
    private String content;       // Chunk text content
    private String type;          // Type: paragraph, heading, table
    private String header;        // Header/section
    private String summary;       // Summary (optional)
    private String textIndex;     // Text index ID
    private String vecIndex;      // Vector embedding ID
  }
}
```

**Python Splitter (called via Pemja bridge):**
```python
# kag/builder/component/splitter/paragraph_splitter.py

from langchain.text_splitter import RecursiveCharacterTextSplitter

def split_document(document: str, chunk_size: int = 512,
                  overlap: int = 50) -> List[Dict]:
    """Split document into chunks using LangChain."""
    splitter = RecursiveCharacterTextSplitter(
        chunk_size=chunk_size,
        chunk_overlap=overlap,
        separators=["\n\n", "\n", " ", ""]
    )

    chunks = []
    text_chunks = splitter.split_text(document)

    for i, chunk_text in enumerate(text_chunks):
        chunk = {
            "id": f"chunk_{i}",
            "content": chunk_text,
            "type": "paragraph",
            "name": f"Paragraph {i+1}"
        }
        chunks.append(chunk)

    return chunks
```

### 3. LLM-Based Extract Processor (Knowledge Extraction)

**File:** `builder/core/src/main/java/com/antgroup/openspg/builder/core/physical/process/LLMBasedExtractProcessor.java`

Uses LLMs to extract entities, relationships, and knowledge from document chunks:

```java
public class LLMBasedExtractProcessor extends BasePythonProcessor<LLMBasedExtractNodeConfig> {

  private ExecuteNode node = new ExecuteNode();

  @Override
  public List<BaseRecord> process(List<BaseRecord> inputs) {
    node.setStatus(StatusEnum.RUNNING);
    node.addTraceLog("Start LLM extraction...");

    List<BaseRecord> results = new ArrayList<>();

    for (BaseRecord record : inputs) {
      ChunkRecord chunkRecord = (ChunkRecord) record;

      // Prepare extraction prompt
      Map<String, Object> params = new HashMap<>();
      params.put("chunk", chunkRecord.getChunk().getContent());
      params.put("schema", context.getCatalog().toSchemaPrompt());
      params.put("instruction", config.getExtractionInstruction());

      // Call Python LLM extractor
      List<Object> extractResult = operatorFactory.invoke(
          config.getOperatorConfig(),
          BuilderConstant.EXTRACTOR_ABC,
          params
      );

      // Parse extracted sub-graph (nodes + edges)
      List<SubGraphRecord> subGraphs = JSON.parseObject(
          JSON.toJSONString(extractResult),
          new TypeReference<List<SubGraphRecord>>() {}
      );

      for (SubGraphRecord subGraph : subGraphs) {
        node.addTraceLog("Extracted %d nodes and %d edges",
            subGraph.getResultNodes().size(),
            subGraph.getResultEdges().size());
        results.add(subGraph);
      }
    }

    node.setStatus(StatusEnum.FINISH);
    return results;
  }
}
```

**SubGraphRecord Model:**
```java
@Getter
@AllArgsConstructor
public class SubGraphRecord extends BaseRecord {
  private final List<BaseSPGRecord> resultNodes;  // Extracted entities
  private final List<BaseSPGRecord> resultEdges;  // Extracted relationships
}
```

**Python LLM Extractor (simplified):**
```python
# kag/builder/component/extractor/llm_extractor.py

from openai import OpenAI

def extract_knowledge(chunk: str, schema: str, instruction: str) -> Dict:
    """Extract entities and relations using LLM."""
    client = OpenAI()

    prompt = f"""
    {instruction}

    Schema:
    {schema}

    Text:
    {chunk}

    Extract entities and relationships in JSON format:
    {{
      "nodes": [
        {{"type": "Person", "name": "...", "properties": {{...}}}}
      ],
      "edges": [
        {{"source": "...", "target": "...", "type": "...", "properties": {{...}}}}
      ]
    }}
    """

    response = client.chat.completions.create(
        model="gpt-4",
        messages=[{"role": "user", "content": prompt}]
    )

    result = json.loads(response.choices[0].message.content)
    return result
```

### 4. Relation Mapping Processor (Relationship Creation)

**File:** `builder/core/src/main/java/com/antgroup/openspg/builder/core/physical/process/RelationMappingProcessor.java`

Creates relationships between entities based on mapping rules:

```java
public class RelationMappingProcessor extends BaseProcessor<RelationMappingNodeConfig> {

  private Relation relation;
  private RecordLinking recordLinking;

  @Override
  public void doInit(BuilderContext context) throws BuilderException {
    super.doInit(context);

    // Load relation schema
    RelationIdentifier identifier = RelationIdentifier.parse(config.getRelation());
    this.relation = (Relation) loadSchema(identifier, context.getCatalog());

    // Initialize record linking (entity resolution)
    this.recordLinking = new RecordLinkingImpl(config.getMappingConfigs());
    this.recordLinking.init(context);
  }

  @Override
  public List<BaseRecord> process(List<BaseRecord> inputs) {
    List<BaseRecord> spgRecords = new ArrayList<>();

    for (BaseRecord baseRecord : inputs) {
      BuilderRecord record = (BuilderRecord) baseRecord;

      // Apply filters
      if (isFiltered(record, config.getMappingFilters())) {
        continue;
      }

      // Map source fields to relation properties
      BuilderRecord mappedRecord = mapping(record, config.getMappingConfigs());

      // Create RelationRecord
      RelationRecord relationRecord = toRelationRecord(mappedRecord, relation);

      // Link source/target entities (entity resolution)
      recordLinking.linking(relationRecord);

      spgRecords.add(relationRecord);
    }

    return spgRecords;
  }

  private RelationRecord toRelationRecord(BuilderRecord record, Relation relation) {
    String srcId = record.getPropValue("srcId");
    String dstId = record.getPropValue("dstId");

    if (StringUtils.isBlank(srcId) || StringUtils.isBlank(dstId)) {
      throw new BuilderRecordException("Missing source or destination ID");
    }

    // Create typed relation record
    return EdgeRecordConvertor.toRelationRecord(
        relation,
        srcId,   // Source entity ID
        dstId,   // Target entity ID
        record.getProps()  // Relation properties
    );
  }
}
```

**Example Configuration:**
```json
{
  "nodeType": "RELATION_MAPPING",
  "config": {
    "relation": "Document.hasAuthor.Person",
    "mappingConfigs": [
      {"source": "document_id", "target": "srcId"},
      {"source": "author_id", "target": "dstId"}
    ],
    "filterConditions": [
      {"field": "author_id", "operator": "NOT_NULL"}
    ]
  }
}
```

### 5. Vectorizer Processor (Embedding Generation)

**File:** `builder/core/src/main/java/com/antgroup/openspg/builder/core/physical/process/VectorizerProcessor.java`

Generates vector embeddings for text content:

```java
public class VectorizerProcessor extends BasePythonProcessor<VectorizerNodeConfig> {

  @Override
  public List<BaseRecord> process(List<BaseRecord> inputs) {
    List<BaseRecord> results = new ArrayList<>();

    for (BaseRecord record : inputs) {
      BaseSPGRecord spgRecord = (BaseSPGRecord) record;

      // Get text content to embed
      String textContent = extractTextContent(spgRecord);

      // Call Python embedding model
      Map<String, Object> params = new HashMap<>();
      params.put("text", textContent);
      params.put("model", config.getModelName());

      List<Object> embeddingResult = operatorFactory.invoke(
          config.getOperatorConfig(),
          BuilderConstant.VECTORIZER_ABC,
          params
      );

      // Add embedding to record
      float[] embedding = parseEmbedding(embeddingResult);
      spgRecord.addProperty("vector", embedding);

      results.add(spgRecord);
    }

    return results;
  }
}
```

---

## Storage Layer

### Base Sink Writer Architecture

**File:** `builder/runner/local/src/main/java/com/antgroup/openspg/builder/runner/local/physical/sink/BaseSinkWriter.java`

```java
public abstract class BaseSinkWriter<C> extends BasePhysicalNode {
  protected final C config;

  /**
   * Write records to storage backend.
   * @param records - Processed records to persist
   */
  public abstract void write(List<BaseRecord> records);

  /**
   * Initialize writer with context
   */
  public void doInit(BuilderContext context) throws BuilderException {}

  /**
   * Cleanup resources
   */
  public void close() throws Exception {}
}
```

### Graph Store Sink Writer (TuGraph/Neo4j)

**File:** `builder/runner/local/src/main/java/com/antgroup/openspg/builder/runner/local/physical/sink/impl/GraphStoreSinkWriter.java`

Persists SPG records to graph database:

```java
public class GraphStoreSinkWriter extends BaseSinkWriter<GraphStoreSinkNodeConfig> {

  private GraphStoreClient graphStoreClient;
  private CheckProcessor checkProcessor;

  @Override
  public void doInit(BuilderContext context) throws BuilderException {
    // Initialize graph store client (TuGraph, Neo4j, etc.)
    graphStoreClient = GraphStoreClientDriverManager.getClient(
        context.getGraphStoreUrl()
    );

    // Initialize data validation processor
    checkProcessor = new CheckProcessor();
    checkProcessor.init(context);
  }

  @Override
  public void write(List<BaseRecord> records) {
    if (CollectionUtils.isEmpty(records) || !config.getIsWriter()) {
      return;
    }

    // Validate records if UPSERT operation
    if (RecordAlterOperationEnum.UPSERT == context.getOperation()) {
      records = checkProcessor.process(records);
    }

    // Batch write to graph store
    batchWriteToGraphStore(records);
  }

  private void batchWriteToGraphStore(List<BaseRecord> records) {
    // Convert records to graph store commands
    List<SPGRecordAlterItem> items = records.stream()
        .map(record -> new SPGRecordAlterItem(
            context.getOperation(),  // UPSERT, INSERT, UPDATE, DELETE
            (BaseSPGRecord) record
        ))
        .collect(Collectors.toList());

    // Execute batch write
    SPGRecordManipulateCmd cmd = new SPGRecordManipulateCmd(items);
    graphStoreClient.manipulateRecord(cmd);
  }
}
```

**GraphStoreClient Interface:**
```java
public interface GraphStoreClient {

  /**
   * Batch manipulate SPG records (insert, update, delete).
   */
  void manipulateRecord(SPGRecordManipulateCmd cmd);

  /**
   * Query records by IDs.
   */
  List<BaseSPGRecord> queryRecords(List<String> ids);

  /**
   * Execute Cypher query.
   */
  QueryResult executeQuery(String cypher, Map<String, Object> params);
}
```

**SPGRecordAlterItem:**
```java
@Getter
@AllArgsConstructor
public class SPGRecordAlterItem {
  private final RecordAlterOperationEnum operation;  // UPSERT, INSERT, UPDATE, DELETE
  private final BaseSPGRecord record;                // Entity, Relation, Concept, etc.
}

public enum RecordAlterOperationEnum {
  UPSERT,   // Insert or update if exists
  INSERT,   // Insert only (fail if exists)
  UPDATE,   // Update only (fail if not exists)
  DELETE    // Delete record
}
```

---

## Complete Example Flow

### Scenario: Load Research Papers from CSV

Let's trace how a CSV file of research papers flows through OpenSPG:

#### 1. Input Data (papers.csv)

```csv
id,title,abstract,authors,year,citations
paper1,"Graph Neural Networks","Abstract about GNNs...","Alice;Bob",2020,150
paper2,"Knowledge Graphs","Abstract about KGs...","Carol;David",2019,200
paper3,"Machine Learning","Abstract about ML...","Alice;Emma",2021,100
```

#### 2. Pipeline Configuration

```json
{
  "nodes": [
    {
      "id": "csv_reader",
      "nodeType": "CSV_SOURCE",
      "config": {
        "url": "/data/papers.csv",
        "startRow": 2,
        "columns": ["id", "title", "abstract", "authors", "year", "citations"]
      }
    },
    {
      "id": "paper_mapping",
      "nodeType": "SPG_TYPE_MAPPING",
      "config": {
        "mappings": [{
          "spgType": "Paper",
          "mappingConfigs": [
            {"source": "id", "target": "id"},
            {"source": "title", "target": "title"},
            {"source": "abstract", "target": "abstract"},
            {"source": "year", "target": "year"},
            {"source": "citations", "target": "citations"}
          ]
        }]
      }
    },
    {
      "id": "author_extraction",
      "nodeType": "USER_DEFINED_EXTRACT",
      "config": {
        "operatorConfig": {
          "module": "extract_authors",
          "function": "split_authors"
        }
      }
    },
    {
      "id": "authorship_relation",
      "nodeType": "RELATION_MAPPING",
      "config": {
        "relation": "Paper.hasAuthor.Person",
        "mappingConfigs": [
          {"source": "paper_id", "target": "srcId"},
          {"source": "author_name", "target": "dstId"}
        ]
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
    {"from": "csv_reader", "to": "paper_mapping"},
    {"from": "paper_mapping", "to": "author_extraction"},
    {"from": "author_extraction", "to": "authorship_relation"},
    {"from": "authorship_relation", "to": "graph_writer"}
  ]
}
```

#### 3. Execution Flow

**Step 1: CSV Reader reads first batch**
```java
// CsvFileSourceReader.read()
List<BaseRecord> batch = [
  BuilderRecord {
    recordId: "line2",
    identifier: null,
    props: {
      "id": "paper1",
      "title": "Graph Neural Networks",
      "abstract": "Abstract about GNNs...",
      "authors": "Alice;Bob",
      "year": "2020",
      "citations": "150"
    }
  }
]
```

**Step 2: SPG Type Mapping converts to EntityRecord**
```java
// SPGTypeMappingProcessor.process(batch)
List<BaseSPGRecord> mappedRecords = [
  EntityRecord {
    recordType: SPGRecordTypeEnum.ENTITY,
    spgTypeIdentifier: SPGTypeIdentifier("Paper"),
    id: "paper1",
    properties: [
      Property("id", "paper1"),
      Property("title", "Graph Neural Networks"),
      Property("abstract", "Abstract about GNNs..."),
      Property("year", 2020),
      Property("citations", 150)
    ]
  }
]
```

**Step 3: Author Extraction extracts authors**
```java
// UserDefinedExtractProcessor.process(mappedRecords)
// Calls Python: extract_authors.split_authors("Alice;Bob")

List<BuilderRecord> authorRecords = [
  BuilderRecord {
    recordId: "author_alice",
    identifier: SPGTypeIdentifier("Person"),
    props: {
      "name": "Alice",
      "paper_id": "paper1"
    }
  },
  BuilderRecord {
    recordId: "author_bob",
    identifier: SPGTypeIdentifier("Person"),
    props: {
      "name": "Bob",
      "paper_id": "paper1"
    }
  }
]
```

**Step 4: Relation Mapping creates authorship edges**
```java
// RelationMappingProcessor.process(authorRecords)
List<RelationRecord> relations = [
  RelationRecord {
    recordType: SPGRecordTypeEnum.RELATION,
    relationIdentifier: RelationIdentifier("Paper.hasAuthor.Person"),
    srcId: "paper1",
    dstId: "Alice",
    properties: []
  },
  RelationRecord {
    recordType: SPGRecordTypeEnum.RELATION,
    relationIdentifier: RelationIdentifier("Paper.hasAuthor.Person"),
    srcId: "paper1",
    dstId: "Bob",
    properties: []
  }
]
```

**Step 5: Graph Store Writer persists to database**
```java
// GraphStoreSinkWriter.write(relations)
graphStoreClient.manipulateRecord(
  new SPGRecordManipulateCmd([
    SPGRecordAlterItem(UPSERT, paperEntity),
    SPGRecordAlterItem(UPSERT, aliceEntity),
    SPGRecordAlterItem(UPSERT, bobEntity),
    SPGRecordAlterItem(UPSERT, paperAliceRelation),
    SPGRecordAlterItem(UPSERT, paperBobRelation)
  ])
);
```

**Result in Graph Database:**
```
(paper1:Paper {
  id: "paper1",
  title: "Graph Neural Networks",
  abstract: "Abstract about GNNs...",
  year: 2020,
  citations: 150
})

(alice:Person {name: "Alice"})
(bob:Person {name: "Bob"})

(paper1)-[:hasAuthor]->(alice)
(paper1)-[:hasAuthor]->(bob)
```

---

## Code Examples

### Complete LocalBuilderRunner Initialization

```java
// File: builder/runner/local/src/main/java/com/antgroup/openspg/builder/runner/local/LocalBuilderRunner.java

public class LocalBuilderRunner implements BuilderRunner {

  @Override
  public void init(Pipeline pipeline, BuilderContext context) throws BuilderException {
    // Step 1: Parse Pipeline JSON to LogicalPlan (DAG)
    LogicalPlan logicalPlan = LogicalPlan.parse(pipeline);

    // Step 2: Get source reader node (entry point)
    BaseLogicalNode<?> sourceNode = logicalPlan.sourceNodes().stream()
        .findFirst()
        .orElseThrow(() -> new BuilderException("No source node found"));
    sourceReader = SourceReaderFactory.getSourceReader(sourceNode);
    sourceReader.init(context);

    // Step 3: Get sink writer node (exit point)
    BaseLogicalNode<?> sinkNode = logicalPlan.sinkNodes().stream()
        .findFirst()
        .orElseThrow(() -> new BuilderException("No sink node found"));
    sinkWriter = SinkWriterFactory.getSinkWriter(sinkNode);
    sinkWriter.init(context);

    // Step 4: Convert LogicalPlan to PhysicalPlan (remove source/sink)
    PhysicalPlan physicalPlan = PhysicalPlan.plan(logicalPlan);

    // Step 5: Initialize executor with physical plan
    builderExecutor = new DefaultBuilderExecutor();
    builderExecutor.init(physicalPlan, context);

    // Step 6: Setup metrics reporting
    builderMetric = new BuilderMetric(context.getJobName());
    builderMetric.reportToLog();
  }

  @Override
  public void execute() throws Exception {
    final int parallelism = context.getParallelism();
    final int batchSize = context.getBatchSize();

    // Create thread pool for parallel processing
    ThreadPoolExecutor threadPoolExecutor = ThreadUtils.newDaemonFixedThreadPool(
        parallelism, "builder-thread-"
    );

    List<CompletableFuture<Void>> futures = new ArrayList<>(parallelism);

    // Launch parallel threads
    for (int i = 0; i < parallelism; i++) {
      CompletableFuture<Void> future = CompletableFuture.runAsync(() -> {

        // Read first batch
        List<BaseRecord> records = sourceReader.read();

        // Process until no more data
        while (CollectionUtils.isNotEmpty(records)) {

          try {
            // Execute through pipeline
            List<BaseRecord> results = builderExecutor.eval(records);

            // Write to sink
            if (CollectionUtils.isNotEmpty(results)) {
              sinkWriter.write(results);
            }

          } catch (BuilderRecordException e) {
            log.error("Builder record error", e);
          }

          // Read next batch
          records = sourceReader.read();
        }

      }, threadPoolExecutor);

      futures.add(future);
    }

    // Wait for all threads to complete
    CompletableFuture.allOf(futures.toArray(new CompletableFuture[0])).join();

    // Cleanup
    threadPoolExecutor.shutdownNow();
  }
}
```

### DefaultBuilderExecutor Recursive Processing

```java
// File: builder/core/src/main/java/com/antgroup/openspg/builder/core/runtime/impl/DefaultBuilderExecutor.java

public class DefaultBuilderExecutor implements BuilderExecutor {

  private PhysicalPlan plan;

  @Override
  public List<BaseRecord> eval(List<BaseRecord> inputRecords)
      throws BuilderRecordException {

    List<BaseRecord> finalResults = new ArrayList<>();

    // Get entry point processors (nodes with no predecessors)
    Set<BaseProcessor<?>> sourceProcessors = plan.sourceNodes();

    // Process through each source processor
    for (BaseProcessor<?> processor : sourceProcessors) {
      processRecursively(processor, inputRecords, finalResults);
    }

    return finalResults;
  }

  /**
   * Recursively process records through processor DAG.
   */
  private void processRecursively(BaseProcessor<?> processor,
                                 List<BaseRecord> inputs,
                                 List<BaseRecord> finalResults) {
    if (CollectionUtils.isEmpty(inputs)) {
      return;
    }

    // Process records through current processor
    List<BaseRecord> outputs = processor.process(inputs);

    // Get downstream processors
    Set<BaseProcessor<?>> nextProcessors = plan.successors(processor);

    if (CollectionUtils.isEmpty(nextProcessors)) {
      // No more processors - add to final results
      finalResults.addAll(outputs);
    } else {
      // Continue to downstream processors
      for (BaseProcessor<?> nextProcessor : nextProcessors) {
        processRecursively(nextProcessor, outputs, finalResults);
      }
    }
  }
}
```

---

## Summary

### Key Takeaways

1. **Pipeline-Based Architecture** - OpenSPG uses a **DAG-based pipeline model** where documents flow through configurable stages (source → processors → sink).

2. **Three-Layer Abstraction**:
   - **Pipeline (JSON)** - User-defined configuration
   - **LogicalPlan (DAG)** - Abstract execution plan
   - **PhysicalPlan (DAG)** - Concrete processor instances

3. **Parallel Batch Processing** - Documents are read in batches and processed in parallel threads for high throughput.

4. **Pluggable Components**:
   - **Source Readers** - CSV, String, Database, etc.
   - **Processors** - Type mapping, relation mapping, extraction, chunking, vectorization
   - **Sink Writers** - Graph database, search engine, cache

5. **Record Transformation Flow**:
   ```
   Raw Data (CSV/String)
     → BuilderRecord (key-value)
     → BaseSPGRecord (typed: Entity/Relation/Concept)
     → Graph Storage
   ```

6. **Python Integration** - LLM extraction, text splitting, and vectorization use Python operators called via Pemja (Python-Java bridge).

7. **Entity Resolution** - RecordLinking component handles entity resolution and disambiguation during relationship creation.

8. **Graph Store Abstraction** - Supports multiple graph databases (TuGraph, Neo4j) through unified interface.

This architecture allows OpenSPG to handle large-scale document ingestion with high parallelism, flexible processing pipelines, and seamless integration with LLMs and knowledge extraction tools.
