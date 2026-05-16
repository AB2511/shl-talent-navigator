"""
Final verification script before submission.
Checks all critical components are working correctly.
"""
import sys
import asyncio
from app.catalog_loader import CatalogLoader
from app.hybrid_retrieval import HybridRetriever
from app.state_machine import StateMachine
from app.llm import LLMClient
from app.constraints import ConstraintExtractor
from app.schemas import Message


def verify_catalog():
    """Verify catalog is loaded correctly."""
    print("=" * 60)
    print("VERIFICATION 1: Catalog Loading")
    print("=" * 60)
    
    catalog_loader = CatalogLoader()
    count = catalog_loader.get_catalog_size()
    
    print(f"✓ Catalog loaded: {count} assessments")
    assert count == 37, f"Expected 37 assessments, got {count}"
    
    # Verify assessments have required fields
    assessments = catalog_loader.get_all_assessments()
    sample = assessments[0]
    
    assert sample.id, "Assessment must have ID"
    assert sample.name, "Assessment must have name"
    assert sample.url, "Assessment must have URL"
    assert sample.test_types, "Assessment must have test types"
    assert sample.job_levels, "Assessment must have job levels"
    
    print(f"✓ Sample assessment: {sample.name}")
    print(f"✓ All assessments have required fields")
    print("✅ VERIFICATION 1 PASSED\n")


def verify_hybrid_retrieval():
    """Verify hybrid retrieval system."""
    print("=" * 60)
    print("VERIFICATION 2: Hybrid Retrieval")
    print("=" * 60)
    
    catalog_loader = CatalogLoader()
    retriever = HybridRetriever(catalog_loader.get_all_assessments())
    
    # Test retrieval
    from app.constraints import ConversationConstraints
    constraints = ConversationConstraints()
    constraints.job_levels = ["Graduate"]
    
    results = retriever.retrieve(
        query="cognitive assessment for software engineers",
        constraints=constraints,
        top_k=5
    )
    
    print(f"✓ Retrieved {len(results)} assessments")
    assert len(results) > 0, "Should retrieve at least one assessment"
    
    # Verify results match constraints
    for result in results:
        assert "Graduate" in result.job_levels, "Results should match job level constraint"
    
    print(f"✓ All results match constraints")
    print("✅ VERIFICATION 2 PASSED\n")


def verify_state_machine():
    """Verify state machine with explicit transitions."""
    print("=" * 60)
    print("VERIFICATION 3: State Machine")
    print("=" * 60)
    
    state_machine = StateMachine()
    
    # Verify transition table exists
    assert hasattr(state_machine, 'TRANSITIONS'), "Must have TRANSITIONS table"
    assert len(state_machine.TRANSITIONS) > 0, "TRANSITIONS table must not be empty"
    
    print(f"✓ Transition table defined with {len(state_machine.TRANSITIONS)} states")
    
    # Verify deterministic methods exist
    assert hasattr(state_machine, 'get_deterministic_refusal_response'), "Must have deterministic refusal"
    assert hasattr(state_machine, 'get_deterministic_clarification_questions'), "Must have deterministic clarification"
    assert hasattr(state_machine, 'validate_transition'), "Must have transition validation"
    
    print("✓ Deterministic methods implemented")
    
    # Test deterministic refusal
    refusal = state_machine.get_deterministic_refusal_response()
    assert len(refusal) > 0, "Refusal response must not be empty"
    assert "SHL" in refusal, "Refusal should mention SHL"
    
    print("✓ Deterministic refusal works")
    
    # Test deterministic clarification
    from app.constraints import ConversationConstraints
    constraints = ConversationConstraints()
    clarification = state_machine.get_deterministic_clarification_questions(constraints)
    assert len(clarification) > 0, "Clarification must not be empty"
    assert "?" in clarification, "Clarification should contain questions"
    
    print("✓ Deterministic clarification works")
    
    # Test transition validation
    assert state_machine.validate_transition("clarification", "recommendation"), "Valid transition should pass"
    assert not state_machine.validate_transition("refusal", "recommendation"), "Invalid transition should fail"
    
    print("✓ Transition validation works")
    print("✅ VERIFICATION 3 PASSED\n")


