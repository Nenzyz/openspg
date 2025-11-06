"""API request and response models."""

from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field


# Query API Models

class QueryRequest(BaseModel):
    """Request to execute a DSL query."""
    query: str = Field(..., description="DSL query string")
    parameters: Optional[Dict[str, Any]] = Field(
        default=None,
        description="Optional query parameters"
    )


class QueryResponse(BaseModel):
    """Response from query execution."""
    success: bool = Field(..., description="Whether query succeeded")
    results: List[Dict[str, Any]] = Field(..., description="Query results")
    row_count: int = Field(..., description="Number of result rows")
    compiled_query: Optional[str] = Field(
        default=None,
        description="Compiled Cypher query (if debug=true)"
    )
    error: Optional[str] = Field(
        default=None,
        description="Error message if query failed"
    )


class CompileRequest(BaseModel):
    """Request to compile a DSL query to Cypher."""
    query: str = Field(..., description="DSL query string")


class CompileResponse(BaseModel):
    """Response from query compilation."""
    success: bool
    cypher_query: Optional[str] = None
    error: Optional[str] = None


# Entity Management API Models

class CreateEntityRequest(BaseModel):
    """Request to create an entity."""
    entity_type: str = Field(..., description="Entity type name")
    properties: Dict[str, Any] = Field(..., description="Entity properties")
    entity_id: Optional[str] = Field(default=None, description="Optional custom ID")


class CreateEntityResponse(BaseModel):
    """Response from entity creation."""
    success: bool
    entity_id: Optional[str] = None
    error: Optional[str] = None


class CreateRelationRequest(BaseModel):
    """Request to create a relation."""
    source_id: str = Field(..., description="Source entity ID")
    target_id: str = Field(..., description="Target entity ID")
    relation_type: str = Field(..., description="Relation type name")
    properties: Optional[Dict[str, Any]] = Field(
        default=None,
        description="Optional relation properties"
    )


class CreateRelationResponse(BaseModel):
    """Response from relation creation."""
    success: bool
    relation_id: Optional[str] = None
    error: Optional[str] = None


class GetEntityRequest(BaseModel):
    """Request to get an entity by ID."""
    entity_id: str = Field(..., description="Entity ID")


class GetEntityResponse(BaseModel):
    """Response from getting an entity."""
    success: bool
    entity: Optional[Dict[str, Any]] = None
    error: Optional[str] = None


# Schema API Models

class SchemaInfo(BaseModel):
    """Schema information."""
    name: str
    version: str
    entity_types: List[str]
    relation_types: List[str]


class SchemaListResponse(BaseModel):
    """Response with list of schemas."""
    success: bool
    schemas: List[str]
    active_schema: Optional[str] = None


class SchemaDetailResponse(BaseModel):
    """Response with schema details."""
    success: bool
    schema: Optional[SchemaInfo] = None
    error: Optional[str] = None


# Health Check

class HealthResponse(BaseModel):
    """Health check response."""
    status: str = Field(..., description="Service status")
    database_connected: bool = Field(..., description="Database connection status")
    version: str = Field(..., description="API version")
