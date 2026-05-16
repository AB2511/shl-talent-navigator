"""
Pydantic schemas for request/response validation.
Ensures strict JSON schema compliance across the API.
"""
from typing import List, Literal, Optional
from pydantic import BaseModel, Field, validator


class Message(BaseModel):
    """Single message in conversation history."""
    role: Literal["user", "assistant"] = Field(..., description="Message sender role")
    content: str = Field(..., min_length=1, description="Message content")

    @validator("content")
    def content_not_empty(cls, v):
        if not v.strip():
            raise ValueError("Message content cannot be empty or whitespace only")
        return v.strip()


class ChatRequest(BaseModel):
    """Request schema for /chat endpoint."""
    messages: List[Message] = Field(..., min_items=1, description="Conversation history")

    @validator("messages")
    def validate_messages(cls, v):
        if not v:
            raise ValueError("Messages list cannot be empty")
        # Ensure alternating roles starting with user
        if v[0].role != "user":
            raise ValueError("First message must be from user")
        return v


class Assessment(BaseModel):
    """SHL Assessment metadata with full structured fields."""
    id: str = Field(..., description="Unique assessment identifier")
    name: str = Field(..., description="Assessment name")
    description: str = Field(..., description="Assessment description")
    
    # Job targeting
    job_levels: List[str] = Field(default_factory=list, description="Target job levels (Graduate, Entry, Mid-Professional, Manager, Senior, Executive)")
    
    # Technical specs
    duration_minutes: int = Field(..., description="Typical completion time")
    remote_testing: bool = Field(default=True, description="Available for remote administration")
    adaptive_irt: bool = Field(default=False, description="Uses adaptive IRT technology")
    languages: List[str] = Field(default_factory=lambda: ["English"], description="Available languages")
    
    # Classification
    test_types: List[str] = Field(default_factory=list, description="Test type codes: A=Ability, P=Personality, B=Behavioral, C=Competency, S=Simulation, K=Knowledge")
    categories: List[str] = Field(default_factory=list, description="Assessment categories")
    skills: List[str] = Field(default_factory=list, description="Skills measured")
    
    # Reference
    url: str = Field(..., description="Official SHL catalog URL")


class ChatResponse(BaseModel):
    """Response schema for /chat endpoint."""
    response: str = Field(..., description="Assistant's response message")
    state: Literal[
        "insufficient_context",
        "clarification",
        "recommendation",
        "refinement",
        "comparison",
        "refusal"
    ] = Field(..., description="Current conversation state")
    assessments: List[Assessment] = Field(
        default_factory=list,
        description="Recommended assessments (1-10 items)"
    )

    @validator("assessments")
    def validate_assessment_count(cls, v, values):
        state = values.get("state")
        if state in ["recommendation", "refinement", "comparison"] and len(v) > 10:
            raise ValueError("Cannot recommend more than 10 assessments")
        return v


class HealthResponse(BaseModel):
    """Response schema for /health endpoint."""
    status: Literal["healthy", "unhealthy"] = Field(..., description="Service health status")
    version: str = Field(default="1.0.0", description="API version")
    vector_store_loaded: bool = Field(..., description="FAISS index status")
    catalog_size: int = Field(..., description="Number of assessments in catalog")
