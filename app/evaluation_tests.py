"""
Comprehensive test suite for SHL Talent Navigator.
Tests all components and end-to-end functionality.
"""
import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.catalog_loader import CatalogLoader
from app.state_machine import StateMachine
from app.retrieval import VectorRetriever
from app.filters import FilterExtractor
from app.schemas import ChatRequest, Message, Assessment


# Test fixtures
@pytest.fixture
def catalog_loader():
    """Create catalog loader instance."""
    return CatalogLoader()


@pytest.fixture
def state_machine():
    """Create state machine instance."""
    return StateMachine()


@pytest.fixture
def vector_retriever(catalog_loader):
    """Create vector retriever instance."""
    return VectorRetriever(catalog_loader)


@pytest.fixture
def filter_extractor():
    """Create filter extractor instance."""
    return FilterExtractor()


@pytest.fixture
def client():
    """Create test client."""
    return TestClient(app)


# Catalog Loader Tests
class TestCatalogLoader:
    """Test catalog loading and management."""
    
    def test_catalog_loads(self, catalog_loader):
        """Test that catalog loads successfully."""
        assert catalog_loader.get_catalog_size() > 0
    
    def test_get_all_assessments(self, catalog_loader):
        """Test retrieving all assessments."""
        assessments = catalog_loader.get_all_assessments()
        assert len(assessments) > 0
        assert all(isinstance(a, Assessment) for a in assessments)
    
    def test_get_assessment_by_id(self, catalog_loader):
        """Test retrieving specific assessment."""
        assessment = catalog_loader.get_assessment_by_id("shl-verify-g-plus")
        assert assessment is not None
        assert assessment.id == "shl-verify-g-plus"
        assert "cognitive" in assessment.category.lower()
    
    def test_search_by_category(self, catalog_loader):
        """Test category filtering."""
        cognitive = catalog_loader.search_by_category("cognitive")
        assert len(cognitive) > 0
        assert all(a.category.lower() == "cognitive" for a in cognitive)
    
    def test_search_by_skill(self, catalog_loader):
        """Test skill filtering."""
        leadership = catalog_loader.search_by_skill("leadership")
        assert len(leadership) > 0
        assert all(
            any("leadership" in s.lower() for s in a.skills)
            for a in leadership
        )


# State Machine Tests
class TestStateMachine:
    """Test state machine logic."""
    
    def test_initial_state_clarification(self, state_machine):
        """Test initial vague query leads to clarification."""
        messages = [Message(role="user", content="I need an assessment")]
        state = state_machine.determine_state(messages)
        assert state == "clarification"
    
    def test_off_topic_refusal(self, state_machine):
        """Test off-topic queries are refused."""
        messages = [Message(role="user", content="What's the weather today?")]
        state = state_machine.determine_state(messages)
        assert state == "refusal"
    
    def test_specific_query_recommendation(self, state_machine):
        """Test specific query leads to recommendation."""
        messages = [
            Message(
                role="user",
                content="I need a cognitive assessment for leadership roles"
            )
        ]
        state = state_machine.determine_state(messages)
        assert state == "recommendation"
    
    def test_comparison_detection(self, state_machine):
        """Test comparison request detection."""
        messages = [
            Message(role="user", content="I need leadership assessments"),
            Message(role="assistant", content="Here are some options..."),
            Message(role="user", content="Can you compare the first two?")
        ]
        state = state_machine.determine_state(messages)
        assert state == "comparison"
    
    def test_refinement_detection(self, state_machine):
        """Test refinement request detection."""
        messages = [
            Message(role="user", content="I need cognitive assessments"),
            Message(role="assistant", content="Here are recommendations..."),
            Message(role="user", content="Show me shorter alternatives")
        ]
        state = state_machine.determine_state(messages)
        assert state == "refinement"


# Vector Retrieval Tests
class TestVectorRetriever:
    """Test vector retrieval functionality."""
    
    def test_retriever_initialization(self, vector_retriever):
        """Test retriever initializes successfully."""
        assert vector_retriever.is_loaded()
        assert vector_retriever.index.ntotal > 0
    
    def test_basic_retrieval(self, vector_retriever):
        """Test basic retrieval returns results."""
        results = vector_retriever.retrieve("leadership assessment", top_k=5)
        assert len(results) > 0
        assert len(results) <= 5
        assert all(isinstance(a, Assessment) for a in results)
    
    def test_category_filtering(self, vector_retriever):
        """Test category filter works."""
        results = vector_retriever.retrieve(
            "assessment",
            top_k=5,
            filter_category="cognitive"
        )
        assert all(a.category.lower() == "cognitive" for a in results)
    
    def test_skill_filtering(self, vector_retriever):
        """Test skill filter works."""
        results = vector_retriever.retrieve(
            "assessment",
            top_k=5,
            filter_skills=["leadership"]
        )
        assert all(
            any("leadership" in s.lower() for s in a.skills)
            for a in results
        )
    
    def test_max_10_recommendations(self, vector_retriever):
        """Test that retrieval respects 10 item limit."""
        results = vector_retriever.retrieve("assessment", top_k=20)
        assert len(results) <= 10


