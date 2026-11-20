"""Quick auth test script - run this to verify backend is working"""
import requests
import json

BASE_URL = "http://localhost:8000"

def test_health():
    print("\n1️⃣  Testing Health Endpoint...")
    response = requests.get(f"{BASE_URL}/health")
    print(f"Status: {response.status_code}")
    print(f"Response: {response.json()}")
    return response.status_code == 200

def test_register():
    print("\n2️⃣  Testing Register...")
    data = {
        "email": "test_user@example.com",
        "password": "TestPass123!",
        "role": "borrower"
    }
    response = requests.post(f"{BASE_URL}/auth/register", json=data)
    print(f"Status: {response.status_code}")
    try:
        print(f"Response: {response.json()}")
        return response.status_code in [201, 409]  # 409 if user already exists
    except:
        print(f"Response text: {response.text}")
        return False

def test_login():
    print("\n3️⃣  Testing Login...")
    data = {
        "email": "test_user@example.com",
        "password": "TestPass123!",
        "remember_me": False
    }
    response = requests.post(f"{BASE_URL}/auth/login", json=data)
    print(f"Status: {response.status_code}")
    try:
        resp_json = response.json()
        print(f"Response keys: {resp_json.keys()}")
        
        if "access_token" in resp_json:
            token = resp_json["access_token"]
            print(f"✅ Access token received: {token[:30]}...")
            return token
        else:
            print(f"❌ No access_token in response: {resp_json}")
            return None
    except Exception as e:
        print(f"Error parsing response: {e}")
        print(f"Response text: {response.text}")
        return None

def test_protected_endpoint(token):
    print("\n4️⃣  Testing Protected Endpoint with Token...")
    headers = {"Authorization": f"Bearer {token}"}
    response = requests.get(f"{BASE_URL}/shops/me", headers=headers)
    print(f"Status: {response.status_code}")
    print(f"Response: {response.json()}")
    return response.status_code == 200

def test_reconciliation(token):
    print("\n5️⃣  Testing Reconciliation Endpoint...")
    headers = {"Authorization": f"Bearer {token}"}
    data = {
        "shop_id": "test_shop_1",
        "gstin": "29AABCR0102R1Z5",
        "shop_category": "pharmacy",
        "purchases": 200000,
        "gst_turnover": 250000,
        "upi_turnover": 150000
    }
    response = requests.post(f"{BASE_URL}/reconcile", json=data, headers=headers)
    print(f"Status: {response.status_code}")
    try:
        result = response.json()
        print(f"Verdict: {result.get('verdict')}")
        print(f"Reason: {result.get('reason')}")
        return response.status_code == 200
    except:
        print(f"Response text: {response.text}")
        return False

if __name__ == "__main__":
    print("=" * 60)
    print("UdyamCred Backend - Auth & API Test")
    print("=" * 60)
    
    try:
        # Test health
        if not test_health():
            print("❌ Backend is not responding. Make sure it's running!")
            exit(1)
        
        # Test register
        test_register()
        
        # Test login and get token
        token = test_login()
        if not token:
            print("❌ Login failed")
            exit(1)
        
        # Test protected endpoint
        if test_protected_endpoint(token):
            print("✅ Token authentication working!")
        else:
            print("❌ Token authentication failed")
            exit(1)
        
        # Test reconciliation
        if test_reconciliation(token):
            print("✅ Reconciliation endpoint working!")
        else:
            print("❌ Reconciliation endpoint failed")
            exit(1)
        
        print("\n" + "=" * 60)
        print("✅ ALL TESTS PASSED!")
        print("=" * 60)
        
    except requests.exceptions.ConnectionError:
        print("\n❌ ERROR: Cannot connect to backend!")
        print("Make sure backend is running:")
        print("  cd d:\\Hackathon\\udyam-cred\\be")
        print("  .\\venv\\Scripts\\Activate.ps1")
        print("  uvicorn main:app --reload")
        exit(1)
    except Exception as e:
        print(f"\n❌ Unexpected error: {e}")
        exit(1)
