"""FastAPI application for GraphSPG."""

from contextlib import asynccontextmanager
from typing import Optional
from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware

from graphspg.api.models import (
    CompileRequest,
    CompileResponse,
    CreateEntityRequest,
    CreateEntityResponse,
    CreateRelationRequest,
    CreateRelationResponse,
    GetEntityRequest,
    GetEntityResponse,
    HealthResponse,
    QueryRequest,
    QueryResponse,
    SchemaDetailResponse,
    SchemaInfo,
    SchemaListResponse,
)
from graphspg.engine.executor import QueryExecutor
from graphspg.schema.registry import schema_registry
from graphspg.storage.memgraph import MemgraphAdapter
from graphspg.utils.config import settings


# Global storage adapter and executor
storage: Optional[MemgraphAdapter] = None
executor: Optional[QueryExecutor] = None


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan manager."""
    global storage, executor

    # Startup: Initialize storage and executor
    storage = MemgraphAdapter(
        uri=settings.memgraph_uri,
        user=settings.memgraph_user,
        password=settings.memgraph_password
    )
    storage.connect()
    executor = QueryExecutor(storage=storage)

    yield

    # Shutdown: Close connections
    if storage:
        storage.close()


# Create FastAPI app
app = FastAPI(
    title=settings.api_title,
    version=settings.api_version,
    lifespan=lifespan
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# Health Check

@app.get("/health", response_model=HealthResponse)
async def health_check():
    """Health check endpoint."""
    database_connected = False
    if storage:
        try:
            storage.execute_query("RETURN 1")
            database_connected = True
        except Exception:
            pass

    return HealthResponse(
        status="healthy" if database_connected else "degraded",
        database_connected=database_connected,
        version=settings.api_version
    )


# Query API

@app.post("/api/v1/query", response_model=QueryResponse)
async def execute_query(
    request: QueryRequest,
    debug: bool = Query(False, description="Include compiled Cypher in response")
):
    """Execute a DSL query."""
    if not executor:
        raise HTTPException(status_code=503, detail="Service not ready")

    try:
        # Get compiled query if debug mode
        compiled_query = None
        if debug:
            compiled_query = executor.get_compiled_query(request.query)

        # Execute query
        results = executor.execute(request.query, request.parameters)

        return QueryResponse(
            success=True,
            results=results,
            row_count=len(results),
            compiled_query=compiled_query
        )
    except Exception as e:
        return QueryResponse(
            success=False,
            results=[],
            row_count=0,
            error=str(e)
        )


@app.post("/api/v1/compile", response_model=CompileResponse)
async def compile_query(request: CompileRequest):
    """Compile DSL query to Cypher without executing."""
    if not executor:
        raise HTTPException(status_code=503, detail="Service not ready")

    try:
        cypher_query = executor.get_compiled_query(request.query)
        return CompileResponse(
            success=True,
            cypher_query=cypher_query
        )
    except Exception as e:
        return CompileResponse(
            success=False,
            error=str(e)
        )


@app.post("/api/v1/query/cypher", response_model=QueryResponse)
async def execute_cypher(request: QueryRequest):
    """Execute a raw Cypher query directly."""
    if not executor:
        raise HTTPException(status_code=503, detail="Service not ready")

    try:
        results = executor.execute_cypher(request.query, request.parameters)
        return QueryResponse(
            success=True,
            results=results,
            row_count=len(results)
        )
    except Exception as e:
        return QueryResponse(
            success=False,
            results=[],
            row_count=0,
            error=str(e)
        )


# Entity Management API

@app.post("/api/v1/entities", response_model=CreateEntityResponse)
async def create_entity(request: CreateEntityRequest):
    """Create a new entity."""
    if not storage:
        raise HTTPException(status_code=503, detail="Service not ready")

    try:
        entity_id = storage.create_vertex(
            labels=[request.entity_type],
            properties=request.properties,
            vertex_id=request.entity_id
        )
        return CreateEntityResponse(
            success=True,
            entity_id=entity_id
        )
    except Exception as e:
        return CreateEntityResponse(
            success=False,
            error=str(e)
        )


@app.get("/api/v1/entities/{entity_id}", response_model=GetEntityResponse)
async def get_entity(entity_id: str):
    """Get an entity by ID."""
    if not storage:
        raise HTTPException(status_code=503, detail="Service not ready")

    try:
        entity = storage.get_vertex(entity_id)
        if entity is None:
            return GetEntityResponse(
                success=False,
                error="Entity not found"
            )
        return GetEntityResponse(
            success=True,
            entity=entity
        )
    except Exception as e:
        return GetEntityResponse(
            success=False,
            error=str(e)
        )


@app.post("/api/v1/relations", response_model=CreateRelationResponse)
async def create_relation(request: CreateRelationRequest):
    """Create a new relation between entities."""
    if not storage:
        raise HTTPException(status_code=503, detail="Service not ready")

    try:
        relation_id = storage.create_edge(
            source_id=request.source_id,
            target_id=request.target_id,
            edge_type=request.relation_type,
            properties=request.properties
        )
        return CreateRelationResponse(
            success=True,
            relation_id=relation_id
        )
    except Exception as e:
        return CreateRelationResponse(
            success=False,
            error=str(e)
        )


# Schema API

@app.get("/api/v1/schemas", response_model=SchemaListResponse)
async def list_schemas():
    """List all registered schemas."""
    schemas = schema_registry.list_schemas()
    active = schema_registry.get_active()
    return SchemaListResponse(
        success=True,
        schemas=schemas,
        active_schema=active.name if active else None
    )


@app.get("/api/v1/schemas/{schema_name}", response_model=SchemaDetailResponse)
async def get_schema(schema_name: str):
    """Get schema details."""
    schema = schema_registry.get(schema_name)
    if not schema:
        return SchemaDetailResponse(
            success=False,
            error="Schema not found"
        )

    entity_types = [et.name for et in schema.entity_types]
    relation_types = [r.name for r in schema.relations]

    return SchemaDetailResponse(
        success=True,
        schema=SchemaInfo(
            name=schema.name,
            version=schema.version,
            entity_types=entity_types,
            relation_types=relation_types
        )
    )


# Root endpoint

@app.get("/")
async def root():
    """Root endpoint."""
    return {
        "name": settings.api_title,
        "version": settings.api_version,
        "docs": "/docs"
    }


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        app,
        host=settings.api_host,
        port=settings.api_port
    )