# Filter Extractor Tests
class TestFilterExtractor:
    """Test filter extraction logic."""
    
    def test_category_extraction(self, filter_extractor):
        """Test category extraction from query."""
        category, _, _ = filter_extractor.extract_filters(
            "I need a cognitive assessment"
        )
        assert category == "cognitive"
    
    def test_skill_extraction(self, filter_extractor):
        """Test skill extraction from query."""
        _, skills, _ = filter_extractor.extract_filters(
            "Looking for leadership and teamwork assessment"
        )
        assert skills is not None
        assert "leadership" in skills
        assert "teamwork" in skills
    
    def test_duration_extraction(self, filter_extractor):
        """Test duration constraint extraction."""
        _, _, duration = filter_extractor.extract_filters(
            "Need a quick assessment under 20 minutes"
        )
        assert duration is not None
        assert duration <= 20
    
    def test_vague_query_detection(self, filter_extractor):
        """Test vague query detection."""
        assert filter_extractor.is_vague_query("need assessment")
        assert not filter_extractor.is_vague_query(
            "need cognitive assessment for senior leadership role"
        )


# API Endpoint Tests
class TestAPIEndpoints:
    """Test API endpoints."""
    
    def test_health_endpoint(self, client):
        """Test health check endpoint."""
        response = client.get("/health")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] in ["healthy", "unhealthy"]
        assert "version" in data
        assert "catalog_size" in data
    
    def test_chat_endpoint_basic(self, client):
        """Test basic chat endpoint."""
        request = ChatRequest(
            messages=[
                Message(
                    role="user",
                    content="I need a cognitive assessment for leadership"
                )
            ]
        )
        response = client.post("/chat", json=request.dict())
        assert response.status_code == 200
        data = response.json()
        assert "response" in data
        assert "state" in data
        assert "assessments" in data
    
    def test_chat_endpoint_validation(self, client):
        """Test request validation."""
        # Empty messages
        response = client.post("/chat", json={"messages": []})
        assert response.status_code == 422
        
        # Invalid role
        response = client.post("/chat", json={
            "messages": [{"role": "invalid", "content": "test"}]
        })
        assert response.status_code == 422
    
    def test_chat_refusal_state(self, client):
        """Test off-topic request handling."""
        request = ChatRequest(
            messages=[
                Message(role="user", content="What's the weather today?")
            ]
        )
        response = client.post("/chat", json=request.dict())
        assert response.status_code == 200
        data = response.json()
        assert data["state"] == "refusal"
        assert len(data["assessments"]) == 0


# Integration Tests
class TestIntegration:
    """End-to-end integration tests."""
    
    def test_full_conversation_flow(self, client):
        """Test complete conversation flow."""
        # Step 1: Vague query -> clarification
        response1 = client.post("/chat", json={
            "messages": [
                {"role": "user", "content": "I need an assessment"}
            ]
        })
        assert response1.status_code == 200
        data1 = response1.json()
        assert data1["state"] in ["clarification", "recommendation"]
        
        # Step 2: Specific query -> recommendation
        response2 = client.post("/chat", json={
            "messages": [
                {"role": "user", "content": "I need an assessment"},
                {"role": "assistant", "content": data1["response"]},
                {"role": "user", "content": "For a leadership role requiring cognitive skills"}
            ]
        })
        assert response2.status_code == 200
        data2 = response2.json()
        assert data2["state"] in ["recommendation", "refinement"]
        assert len(data2["assessments"]) > 0
    
    def test_no_hallucinated_urls(self, client):
        """Test that responses only contain catalog URLs."""
        request = ChatRequest(
            messages=[
                Message(
                    role="user",
                    content="Recommend cognitive assessments"
                )
            ]
        )
        response = client.post("/chat", json=request.dict())
        data = response.json()
        
        # Check all returned assessments have valid URLs
        for assessment in data["assessments"]:
            assert assessment["url"].startswith("https://www.shl.com/")
    
    def test_max_10_recommendations(self, client):
        """Test that API never returns more than 10 recommendations."""
        request = ChatRequest(
            messages=[
                Message(role="user", content="Show me all assessments")
            ]
        )
        response = client.post("/chat", json=request.dict())
        data = response.json()
        assert len(data["assessments"]) <= 10


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
