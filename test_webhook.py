"""
Test script for Salsify webhook integration.

This script simulates a Salsify webhook POST request to test the integration.
"""

import os
import requests
import json
import time

WEBHOOK_URL = "http://localhost:5000/api/salsify/webhook"
STATUS_URL = "http://localhost:5000/api/salsify/status"

WEBHOOK_SECRET = os.environ.get('SALSIFY_WEBHOOK_SECRET', 'test-secret-key')

def test_webhook_auth():
    """Test webhook authentication"""
    print("\n=== Testing Webhook Authentication ===")
    
    payload = {
        "channel_id": "test-channel-123",
        "channel_name": "Test Channel",
        "user_id": "test-user-456",
        "publication_status": "completed",
        "product_feed_export_url": "https://example.com/test.xlsx"
    }
    
    print("1. Testing without key (should fail)...")
    response = requests.post(WEBHOOK_URL, json=payload)
    print(f"   Status: {response.status_code} (expected: 401)")
    print(f"   Response: {response.json()}")
    
    print("\n2. Testing with wrong key (should fail)...")
    response = requests.post(f"{WEBHOOK_URL}?key=wrong-key", json=payload)
    print(f"   Status: {response.status_code} (expected: 401)")
    print(f"   Response: {response.json()}")
    
    print("\n3. Testing with correct key (should succeed)...")
    response = requests.post(f"{WEBHOOK_URL}?key={WEBHOOK_SECRET}", json=payload)
    print(f"   Status: {response.status_code} (expected: 202)")
    print(f"   Response: {response.json()}")
    
    if response.status_code == 202:
        sync_id = response.json().get('sync_id')
        return sync_id
    
    return None


def test_webhook_payload_validation():
    """Test webhook payload validation"""
    print("\n=== Testing Webhook Payload Validation ===")
    
    print("1. Testing with empty payload (should fail)...")
    response = requests.post(f"{WEBHOOK_URL}?key={WEBHOOK_SECRET}", json={})
    print(f"   Status: {response.status_code}")
    print(f"   Response: {response.json()}")
    
    print("\n2. Testing with failed status (should be ignored)...")
    payload = {
        "publication_status": "failed",
        "product_feed_export_url": "https://example.com/test.xlsx"
    }
    response = requests.post(f"{WEBHOOK_URL}?key={WEBHOOK_SECRET}", json=payload)
    print(f"   Status: {response.status_code}")
    print(f"   Response: {response.json()}")
    
    print("\n3. Testing with missing URL (should fail)...")
    payload = {
        "publication_status": "completed"
    }
    response = requests.post(f"{WEBHOOK_URL}?key={WEBHOOK_SECRET}", json=payload)
    print(f"   Status: {response.status_code}")
    print(f"   Response: {response.json()}")


def test_status_endpoint(sync_id=None):
    """Test status endpoint"""
    print("\n=== Testing Status Endpoint ===")
    
    print("1. Testing list all syncs...")
    response = requests.get(STATUS_URL)
    print(f"   Status: {response.status_code}")
    data = response.json()
    print(f"   Total syncs returned: {data.get('total_returned', 0)}")
    if data.get('syncs'):
        print(f"   Latest sync: {data['syncs'][0]}")
    
    if sync_id:
        print(f"\n2. Testing get specific sync (ID: {sync_id})...")
        response = requests.get(f"{STATUS_URL}?sync_id={sync_id}")
        print(f"   Status: {response.status_code}")
        print(f"   Response: {json.dumps(response.json(), indent=2)}")
    
    print("\n3. Testing with limit parameter...")
    response = requests.get(f"{STATUS_URL}?limit=3")
    print(f"   Status: {response.status_code}")
    data = response.json()
    print(f"   Total syncs returned: {data.get('total_returned', 0)}")


def test_mock_salsify_webhook():
    """Test with realistic Salsify webhook payload"""
    print("\n=== Testing Mock Salsify Webhook ===")
    
    payload = {
        "channel_id": "s-00000000-0000-0000-0000-000000000000",
        "channel_name": "My Channel",
        "user_id": "s-00000000-0000-0000-0000-000000000000",
        "publication_status": "completed",
        "product_feed_export_url": "https://example.com/path/to/export.xlsx",
        "digital_asset_export_url": "https://example.com/path/to/assets.zip"
    }
    
    print("Sending webhook with realistic Salsify payload...")
    print(f"Payload: {json.dumps(payload, indent=2)}")
    
    response = requests.post(f"{WEBHOOK_URL}?key={WEBHOOK_SECRET}", json=payload)
    print(f"\nStatus: {response.status_code}")
    print(f"Response: {json.dumps(response.json(), indent=2)}")
    
    if response.status_code == 202:
        sync_id = response.json().get('sync_id')
        print(f"\nSync ID: {sync_id}")
        
        print("\nWaiting 2 seconds for background processing...")
        time.sleep(2)
        
        print("\nChecking sync status...")
        response = requests.get(f"{STATUS_URL}?sync_id={sync_id}")
        print(f"Status: {response.status_code}")
        print(f"Response: {json.dumps(response.json(), indent=2)}")
        
        return sync_id
    
    return None


def main():
    """Run all tests"""
    print("=" * 60)
    print("Salsify Webhook Integration Test Suite")
    print("=" * 60)
    print(f"Webhook URL: {WEBHOOK_URL}")
    print(f"Status URL: {STATUS_URL}")
    print(f"Webhook Secret: {WEBHOOK_SECRET[:4]}{'*' * (len(WEBHOOK_SECRET) - 4)}")
    
    try:
        sync_id = test_webhook_auth()
        test_webhook_payload_validation()
        test_status_endpoint(sync_id)
        
        print("\n" + "=" * 60)
        print("Running full integration test...")
        print("=" * 60)
        mock_sync_id = test_mock_salsify_webhook()
        
        print("\n" + "=" * 60)
        print("Test Summary")
        print("=" * 60)
        print("✓ Authentication tests completed")
        print("✓ Payload validation tests completed")
        print("✓ Status endpoint tests completed")
        print("✓ Mock webhook integration test completed")
        
        if mock_sync_id:
            print(f"\nNote: Sync ID {mock_sync_id} attempted to download from example.com")
            print("This will fail because it's a mock URL, but the webhook flow is working!")
        
    except requests.exceptions.ConnectionError:
        print("\n❌ ERROR: Could not connect to Flask app.")
        print("Make sure the Flask app is running on http://localhost:5000")
        print("Run: python3 app.py")
    except Exception as e:
        print(f"\n❌ ERROR: {str(e)}")
        import traceback
        traceback.print_exc()


if __name__ == '__main__':
    main()
