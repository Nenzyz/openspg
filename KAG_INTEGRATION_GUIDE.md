# KAG Integration with OpenSPG
## Key Integration Points for Knowledge Augmented Generation

**Document Purpose:** This guide details how KAG (Knowledge Augmented Generation) integrates with OpenSPG from the OpenSPG side, enabling you to connect a KAG implementation to OpenSPG.

**Version:** Based on OpenSPG v0.8
**Date:** 2025-11-05

---

## Table of Contents

1. [Overview](#1-overview)
2. [KAG Pipeline Architecture](#2-kag-pipeline-architecture)
3. [IndexType Schema Integration](#3-indextype-schema-integration)
4. [Data Models](#4-data-models)
5. [Builder Pipeline Tasks](#5-builder-pipeline-tasks)
6. [Python Operator Integration](#6-python-operator-integration)
7. [Storage Integration](#7-storage-integration)
8. [Retrieval Service Integration](#8-retrieval-service-integration)
9. [API Integration Points](#9-api-integration-points)
10. [Implementation Guide](#10-implementation-guide)

---

## 1. Overview

### 1.1 What is KAG?

KAG (Knowledge Augmented Generation) is OpenSPG's framework for:
- **Document Processing:** Chunking, extraction, summarization
- **Knowledge Indexing:** Building searchable indices from documents
- **Vector Embeddings:** Generating embeddings for semantic search
- **Graph-Enhanced RAG:** Using knowledge graphs to improve LLM responses

### 1.2 Integration Architecture

```
┌──────────────────────────────────────────────────────┐
│                   KAG System                         │
│  (External Python Service - Separate from OpenSPG)   │
│                                                      │
│  ┌─────────┐  ┌──────────┐  ┌───────────┐         │
│  │  LLM    │  │ Embedder │  │ Chunker   │         │
│  │ Service │  │ Service  │  │ Service   │         │
│  └─────────┘  └──────────┘  └───────────┘         │
└──────────────────────────────────────────────────────┘
            ↕ Python Calls (via Pemja)
┌──────────────────────────────────────────────────────┐
│            OpenSPG Integration Layer                 │
│                                                      │
│  ┌────────────────────────────────────────┐         │
│  │  KAG Builder Pipeline (Java)           │         │
│  │  - Scanner → Reader → Mapper →         │         │
│  │    Splitter → Extractor → Alignment →  │         │
│  │    Vectorizer → Writer                  │         │
│  └────────────────────────────────────────┘         │
│                                                      │
│  ┌────────────────────────────────────────┐         │
│  │  Data Models                            │         │
│  │  - ChunkRecord                          │         │
│  │  - SubGraphRecord                       │         │
│  └────────────────────────────────────────┘         │
│                                                      │
│  ┌────────────────────────────────────────┐         │
│  │  IndexType Schema                       │         │
│  │  - Special schema type for indices     │         │
│  └────────────────────────────────────────┘         │
└──────────────────────────────────────────────────────┘
            ↓
┌──────────────────────────────────────────────────────┐
│              OpenSPG Core                            │
│  - Graph Store (Vertices/Edges)                     │
│  - Search Engine (Text/Vector indices)              │
│  - Schema Registry                                   │
└──────────────────────────────────────────────────────┘
```

**Key Insight:** KAG is a **separate system** that integrates with OpenSPG through:
1. **Builder Pipeline** - Orchestrates KAG tasks
2. **Python Operators** - Calls KAG Python services via Pemja
3. **IndexType Schema** - Stores index metadata in graph
4. **Object Storage** - Temporary storage for chunks/vectors
5. **Retrieval Service** - Manages search indices

---

## 2. KAG Pipeline Architecture

### 2.1 Complete Pipeline Flow

```
Documents (PDF, TXT, DOCX, etc.)
    ↓
[1. Scanner] - Discover files from source
    ↓
[2. Reader] - Read file contents
    ↓
[3. Mapping] - Extract structured metadata
    ↓
[4. Splitter] - Chunk documents into segments
    ↓ ChunkRecord[]
[5. Extractor] - Extract entities/relations using LLM
    ↓ SubGraphRecord[]
[6. Alignment] - Align extracted entities with KG
    ↓
[7. Vectorizer] - Generate embeddings
    ↓
[8. Writer] - Write to graph store + search index
    ↓
Knowledge Graph + Vector Index
```

### 2.2 Task Types

OpenSPG implements KAG as a series of scheduled tasks:

| Task | Type | Description | Output |
|------|------|-------------|--------|
| `kagScannerSyncTask` | Sync | Scan source for documents | File list |
| `kagReaderSyncTask` | Sync | Read document contents | Raw text |
| `kagMappingSyncTask` | Sync | Extract document metadata | Metadata |
| `kagSplitterAsyncTask` | Async | Split into chunks | `ChunkRecord[]` |
| `kagExtractorAsyncTask` | Async | Extract KG from chunks | `SubGraphRecord[]` |
| `kagAlignmentAsyncTask` | Async | Align entities with existing KG | Aligned graphs |
| `kagVectorizerAsyncTask` | Async | Generate embeddings | Vectors |
| `kagWriterAsyncTask` | Async | Write to storage | Persisted KG |

**Task Coordinator:**
- **Class:** `KagBuilderTranslate`
- **Location:** `server/core/scheduler/service/src/main/java/.../KagBuilderTranslate.java`
- **Function:** Converts KAG job into task DAG (Directed Acyclic Graph)

### 2.3 Task DAG Example

```java
// From KagBuilderTranslate.java
public TaskExecuteDag getTaskDag(BuilderJob builderJob) {
    List<TaskExecuteDag.Node> nodes = Lists.newArrayList();
    List<TaskExecuteDag.Edge> edges = Lists.newArrayList();

    // Node 1: Create Index (Retrieval)
    TaskExecuteDag.Node retrievalNode = new TaskExecuteDag.Node();
    retrievalNode.setTaskComponent("retrievalSyncTask");
    nodes.add(retrievalNode);

    // Node 2: Scanner
    TaskExecuteDag.Node scannerNode = new TaskExecuteDag.Node();
    scannerNode.setTaskComponent("kagScannerSyncTask");
    nodes.add(scannerNode);

    // Node 3: Reader
    TaskExecuteDag.Node readerNode = new TaskExecuteDag.Node();
    readerNode.setTaskComponent("kagReaderSyncTask");
    nodes.add(readerNode);

    // ... continues with other tasks

    // Define dependencies (edges)
    edges.add(new Edge(scannerNode, readerNode));
    edges.add(new Edge(readerNode, splitterNode));
    edges.add(new Edge(splitterNode, extractorNode));
    // ... etc

    return new TaskExecuteDag(nodes, edges);
}
```

---

## 3. IndexType Schema Integration

### 3.1 What is IndexType?

`IndexType` is a special SPG schema type for storing index metadata:

**Class Definition:**
```java
// Location: server/core/schema/model/.../IndexType.java
public class IndexType extends BaseAdvancedType {
    public IndexType(
        BasicInfo<SPGTypeIdentifier> basicInfo,
        ParentTypeInfo parentTypeInfo,
        List<Property> properties,
        List<Relation> relations,
        SPGTypeAdvancedConfig advancedConfig
    ) {
        super(basicInfo, parentTypeInfo, SPGTypeEnum.INDEX_TYPE,
              properties, relations, advancedConfig);
    }
}
```

### 3.2 Index Types

Common index types in KAG:

1. **Chunk2QueryIndex** - Maps chunks to potential queries
2. **SummaryIndex** - Document summaries
3. **VectorIndex** - Embedding vectors
4. **FullTextIndex** - Text search indices

### 3.3 Schema Example

**Define an index type:**
```python
# Python equivalent
from openspg.core.schema.types import IndexType, BasicInfo, SPGTypeIdentifier

chunk_index = IndexType(
    basic_info=BasicInfo(
        identifier=SPGTypeIdentifier(name="Chunk2QueryIndex"),
        description="Maps document chunks to queries"
    ),
    properties=[
        Property(name="chunkId", type="String"),
        Property(name="content", type="Text"),
        Property(name="summary", type="Text"),
        Property(name="vectorId", type="String"),
        Property(name="entityRefs", type="List[String]")
    ],
    relations=[
        Relation(
            name="extractedFrom",
            source="Chunk2QueryIndex",
            target="Document"
        )
    ]
)
```

### 3.4 Storage in Graph

IndexType instances are stored as vertices in the graph:

```cypher
// Memgraph/Neo4j representation
CREATE (idx:Chunk2QueryIndex {
    id: "chunk_123",
    chunkId: "chunk_123",
    content: "Full text content...",
    summary: "Summary of chunk...",
    vectorId: "vec_456",
    entityRefs: ["Entity_1", "Entity_2"]
})

// Relation to source document
CREATE (doc:Document {id: "doc_789"})
CREATE (idx)-[:extractedFrom]->(doc)
```

---

## 4. Data Models

### 4.1 ChunkRecord

**Purpose:** Represents a document chunk after splitting.

**Java Definition:**
```java
// Location: builder/model/.../ChunkRecord.java
public class ChunkRecord extends BaseRecord {
    private final Chunk chunk;

    public static class Chunk {
        private final String header;      // Document header/title
        private final String name;        // Chunk name
        private final String id;          // Unique chunk ID
        private final String content;     // Chunk text content
        private final String type;        // Chunk type (paragraph, heading, etc.)
        private final String summary;     // LLM-generated summary
        private final String textIndex;   // Text index reference
        private final String vecIndex;    // Vector index reference

        public String getShortId() {
            return id.substring(0, 6);  // First 6 chars for display
        }
    }
}
```

**Python Equivalent:**
```python
from dataclasses import dataclass
from typing import Optional

@dataclass
class Chunk:
    header: str
    name: str
    id: str
    content: str
    type: str  # 'paragraph', 'heading', 'table', etc.
    summary: Optional[str] = None
    text_index: Optional[str] = None
    vec_index: Optional[str] = None

    def get_short_id(self) -> str:
        return self.id[:6]

@dataclass
class ChunkRecord:
    chunk: Chunk

    def to_dict(self):
        return {
            "chunk": {
                "header": self.chunk.header,
                "name": self.chunk.name,
                "id": self.chunk.id,
                "content": self.chunk.content,
                "type": self.chunk.type,
                "summary": self.chunk.summary,
                "textIndex": self.chunk.text_index,
                "vecIndex": self.chunk.vec_index
            }
        }
```

### 4.2 SubGraphRecord

**Purpose:** Represents extracted knowledge graph from a chunk.

**Structure:**
```python
@dataclass
class SubGraphRecord:
    """
    Knowledge subgraph extracted from a chunk

    Contains:
    - Entities extracted from chunk
    - Relations between entities
    - Properties of entities
    - Link back to source chunk
    """
    chunk_id: str
    entities: List[Entity]
    relations: List[Relation]
    source_doc_id: str
    confidence: float

    @dataclass
    class Entity:
        id: str
        type: str  # Entity type (Person, Organization, etc.)
        name: str
        properties: Dict[str, Any]
        mention_text: str  # Text span in chunk
        start_offset: int
        end_offset: int

    @dataclass
    class Relation:
        source_id: str
        target_id: str
        relation_type: str
        properties: Dict[str, Any]
        confidence: float
```

**Example:**
```python
# From chunk: "Apple Inc. was founded by Steve Jobs in 1976."
subgraph = SubGraphRecord(
    chunk_id="chunk_123",
    source_doc_id="doc_789",
    entities=[
        Entity(
            id="ent_1",
            type="Organization",
            name="Apple Inc.",
            properties={"industry": "Technology"},
            mention_text="Apple Inc.",
            start_offset=0,
            end_offset=10
        ),
        Entity(
            id="ent_2",
            type="Person",
            name="Steve Jobs",
            properties={"role": "Founder"},
            mention_text="Steve Jobs",
            start_offset=26,
            end_offset=36
        )
    ],
    relations=[
        Relation(
            source_id="ent_2",
            target_id="ent_1",
            relation_type="foundedBy",
            properties={"year": 1976},
            confidence=0.95
        )
    ],
    confidence=0.92
)
```

---

## 5. Builder Pipeline Tasks

### 5.1 Task: Splitter

**Purpose:** Split documents into manageable chunks.

**Implementation Points:**

**Java Task Handler:**
```java
// Location: server/core/scheduler/service/.../KagSplitterAsyncTask.java
@Component("kagSplitterAsyncTask")
public class KagSplitterAsyncTask extends AsyncTaskExecuteTemplate {

    @Override
    public String submit(TaskExecuteContext context) {
        // 1. Get input documents from previous task
        List<String> inputs = SchedulerUtils.getTaskInputs(taskService, instance, task);

        // 2. Submit to thread pool for async execution
        String taskId = memoryTaskServer.submit(
            new SplitterTaskCallable(..., inputs),
            key,
            instance.getId()
        );

        return taskId;
    }

    // Callable that does actual work
    class SplitterTaskCallable implements Callable<String> {
        @Override
        public String call() {
            // 3. Call Python splitter via Pemja
            PythonInvokeMethod method = new PythonInvokeMethod(
                "kag.splitter",  // Python module
                "split_document" // Python function
            );

            Map<String, Object> params = Maps.newHashMap();
            params.put("documents", documents);
            params.put("chunk_size", 512);
            params.put("overlap", 50);

            // 4. Execute Python call
            String result = PemjaUtils.invoke(pemjaConfig, method, params);

            // 5. Parse result as ChunkRecord[]
            List<ChunkRecord> chunks = JSON.parseArray(result, ChunkRecord.class);

            // 6. Write chunks to object storage
            String outputPath = writeToObjectStorage(chunks);

            return outputPath;
        }
    }
}
```

**Python Splitter Implementation:**
```python
# KAG side implementation (external to OpenSPG)
def split_document(documents, chunk_size=512, overlap=50):
    """
    Split documents into chunks

    Called by OpenSPG via Pemja bridge

    Args:
        documents: List of document dicts
        chunk_size: Target chunk size in tokens
        overlap: Overlap between chunks

    Returns:
        JSON array of ChunkRecord objects
    """
    from langchain.text_splitter import RecursiveCharacterTextSplitter

    splitter = RecursiveCharacterTextSplitter(
        chunk_size=chunk_size,
        chunk_overlap=overlap,
        separators=["\n\n", "\n", ". ", " ", ""]
    )

    chunks = []
    for doc in documents:
        text_chunks = splitter.split_text(doc['content'])

        for i, chunk_text in enumerate(text_chunks):
            chunk = {
                "chunk": {
                    "header": doc.get('header', ''),
                    "name": f"{doc['name']}_chunk_{i}",
                    "id": f"{doc['id']}_chunk_{i}",
                    "content": chunk_text,
                    "type": "paragraph",
                    "summary": None,  # Will be filled by extractor
                    "textIndex": None,
                    "vecIndex": None
                }
            }
            chunks.append(chunk)

    return json.dumps(chunks)
```

### 5.2 Task: Extractor

**Purpose:** Extract entities and relations from chunks using LLM.

**Java Task Handler:**
```java
@Component("kagExtractorAsyncTask")
public class KagExtractorAsyncTask extends AsyncTaskExecuteTemplate {

    @Override
    public String submit(TaskExecuteContext context) {
        // Get LLM configuration
        String llmId = task.getConfig().get("llm_id");
        String extractorConfig = task.getConfig().get("config");

        // Submit extraction job
        return executorMap.get(llmId).submit(() -> {
            // Call Python extractor
            PythonInvokeMethod method = new PythonInvokeMethod(
                "kag.extractor",
                "extract_knowledge"
            );

            Map<String, Object> params = Maps.newHashMap();
            params.put("chunks", chunks);
            params.put("llm_config", extractorConfig);
            params.put("schema", schemaContext);

            String result = PemjaUtils.invoke(pemjaConfig, method, params);

            // Parse as SubGraphRecord[]
            List<SubGraphRecord> subgraphs = JSON.parseArray(result, SubGraphRecord.class);

            return writeToObjectStorage(subgraphs);
        });
    }
}
```

**Python Extractor Implementation:**
```python
from openai import OpenAI
from typing import List, Dict

def extract_knowledge(chunks: List[Dict], llm_config: Dict, schema: Dict) -> str:
    """
    Extract entities and relations using LLM

    Args:
        chunks: List of ChunkRecord dicts
        llm_config: LLM configuration (model, temperature, etc.)
        schema: SPG schema context for extraction

    Returns:
        JSON array of SubGraphRecord objects
    """
    client = OpenAI(api_key=llm_config['api_key'])

    # Build extraction prompt
    entity_types = ", ".join(schema['entity_types'])
    relation_types = ", ".join(schema['relation_types'])

    prompt_template = f"""
    Extract entities and relations from the following text.

    Entity types: {entity_types}
    Relation types: {relation_types}

    Text: {{chunk_content}}

    Output format:
    {{
        "entities": [
            {{"id": "...", "type": "...", "name": "...", "properties": {{...}}}}
        ],
        "relations": [
            {{"source_id": "...", "target_id": "...", "type": "...", "properties": {{...}}}}
        ]
    }}
    """

    subgraphs = []
    for chunk_record in chunks:
        chunk = chunk_record['chunk']

        # Call LLM
        response = client.chat.completions.create(
            model=llm_config['model'],
            messages=[
                {"role": "system", "content": "You are a knowledge extraction expert."},
                {"role": "user", "content": prompt_template.format(chunk_content=chunk['content'])}
            ],
            temperature=llm_config.get('temperature', 0.1)
        )

        # Parse LLM output
        extracted = json.loads(response.choices[0].message.content)

        subgraph = {
            "chunkId": chunk['id'],
            "sourceDocId": chunk['header'],
            "entities": extracted['entities'],
            "relations": extracted['relations'],
            "confidence": 0.9  # Could be computed from LLM scores
        }
        subgraphs.append(subgraph)

    return json.dumps(subgraphs)
```

### 5.3 Task: Vectorizer

**Purpose:** Generate embeddings for chunks.

**Java Task Handler:**
```java
@Component("kagVectorizerAsyncTask")
public class KagVectorizerAsyncTask extends AsyncTaskExecuteTemplate {

    @Override
    public String submit(TaskExecuteContext context) {
        return executor.submit(() -> {
            // Call Python embedder
            PythonInvokeMethod method = new PythonInvokeMethod(
                "kag.vectorizer",
                "generate_embeddings"
            );

            Map<String, Object> params = Maps.newHashMap();
            params.put("chunks", chunks);
            params.put("model", "text-embedding-ada-002");

            String result = PemjaUtils.invoke(pemjaConfig, method, params);

            // Result: chunks with populated vecIndex field
            return result;
        });
    }
}
```

**Python Vectorizer:**
```python
from openai import OpenAI
import numpy as np

def generate_embeddings(chunks: List[Dict], model: str = "text-embedding-ada-002") -> str:
    """
    Generate embeddings for chunks

    Args:
        chunks: List of ChunkRecord dicts
        model: Embedding model name

    Returns:
        Updated chunks with vecIndex populated
    """
    client = OpenAI()

    for chunk_record in chunks:
        chunk = chunk_record['chunk']

        # Generate embedding
        response = client.embeddings.create(
            model=model,
            input=chunk['content']
        )

        embedding = response.data[0].embedding

        # Store embedding (could be in vector DB)
        vec_id = store_embedding(chunk['id'], embedding)

        # Update chunk with vector reference
        chunk['vecIndex'] = vec_id

    return json.dumps(chunks)

def store_embedding(chunk_id: str, embedding: List[float]) -> str:
    """Store embedding in vector database"""
    # Implementation depends on vector DB
    # Could be Pinecone, Weaviate, Milvus, etc.
    pass
```

### 5.4 Task: Alignment

**Purpose:** Align extracted entities with existing knowledge graph.

**Key Functions:**
- Entity resolution (same entity, different names)
- Entity linking (link mentions to canonical entities)
- Confidence scoring
- Conflict resolution

**Python Implementation:**
```python
def align_entities(subgraphs: List[Dict], existing_kg: Dict) -> str:
    """
    Align extracted entities with existing KG

    Steps:
    1. For each extracted entity, search for matches in KG
    2. Compute similarity scores
    3. Link if similarity > threshold
    4. Create new entity if no match

    Args:
        subgraphs: SubGraphRecord dicts
        existing_kg: Existing KG context

    Returns:
        Aligned SubGraphRecord dicts with entity IDs resolved
    """
    for subgraph in subgraphs:
        for entity in subgraph['entities']:
            # Search existing KG
            candidates = search_existing_entities(
                name=entity['name'],
                type=entity['type'],
                kg=existing_kg
            )

            if candidates:
                # Compute similarity
                best_match = max(candidates, key=lambda c: compute_similarity(entity, c))

                if best_match['similarity'] > 0.8:
                    # Link to existing entity
                    entity['id'] = best_match['id']
                    entity['is_new'] = False
                else:
                    # Create new entity
                    entity['id'] = generate_new_id()
                    entity['is_new'] = True
            else:
                # No candidates, create new
                entity['id'] = generate_new_id()
                entity['is_new'] = True

    return json.dumps(subgraphs)
```

---

## 6. Python Operator Integration

### 6.1 Pemja Bridge

OpenSPG uses **Pemja** (Python Embedded in Java) to call Python code from Java.

**Configuration:**
```java
// PemjaConfig setup
PemjaConfig config = new PemjaConfig();
config.setPythonPath("/path/to/kag/python/modules");
config.setPythonLibPath("/path/to/python/lib");

// Initialize Pemja
PythonInterpreter interpreter = PemjaUtils.createInterpreter(config);
```

**Calling Python:**
```java
// Define Python method to call
PythonInvokeMethod method = new PythonInvokeMethod(
    "kag.module_name",    // Python module
    "function_name"       // Python function
);

// Prepare parameters
Map<String, Object> params = Maps.newHashMap();
params.put("param1", value1);
params.put("param2", value2);

// Invoke
String result = PemjaUtils.invoke(config, method, params);
```

### 6.2 KAG Python Module Structure

**Expected structure on KAG side:**
```
kag/
├── __init__.py
├── splitter.py          # split_document()
├── extractor.py         # extract_knowledge()
├── vectorizer.py        # generate_embeddings()
├── aligner.py           # align_entities()
└── utils/
    ├── llm_client.py
    └── vector_store.py
```

### 6.3 Interface Contract

**All KAG Python functions must:**

1. **Accept JSON-serializable parameters**
   ```python
   def function_name(param1: Dict, param2: List) -> str:
       pass
   ```

2. **Return JSON string**
   ```python
   return json.dumps(result)
   ```

3. **Handle exceptions gracefully**
   ```python
   try:
       result = do_work()
       return json.dumps({"success": True, "data": result})
   except Exception as e:
       return json.dumps({"success": False, "error": str(e)})
   ```

4. **Support configuration via parameters**
   ```python
   def extract_knowledge(chunks, llm_config, schema):
       model = llm_config.get('model', 'gpt-4')
       # ...
   ```

---

## 7. Storage Integration

### 7.1 Object Storage

**Purpose:** Temporary storage for intermediate results (chunks, vectors, subgraphs).

**Java Integration:**
```java
// Get object storage client
ObjectStorageClient client = ObjectStorageClientDriverManager.getClient(storageUrl);

// Write chunks to storage
String path = "projects/{projectId}/instances/{instanceId}/chunks/{taskId}.json";
client.putObject(bucketName, path, JSON.toJSONString(chunks));

// Read from storage
String content = client.getObject(bucketName, path);
List<ChunkRecord> chunks = JSON.parseArray(content, ChunkRecord.class);

// Clean up after job completes
client.removeObject(bucketName, path);
```

**Supported Backends:**
- **MinIO** (S3-compatible)
- **Alibaba OSS**
- **AWS S3**
- **Local filesystem** (for testing)

### 7.2 Graph Store

**Purpose:** Persistent storage for entities, relations, and index metadata.

**Data Written:**
```cypher
// 1. Index vertex (IndexType instance)
CREATE (idx:Chunk2QueryIndex {
    id: "chunk_123",
    content: "...",
    summary: "...",
    vectorId: "vec_456"
})

// 2. Extracted entities
CREATE (e1:Person {id: "ent_1", name: "Steve Jobs"})
CREATE (e2:Organization {id: "ent_2", name: "Apple Inc."})

// 3. Relations
CREATE (e1)-[:foundedBy {year: 1976}]->(e2)

// 4. Link to index
CREATE (e1)-[:mentionedIn]->(idx)
CREATE (e2)-[:mentionedIn]->(idx)

// 5. Link to source document
CREATE (doc:Document {id: "doc_789"})
CREATE (idx)-[:extractedFrom]->(doc)
```

### 7.3 Vector Store

**Purpose:** Store and retrieve embeddings.

**Integration Points:**
- Embeddings stored in **separate vector database** (Pinecone, Weaviate, Milvus)
- **Reference stored in graph:** `Chunk2QueryIndex.vectorId = "vec_456"`
- **Retrieval service** coordinates between graph and vector store

---

## 8. Retrieval Service Integration

### 8.1 Purpose

The **Retrieval Service** manages search indices and coordinates queries.

**Java Interface:**
```java
public interface RetrievalService {
    // Create index
    Long createIndex(String indexName, String indexType, Map<String, Object> config);

    // Add documents to index
    void addDocuments(Long indexId, List<Document> documents);

    // Search
    List<SearchResult> search(Long indexId, String query, int topK);

    // Hybrid search (text + vector)
    List<SearchResult> hybridSearch(Long indexId, String query, float[] vector, int topK);
}
```

### 8.2 Index Types

1. **Text Index** (Elasticsearch)
   - Full-text search
   - BM25 ranking
   - Keyword matching

2. **Vector Index** (Vector DB)
   - Semantic search
   - Cosine similarity
   - ANN (Approximate Nearest Neighbor)

3. **Hybrid Index**
   - Combines text + vector
   - Weighted fusion
   - Re-ranking

### 8.3 Query Flow

```
User Query
    ↓
[1. Query Understanding]
    - Intent classification
    - Entity extraction
    ↓
[2. Retrieval Service]
    - Text search (BM25)
    - Vector search (embedding similarity)
    - Hybrid fusion
    ↓
[3. Graph Contextualization]
    - For each retrieved chunk, fetch:
      - Source document
      - Extracted entities (via mentionedIn)
      - Related entities (1-hop neighbors)
      - Subgraph context
    ↓
[4. Re-ranking]
    - Relevance scoring
    - Diversity
    - Recency
    ↓
[5. Context Assembly]
    - Top-K chunks + graph context
    ↓
LLM Prompt
```

### 8.4 Python Integration

```python
# KAG Python side - Retrieval interface
class KAGRetriever:
    def __init__(self, openspg_client, vector_store):
        self.openspg = openspg_client
        self.vector_store = vector_store

    def retrieve(self, query: str, top_k: int = 5) -> List[Dict]:
        """
        Hybrid retrieval from OpenSPG

        Returns:
            List of contexts with chunks + graph data
        """
        # 1. Generate query embedding
        query_embedding = self.generate_embedding(query)

        # 2. Vector search
        vector_results = self.vector_store.search(query_embedding, top_k=top_k*2)

        # 3. For each result, get graph context from OpenSPG
        contexts = []
        for result in vector_results:
            chunk_id = result['chunk_id']

            # Query OpenSPG for graph context
            kgdsl_query = f"""
            GraphStructure {{
                (chunk:Chunk2QueryIndex where id='{chunk_id}'),
                (chunk)-[:mentionedIn]-(entity:Entity),
                (entity)-[rel]-(related:Entity)
            }}
            Rule {{}}
            Action {{
                get(chunk.content, chunk.summary, entity.name, rel.type, related.name)
            }}
            """

            graph_context = self.openspg.execute_query(kgdsl_query)

            contexts.append({
                'chunk_id': chunk_id,
                'content': result['content'],
                'score': result['score'],
                'entities': graph_context['entities'],
                'relations': graph_context['relations']
            })

        # 4. Re-rank
        contexts = self.rerank(contexts, query)

        return contexts[:top_k]
```

---

## 9. API Integration Points

### 9.1 KAG Builder Request

**HTTP Endpoint:**
```
POST /api/v1/builder/kag
```

**Request Model:**
```java
// Location: server/api/facade/.../KagBuilderRequest.java
public class KagBuilderRequest extends BaseRequest {
    private Long projectId;
    private String userNumber;
    private String command;           // KAG command (build, index, etc.)
    private String image;             // Docker image for KAG workers
    private String workerPool;        // Worker pool name
    private Integer workerNum;        // Number of workers
    private Double workerCpu;         // CPU per worker
    private Integer workerGpu;        // GPU count
    private String workerGpuType;     // GPU type
    private Integer workerMemory;     // Memory in MB
    private Integer workerStorage;    // Storage in GB
    private Map<String, String> envs; // Environment variables
}
```

**Python Client Example:**
```python
import requests

def submit_kag_job(
    project_id: int,
    documents: List[str],
    llm_config: Dict,
    openspg_url: str = "http://localhost:8080"
):
    """Submit KAG building job to OpenSPG"""

    request = {
        "projectId": project_id,
        "command": "build",
        "workerNum": 4,
        "workerCpu": 2.0,
        "workerMemory": 8192,
        "envs": {
            "LLM_API_KEY": llm_config['api_key'],
            "LLM_MODEL": llm_config['model'],
            "DOCUMENTS": ",".join(documents)
        }
    }

    response = requests.post(
        f"{openspg_url}/api/v1/builder/kag",
        json=request
    )

    job_id = response.json()['jobId']
    return job_id
```

### 9.2 Query API

**Endpoint:**
```
POST /api/v1/query
```

**With KAG Context:**
```python
# Query that leverages KAG indices
kgdsl_query = """
GraphStructure {
    (idx:Chunk2QueryIndex),
    (idx)-[:mentionedIn]-(entity:Entity),
    (entity)-[rel]-(related:Entity)
}
Rule {
    R1: idx.summary like '%artificial intelligence%'
    entityCount = group(idx).count(entity)
}
Action {
    get(idx.content, idx.summary, entityCount, entity.name)
}
"""

response = requests.post(
    f"{openspg_url}/api/v1/query",
    json={
        "query": kgdsl_query,
        "parameters": {}
    }
)

results = response.json()['results']
```

---

## 10. Implementation Guide

### 10.1 Integrating Your KAG System

**Step 1: Implement Python Modules**

Create KAG Python modules with required functions:

```python
# kag/splitter.py
def split_document(documents, chunk_size, overlap):
    """Split documents into chunks"""
    # Your implementation
    return json.dumps(chunk_records)

# kag/extractor.py
def extract_knowledge(chunks, llm_config, schema):
    """Extract entities/relations from chunks"""
    # Your implementation
    return json.dumps(subgraphs)

# kag/vectorizer.py
def generate_embeddings(chunks, model):
    """Generate embeddings"""
    # Your implementation
    return json.dumps(updated_chunks)

# kag/aligner.py
def align_entities(subgraphs, existing_kg):
    """Align with existing KG"""
    # Your implementation
    return json.dumps(aligned_subgraphs)
```

**Step 2: Configure OpenSPG**

Set Pemja configuration to point to your Python modules:

```properties
# application.properties
kag.python.path=/path/to/your/kag/modules
kag.python.lib=/usr/lib/python3.10
```

**Step 3: Define IndexType Schema**

```python
from openspg_client import OpenSPGClient

client = OpenSPGClient(url="http://localhost:8080")

# Create Chunk2QueryIndex type
client.create_schema_type({
    "typeName": "Chunk2QueryIndex",
    "typeCategory": "INDEX_TYPE",
    "properties": [
        {"name": "chunkId", "type": "String"},
        {"name": "content", "type": "Text"},
        {"name": "summary", "type": "Text"},
        {"name": "vectorId", "type": "String"}
    ],
    "relations": [
        {
            "name": "extractedFrom",
            "source": "Chunk2QueryIndex",
            "target": "Document"
        },
        {
            "name": "mentionedIn",
            "source": "Entity",
            "target": "Chunk2QueryIndex"
        }
    ]
})
```

**Step 4: Submit KAG Job**

```python
job_id = client.submit_kag_job(
    project_id=1,
    documents=["doc1.pdf", "doc2.pdf"],
    llm_config={
        "model": "gpt-4",
        "api_key": "sk-...",
        "temperature": 0.1
    }
)

# Poll for completion
status = client.get_job_status(job_id)
```

**Step 5: Query Indexed Knowledge**

```python
# Search with graph context
results = client.execute_query("""
    GraphStructure {
        (idx:Chunk2QueryIndex),
        (idx)-[:mentionedIn]-(entity:Entity)
    }
    Rule {
        R1: idx.summary like '%machine learning%'
    }
    Action {
        get(idx.content, entity.name)
    }
""")
```

### 10.2 Testing Integration

**Unit Test:**
```python
import pytest
from kag.splitter import split_document

def test_splitter():
    documents = [{
        "id": "doc_1",
        "name": "test.txt",
        "content": "Long document content..." * 100
    }]

    result = split_document(documents, chunk_size=512, overlap=50)
    chunks = json.loads(result)

    assert len(chunks) > 1
    assert chunks[0]['chunk']['id'] == "doc_1_chunk_0"
    assert len(chunks[0]['chunk']['content']) <= 512
```

**Integration Test:**
```python
def test_kag_pipeline():
    # 1. Submit documents
    docs = load_test_documents()

    # 2. Split
    chunks = split_document(docs, 512, 50)

    # 3. Extract
    subgraphs = extract_knowledge(chunks, llm_config, schema)

    # 4. Align
    aligned = align_entities(subgraphs, existing_kg)

    # 5. Vectorize
    vectorized = generate_embeddings(chunks, "ada-002")

    # 6. Verify
    assert all('vecIndex' in chunk for chunk in json.loads(vectorized))
```

---

## 11. Summary

### Key Integration Points

1. **Schema Integration**
   - Use `IndexType` for index metadata
   - Store chunks as graph vertices
   - Link entities to chunks via `mentionedIn` relation

2. **Builder Pipeline**
   - 8-stage pipeline (Scanner → Writer)
   - Async tasks with thread pools
   - Object storage for intermediate results

3. **Python Bridge**
   - Pemja for Java-Python communication
   - JSON serialization for data exchange
   - 4 core functions: split, extract, align, vectorize

4. **Data Models**
   - `ChunkRecord` for document chunks
   - `SubGraphRecord` for extracted knowledge
   - Standard JSON format for interoperability

5. **Storage**
   - Graph store for entities/relations
   - Vector store for embeddings
   - Object storage for temp data

6. **Retrieval**
   - Hybrid search (text + vector)
   - Graph-enhanced context
   - Retrieval service coordination

### Implementation Checklist

- [ ] Implement 4 Python modules (splitter, extractor, aligner, vectorizer)
- [ ] Configure Pemja bridge
- [ ] Define IndexType schema in OpenSPG
- [ ] Set up object storage
- [ ] Configure vector database
- [ ] Implement retrieval service
- [ ] Create API client
- [ ] Test end-to-end pipeline

---

**Document Version:** 1.0
**Last Updated:** 2025-11-05
**For Questions:** Refer to OpenSPG documentation and KAG paper

This guide provides everything needed to integrate a KAG system with OpenSPG from the OpenSPG side.
