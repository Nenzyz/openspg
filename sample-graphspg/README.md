# GraphSPG - Graph Semantic Processing

A simplified graph processing system inspired by OpenSPG, demonstrating pattern-based knowledge graph querying with Memgraph.

## Features

- **Simplified DSL**: Pattern-based query language for graph traversal
- **Schema System**: Define and validate entity types and relations
- **Memgraph Integration**: High-performance graph database backend
- **REST API**: FastAPI-based REST interface
- **Cypher Compilation**: Transparent DSL to Cypher translation
- **Docker Ready**: Easy deployment with Docker Compose

## Architecture

```
┌─────────────────────────────────────────────────┐
│              FastAPI REST API                    │
│  /api/v1/query  /api/v1/entities  /api/v1/schemas│
└─────────────────────┬───────────────────────────┘
                      │
┌─────────────────────▼───────────────────────────┐
│            Query Executor                        │
│  - DSL Parser                                    │
│  - AST Builder                                   │
│  - Cypher Compiler                               │
└─────────────────────┬───────────────────────────┘
                      │
┌─────────────────────▼───────────────────────────┐
│         Memgraph Adapter                         │
│  - Connection Management                         │
│  - CRUD Operations                               │
│  - Query Execution                               │
└─────────────────────┬───────────────────────────┘
                      │
                ┌─────▼─────┐
                │  Memgraph │
                │  Database │
                └───────────┘
```

## Quick Start

### Prerequisites

- Docker and Docker Compose
- Python 3.10+ (for local development)
- Poetry (optional, for dependency management)

### Using Docker Compose

1. **Clone and navigate to the project:**
   ```bash
   cd sample-graphspg
   ```

2. **Start the services:**
   ```bash
   docker-compose up -d
   ```

   This starts:
   - Memgraph database on port 7687 (Bolt) and 3000 (Lab UI)
   - GraphSPG API on port 8000

3. **Load sample data:**
   ```bash
   docker-compose exec graphspg-api python examples/social_network.py
   ```

4. **Access the services:**
   - API Documentation: http://localhost:8000/docs
   - Memgraph Lab: http://localhost:3000
   - Health Check: http://localhost:8000/health

### Local Development

1. **Install dependencies:**
   ```bash
   poetry install
   ```

2. **Start Memgraph:**
   ```bash
   docker run -p 7687:7687 -p 3000:3000 memgraph/memgraph-platform
   ```

3. **Set environment variables:**
   ```bash
   cp .env.example .env
   # Edit .env if needed
   ```

4. **Load sample data:**
   ```bash
   python examples/social_network.py
   ```

5. **Run the API:**
   ```bash
   uvicorn graphspg.api.main:app --reload
   ```

## DSL Query Language

### Syntax

The DSL supports pattern-based graph queries:

```
MATCH <pattern> [WHERE <condition>] [RETURN <items>]
```

**Pattern syntax:**
- Nodes: `(variable:Label {property: value})`
- Edges: `-[variable:TYPE]->` (directed) or `-[variable:TYPE]-` (undirected)
- Reverse: `<-[variable:TYPE]-`

**Operators:**
- Comparison: `=`, `!=`, `>`, `>=`, `<`, `<=`
- Logical: `AND`, `OR`
- Membership: `IN`

### Example Queries

**1. Find users who follow Alice:**
```
MATCH (u:User)-[:FOLLOWS]->(alice:User)
WHERE alice.name = 'Alice Johnson'
RETURN u.name, u.city
```

**2. Find users older than 30:**
```
MATCH (u:User)
WHERE u.age > 30
RETURN u.name, u.age, u.city
```

**3. Find mutual followers:**
```
MATCH (a:User)-[:FOLLOWS]->(b:User)-[:FOLLOWS]->(a)
RETURN a.name, b.name
```

**4. Complex pattern:**
```
MATCH (u:User)-[:FOLLOWS]->(f:User)-[:MEMBER_OF]->(g:Group)
WHERE g.name = 'AI Enthusiasts'
RETURN u.name, f.name, g.name
```

## REST API

### Query Execution

**Execute DSL Query:**
```bash
curl -X POST http://localhost:8000/api/v1/query \
  -H "Content-Type: application/json" \
  -d '{
    "query": "MATCH (u:User) WHERE u.age > 30 RETURN u.name, u.age"
  }'
```

**Execute Cypher Query:**
```bash
curl -X POST http://localhost:8000/api/v1/query/cypher \
  -H "Content-Type: application/json" \
  -d '{
    "query": "MATCH (u:User) WHERE u.age > 30 RETURN u.name, u.age"
  }'
```

**Compile DSL to Cypher:**
```bash
curl -X POST http://localhost:8000/api/v1/compile \
  -H "Content-Type: application/json" \
  -d '{
    "query": "MATCH (u:User) WHERE u.age > 30 RETURN u.name"
  }'
```

### Entity Management

**Create Entity:**
```bash
curl -X POST http://localhost:8000/api/v1/entities \
  -H "Content-Type: application/json" \
  -d '{
    "entity_type": "User",
    "properties": {
      "name": "John Doe",
      "age": 35,
      "email": "john@example.com",
      "city": "Boston"
    }
  }'
```

**Get Entity:**
```bash
curl http://localhost:8000/api/v1/entities/{entity_id}
```

**Create Relation:**
```bash
curl -X POST http://localhost:8000/api/v1/relations \
  -H "Content-Type: application/json" \
  -d '{
    "source_id": "user1",
    "target_id": "user2",
    "relation_type": "FOLLOWS"
  }'
```

