"""
Test script to verify NO-API-KEY mode works correctly.
This ensures the application never crashes due to missing API key.
"""
import os
import asyncio
from app.llm import LLMClient
from app.state_machine import StateMachine
from app.constraints import ConstraintExtractor
from app.schemas import Message


async def test_no_api_key_mode():
    """Test that LLM client works in template mode without API key."""
    print("=" * 60)
    print("TEST 1: LLM Client Initialization Without API Key")
    print("=" * 60)
    
    # Remove API key from environment
    original_key = os.environ.get("LLM_API_KEY")
    if "LLM_API_KEY" in os.environ:
        del os.environ["LLM_API_KEY"]
    
    try:
        # Should not crash
        client = LLMClient()
        print(f"✓ Client initialized successfully")
        print(f"✓ Template mode: {client.template_mode}")
        assert client.template_mode == True, "Should be in template mode"
        
        # Test generation
        response = await client.generate(
            prompt="Recommend assessments for software engineers",
            system_prompt="You are a helpful assistant"
        )
        print(f"✓ Generated response: {response[:100]}...")
        assert response is not None, "Should return a response"
        assert len(response) > 0, "Response should not be empty"
        
        print("\n✅ TEST 1 PASSED: NO-API-KEY mode works correctly\n")
        
    finally:
        # Restore original API key
        if original_key:
            os.environ["LLM_API_KEY"] = original_key
        if client:
            await client.close()


def test_deterministic_refusal():
    """Test that refusal responses are deterministic (no LLM)."""
    print("=" * 60)
    print("TEST 2: Deterministic Refusal Response")
    print("=" * 60)
    
    state_machine = StateMachine()
    
    # Get refusal response multiple times
    response1 = state_machine.get_deterministic_refusal_response()
    response2 = state_machine.get_deterministic_refusal_response()
    
    print(f"Response 1: {response1[:80]}...")
    print(f"Response 2: {response2[:80]}...")
    
    # Should be identical (deterministic)
    assert response1 == response2, "Refusal responses should be identical"
    assert "SHL Talent Navigator" in response1, "Should mention SHL Talent Navigator"
    assert len(response1) > 0, "Response should not be empty"
    
    print("\n✅ TEST 2 PASSED: Refusal is deterministic\n")


def test_deterministic_clarification():
    """Test that clarification questions are deterministic (no LLM)."""
    print("=" * 60)
    print("TEST 3: Deterministic Clarification Questions")
    print("=" * 60)
    
    state_machine = StateMachine()
    constraint_extractor = ConstraintExtractor()
    
    # Create empty constraints
    messages = [Message(role="user", content="I need an assessment")]
    constraints = constraint_extractor.extract_from_messages(messages)
    
    # Get clarification questions multiple times
    response1 = state_machine.get_deterministic_clarification_questions(constraints)
    response2 = state_machine.get_deterministic_clarification_questions(constraints)
    
    print(f"Response 1: {response1[:100]}...")
    print(f"Response 2: {response2[:100]}...")
    
    # Should be identical (deterministic)
    assert response1 == response2, "Clarification responses should be identical"
    assert "?" in response1, "Should contain questions"
    assert len(response1) > 0, "Response should not be empty"
    
    print("\n✅ TEST 3 PASSED: Clarification is deterministic\n")


def test_state_transitions():
    """Test explicit state transition table."""
    print("=" * 60)
    print("TEST 4: State Transition Validation")
    print("=" * 60)
    
    state_machine = StateMachine()
    
    # Test valid transitions
    valid_transitions = [
        ("clarification", "recommendation"),
        ("recommendation", "refinement"),
        ("recommendation", "comparison"),
        ("refinement", "recommendation"),
    ]
    
    for from_state, to_state in valid_transitions:
        result = state_machine.validate_transition(from_state, to_state)
        print(f"✓ {from_state} -> {to_state}: {result}")
        assert result == True, f"Should allow {from_state} -> {to_state}"
    
    # Test invalid transitions
    invalid_transitions = [
        ("refusal", "recommendation"),  # Refusal is terminal
        ("refusal", "clarification"),
    ]
    
    for from_state, to_state in invalid_transitions:
        result = state_machine.validate_transition(from_state, to_state)
        print(f"✗ {from_state} -> {to_state}: {result}")
        assert result == False, f"Should not allow {from_state} -> {to_state}"
    
    print("\n✅ TEST 4 PASSED: State transitions validated correctly\n")


def test_off_topic_detection():
    """Test that off-topic queries are detected correctly."""
    print("=" * 60)
    print("TEST 5: Off-Topic Query Detection")
    print("=" * 60)
    
    state_machine = StateMachine()
    
    # Off-topic queries
    off_topic = [
        "What's the weather today?",
        "Tell me a joke",
        "Who won the election?",
        "Recipe for chocolate cake",
    ]
    
    for query in off_topic:
        is_off_topic = state_machine._is_off_topic(query)
        print(f"✓ '{query}': off-topic={is_off_topic}")
        assert is_off_topic == True, f"Should detect '{query}' as off-topic"
    
    # On-topic queries
    on_topic = [
        "I need an assessment for software engineers",
        "What cognitive tests do you have?",
        "Recommend personality assessments",
        "SHL verify tests for graduates",
    ]
    
    for query in on_topic:
        is_off_topic = state_machine._is_off_topic(query)
        print(f"✓ '{query}': off-topic={is_off_topic}")
        assert is_off_topic == False, f"Should detect '{query}' as on-topic"
    
    print("\n✅ TEST 5 PASSED: Off-topic detection works correctly\n")


async def main():
    """Run all tests."""
    print("\n" + "=" * 60)
    print("PRODUCTION READINESS TESTS")
    print("=" * 60 + "\n")
    
    try:
        # Test 1: NO-API-KEY mode
        await test_no_api_key_mode()
        
        # Test 2: Deterministic refusal
        test_deterministic_refusal()
        
        # Test 3: Deterministic clarification
        test_deterministic_clarification()
        
        # Test 4: State transitions
        test_state_transitions()
        
        # Test 5: Off-topic detection
        test_off_topic_detection()
        
        print("=" * 60)
        print("✅ ALL TESTS PASSED")
        print("=" * 60)
        print("\nThe application is production-ready:")
        print("  ✓ Works without API key (template mode)")
        print("  ✓ Deterministic refusal (no LLM)")
        print("  ✓ Deterministic clarification (no LLM)")
        print("  ✓ Explicit state transitions")
        print("  ✓ Off-topic detection")
        print("\nReady for submission! 🚀")
        
    except AssertionError as e:
        print(f"\n❌ TEST FAILED: {e}")
        return 1
    except Exception as e:
        print(f"\n❌ ERROR: {e}")
        import traceback
        traceback.print_exc()
        return 1
    
    return 0


if __name__ == "__main__":
    exit_code = asyncio.run(main())
    exit(exit_code)
