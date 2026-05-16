"""
FastAPI application entry point.
Initializes all components and configures the application.
"""
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.schemas import HealthResponse
from app.catalog_loader import CatalogLoader
from app.hybrid_retrieval import HybridRetriever
from app.state_machine import StateMachine
from app.llm import LLMClient
from app.constraints import ConstraintExtractor
from app import router


# Global instances
app_state = {}


@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Application lifespan manager.
    Initializes components on startup and cleans up on shutdown.
    """
    # Startup: Initialize all components
    print("Initializing SHL Talent Navigator...")
    
    # Load catalog
    catalog_loader = CatalogLoader()
    print(f"Loaded {catalog_loader.get_catalog_size()} assessments")
    
    # Initialize hybrid retriever
    hybrid_retriever = HybridRetriever(catalog_loader.get_all_assessments())
    print("Hybrid retrieval system initialized")
    
    # Initialize state machine
    state_machine = StateMachine()
    
    # Initialize LLM client
    llm_client = LLMClient()
    if llm_client.template_mode:
        print("⚠️  Running in NO-API-KEY MODE (template responses)")
        print("   For enhanced responses, set LLM_API_KEY environment variable")
        print("   Recommended: Get free Gemini API key from https://aistudio.google.com/")
    else:
        print(f"✓ LLM client initialized: {llm_client.provider} ({llm_client.model})")
    
    # Initialize constraint extractor
    constraint_extractor = ConstraintExtractor()
    
    # Store in app state
    app_state["catalog_loader"] = catalog_loader
    app_state["hybrid_retriever"] = hybrid_retriever
    app_state["state_machine"] = state_machine
    app_state["llm_client"] = llm_client
    app_state["constraint_extractor"] = constraint_extractor
    
    # Set router dependencies
    router.catalog_loader = catalog_loader
    router.hybrid_retriever = hybrid_retriever
    router.state_machine = state_machine
    router.llm_client = llm_client
    router.constraint_extractor = constraint_extractor
    
    print("Application ready!")
    
    yield
    
    # Shutdown: Cleanup
    if llm_client:
        await llm_client.close()
    print("Application shutdown complete")


# Create FastAPI application
app = FastAPI(
    title="SHL Talent Navigator",
    description="Conversational recommendation system for SHL assessments",
    version="1.0.0",
    lifespan=lifespan
)

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Configure appropriately for production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/health", response_model=HealthResponse)
async def health_check() -> HealthResponse:
    """
    Health check endpoint.
    Returns service status and component health.
    """
    catalog_loader = app_state.get("catalog_loader")
    hybrid_retriever = app_state.get("hybrid_retriever")
    
    is_healthy = (
        catalog_loader is not None and
        hybrid_retriever is not None
    )
    
    return HealthResponse(
        status="healthy" if is_healthy else "unhealthy",
        version="1.0.0",
        vector_store_loaded=hybrid_retriever is not None,
        catalog_size=catalog_loader.get_catalog_size() if catalog_loader else 0
    )


# Include chat router
app.include_router(router.router, tags=["chat"])


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