### Schema Management

**List Schemas:**
```bash
curl http://localhost:8000/api/v1/schemas
```

**Get Schema Details:**
```bash
curl http://localhost:8000/api/v1/schemas/social_network
```

## Project Structure

```
sample-graphspg/
├── graphspg/                # Main package
│   ├── api/                 # FastAPI application
│   │   ├── main.py          # API routes and app
│   │   └── models.py        # Request/response models
│   ├── dsl/                 # DSL parser
│   │   ├── ast.py           # AST node definitions
│   │   └── parser.py        # DSL parser
│   ├── engine/              # Query engine
│   │   ├── compiler.py      # DSL to Cypher compiler
│   │   └── executor.py      # Query executor
│   ├── schema/              # Schema system
│   │   ├── models.py        # Schema models
│   │   └── registry.py      # Schema registry
│   ├── storage/             # Storage layer
│   │   ├── base.py          # Storage interface
│   │   └── memgraph.py      # Memgraph adapter
│   └── utils/               # Utilities
│       └── config.py        # Configuration
├── examples/                # Example scripts
│   ├── social_network.py    # Sample data loader
│   └── queries.py           # Example queries
├── tests/                   # Tests
├── docker-compose.yml       # Docker Compose config
├── Dockerfile               # Docker image
├── pyproject.toml           # Poetry dependencies
└── README.md                # This file
```

## Sample Domain: Social Network

The included example demonstrates a social network with:

### Entity Types
- **User**: Social network users with profiles
- **Post**: User-generated content
- **Group**: Communities and interest groups

### Relations
- **FOLLOWS**: User follows another user
- **POSTED**: User posted content
- **MEMBER_OF**: User is member of a group
- **LIKES**: User likes a post

### Sample Data
- 5 users (Alice, Bob, Carol, David, Emma)
- 3 groups (AI Enthusiasts, Graph Database Users, San Francisco Tech)
- 3 posts with varying engagement
- Multiple relationships demonstrating various patterns

## Running Example Queries

Execute the example queries script:

```bash
# Using Docker
docker-compose exec graphspg-api python examples/queries.py

# Local development
python examples/queries.py
```

This runs 11 example queries demonstrating:
- Simple pattern matching
- Property filtering
- Multi-hop traversals
- Mutual relationships
- Complex patterns
- Raw Cypher queries
- Aggregations
- Friend recommendations

## Development

### Adding New Features

1. **New DSL Keywords**: Extend `ast.py` and `parser.py`
2. **Custom Storage**: Implement `StorageAdapter` interface
3. **Schema Validation**: Enhance `SchemaAwareExecutor`
4. **API Endpoints**: Add routes in `api/main.py`

### Testing

```bash
# Run tests
poetry run pytest

# Run with coverage
poetry run pytest --cov=graphspg
```

## Comparison with OpenSPG

| Feature | GraphSPG (This Project) | OpenSPG |
|---------|------------------------|---------|
| Language | Python | Scala/Java |
| Database | Memgraph | TuGraph/Neo4j |
| DSL | Simplified pattern matching | Full KGDSL with ANTLR4 |
| Schema | Pydantic models | SPG Schema (LPG+RDF) |
| Reasoner | Direct Cypher compilation | Block IR + optimization |
| Builder | Basic CRUD | Full pipeline with operators |
| KAG Integration | Not included | Integrated via Pemja |

## Performance

- **Query Parsing**: < 1ms for typical queries
- **Cypher Compilation**: < 1ms
- **Query Execution**: Depends on Memgraph (typically < 10ms for simple patterns)
- **API Response Time**: < 50ms end-to-end for cached connections

## Troubleshooting

### Connection Issues

**"Failed to connect to Memgraph":**
- Ensure Memgraph is running: `docker ps | grep memgraph`
- Check connection URI in `.env` or environment variables
- Verify port 7687 is accessible

### Query Errors

**"Parse error at position X":**
- Check DSL syntax (parentheses, colons, brackets)
- Ensure proper spacing around operators
- Verify label and property names match schema

**"Unknown entity type":**
- Load schema first: `python examples/social_network.py`
- Check schema is registered: `GET /api/v1/schemas`

### Docker Issues

**"Port already in use":**
- Stop conflicting services or change ports in `docker-compose.yml`
- Common conflicts: 7687 (Neo4j), 8000 (other APIs)

## Future Enhancements

- [ ] Full ANTLR4-based KGDSL parser
- [ ] Block IR intermediate representation
- [ ] Query optimization and planning
- [ ] Rule-based reasoning (DEFINE statements)
- [ ] Distributed query execution
- [ ] GraphQL interface
- [ ] Real-time streaming queries
- [ ] Schema evolution and migration tools
- [ ] Advanced aggregations in DSL
- [ ] Path finding algorithms

## License

MIT License - feel free to use this for learning and experimentation.

## References

- [OpenSPG](https://github.com/OpenSPG/openspg) - The original inspiration
- [Memgraph](https://memgraph.com/) - High-performance graph database
- [FastAPI](https://fastapi.tiangolo.com/) - Modern Python web framework
- [Cypher Query Language](https://neo4j.com/developer/cypher/) - Graph query language

## Contributing

This is a demonstration project for learning purposes. Feel free to:
- Report issues
- Suggest improvements
- Fork and extend for your use cases
- Use as a starting point for your own graph processing systems

---

Built as a practical demonstration of OpenSPG concepts with Python and Memgraph.
