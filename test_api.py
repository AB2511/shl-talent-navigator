"""
Quick API test script for manual testing.
Run after starting the server to verify functionality.
"""
import requests
import json


BASE_URL = "http://localhost:8000"


def test_health():
    """Test health endpoint."""
    print("Testing /health endpoint...")
    response = requests.get(f"{BASE_URL}/health")
    print(f"Status: {response.status_code}")
    print(f"Response: {json.dumps(response.json(), indent=2)}\n")


def test_chat_clarification():
    """Test chat with vague query."""
    print("Testing chat with vague query...")
    payload = {
        "messages": [
            {"role": "user", "content": "I need an assessment"}
        ]
    }
    response = requests.post(f"{BASE_URL}/chat", json=payload)
    print(f"Status: {response.status_code}")
    data = response.json()
    print(f"State: {data['state']}")
    print(f"Response: {data['response'][:200]}...\n")


def test_chat_recommendation():
    """Test chat with specific query."""
    print("Testing chat with specific query...")
    payload = {
        "messages": [
            {
                "role": "user",
                "content": "I need a cognitive assessment for leadership roles"
            }
        ]
    }
    response = requests.post(f"{BASE_URL}/chat", json=payload)
    print(f"Status: {response.status_code}")
    data = response.json()
    print(f"State: {data['state']}")
    print(f"Response: {data['response'][:200]}...")
    print(f"Assessments returned: {len(data['assessments'])}")
    if data['assessments']:
        print(f"First assessment: {data['assessments'][0]['name']}\n")


def test_chat_refusal():
    """Test chat with off-topic query."""
    print("Testing chat with off-topic query...")
    payload = {
        "messages": [
            {"role": "user", "content": "What's the weather today?"}
        ]
    }
    response = requests.post(f"{BASE_URL}/chat", json=payload)
    print(f"Status: {response.status_code}")
    data = response.json()
    print(f"State: {data['state']}")
    print(f"Response: {data['response']}\n")


def test_chat_refinement():
    """Test chat with refinement."""
    print("Testing chat with refinement...")
    payload = {
        "messages": [
            {"role": "user", "content": "I need cognitive assessments"},
            {
                "role": "assistant",
                "content": "Here are some cognitive assessments: SHL Verify G+ (ID: shl-verify-g-plus)"
            },
            {"role": "user", "content": "Show me shorter alternatives under 20 minutes"}
        ]
    }
    response = requests.post(f"{BASE_URL}/chat", json=payload)
    print(f"Status: {response.status_code}")
    data = response.json()
    print(f"State: {data['state']}")
    print(f"Assessments returned: {len(data['assessments'])}\n")


if __name__ == "__main__":
    print("=" * 60)
    print("SHL Talent Navigator API Test Suite")
    print("=" * 60 + "\n")
    
    try:
        test_health()
        test_chat_clarification()
        test_chat_recommendation()
        test_chat_refusal()
        test_chat_refinement()
        
        print("=" * 60)
        print("All tests completed!")
        print("=" * 60)
    
    except requests.exceptions.ConnectionError:
        print("ERROR: Could not connect to server.")
        print("Make sure the server is running: uvicorn app.main:app --reload")
    except Exception as e:
        print(f"ERROR: {e}")