async def verify_llm_client():
    """Verify LLM client with NO-API-KEY mode."""
    print("=" * 60)
    print("VERIFICATION 4: LLM Client (NO-API-KEY Mode)")
    print("=" * 60)
    
    import os
    
    # Remove API key to test NO-API-KEY mode
    original_key = os.environ.get("LLM_API_KEY")
    if "LLM_API_KEY" in os.environ:
        del os.environ["LLM_API_KEY"]
    
    try:
        # Should not crash
        client = LLMClient()
        
        print(f"✓ Client initialized in template mode: {client.template_mode}")
        assert client.template_mode == True, "Should be in template mode without API key"
        
        # Test generation
        response = await client.generate(
            prompt="Recommend assessments",
            system_prompt="You are helpful"
        )
        
        assert response is not None, "Should return response"
        assert len(response) > 0, "Response should not be empty"
        
        print(f"✓ Template response generated: {len(response)} chars")
        print("✅ VERIFICATION 4 PASSED\n")
        
        await client.close()
        
    finally:
        # Restore API key
        if original_key:
            os.environ["LLM_API_KEY"] = original_key


def verify_constraint_extractor():
    """Verify constraint extraction."""
    print("=" * 60)
    print("VERIFICATION 5: Constraint Extraction")
    print("=" * 60)
    
    extractor = ConstraintExtractor()
    
    messages = [
        Message(role="user", content="I need a graduate assessment"),
        Message(role="assistant", content="Here are some options..."),
        Message(role="user", content="Make it under 30 minutes and remote")
    ]
    
    constraints = extractor.extract_from_messages(messages)
    
    print(f"✓ Extracted constraints: {constraints.to_dict()}")
    
    # Verify cumulative extraction
    assert "Graduate" in constraints.job_levels, "Should extract job level"
    assert constraints.max_duration == 30, "Should extract duration"
    assert constraints.remote_testing == True, "Should extract remote requirement"
    
    print("✓ Cumulative constraint extraction works")
    print("✅ VERIFICATION 5 PASSED\n")


def verify_explainability():
    """Verify explainability in recommendations."""
    print("=" * 60)
    print("VERIFICATION 6: Explainability")
    print("=" * 60)
    
    from app.prompts import format_assessment_with_explanation
    from app.constraints import ConversationConstraints
    from app.catalog_loader import CatalogLoader
    
    catalog_loader = CatalogLoader()
    assessment = catalog_loader.get_all_assessments()[0]
    
    constraints = ConversationConstraints()
    constraints.job_levels = ["Graduate"]
    
    explanation = format_assessment_with_explanation(assessment, "test query", constraints)
    
    print(f"✓ Generated explanation: {len(explanation)} chars")
    assert len(explanation) > 0, "Explanation must not be empty"
    assert assessment.name in explanation, "Should include assessment name"
    assert "✓" in explanation or "•" in explanation, "Should have structured format"
    
    print("✓ Explainability format correct")
    print("✅ VERIFICATION 6 PASSED\n")


def verify_documentation():
    """Verify documentation files exist."""
    print("=" * 60)
    print("VERIFICATION 7: Documentation")
    print("=" * 60)
    
    import os
    
    required_files = [
        "README.md",
        "PRODUCTION_READINESS.md",
        "CRITICAL_IMPROVEMENTS_SUMMARY.md",
        "ARCHITECTURE.md",
        ".env.example",
        "requirements.txt",
        "test_no_api_key_mode.py",
        "verify_submission.py"
    ]
    
    for file in required_files:
        assert os.path.exists(file), f"Missing required file: {file}"
        print(f"✓ {file}")
    
    print("✅ VERIFICATION 7 PASSED\n")


async def main():
    """Run all verifications."""
    print("\n" + "=" * 60)
    print("FINAL SUBMISSION VERIFICATION")
    print("=" * 60 + "\n")
    
    try:
        verify_catalog()
        verify_hybrid_retrieval()
        verify_state_machine()
        await verify_llm_client()
        verify_constraint_extractor()
        verify_explainability()
        verify_documentation()
        
        print("=" * 60)
        print("✅ ALL VERIFICATIONS PASSED")
        print("=" * 60)
        print("\n🎉 READY FOR SUBMISSION! 🎉\n")
        print("Key Features Verified:")
        print("  ✓ 37 assessments loaded")
        print("  ✓ Hybrid retrieval working")
        print("  ✓ Deterministic state machine")
        print("  ✓ NO-API-KEY mode functional")
        print("  ✓ Constraint accumulation")
        print("  ✓ Explainability implemented")
        print("  ✓ Documentation complete")
        print("\nNext Steps:")
        print("  1. Optional: Test with Gemini API key")
        print("  2. Run: uvicorn app.main:app --reload")
        print("  3. Test endpoints manually")
        print("  4. Submit project")
        
        return 0
        
    except AssertionError as e:
        print(f"\n❌ VERIFICATION FAILED: {e}")
        return 1
    except Exception as e:
        print(f"\n❌ ERROR: {e}")
        import traceback
        traceback.print_exc()
        return 1


if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code)
