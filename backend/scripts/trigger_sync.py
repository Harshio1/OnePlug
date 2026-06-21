import requests
import json

base_url = "http://localhost:8001/api/v1"

# 1. Login to get access token
login_url = f"{base_url}/auth/login"
login_payload = {
    "username": "admin",
    "password": "oneplug2026"
}

print(f"Logging in to {login_url}...")
try:
    login_response = requests.post(login_url, json=login_payload)
    print(f"Login Status: {login_response.status_code}")
    login_data = login_response.json()
    token = login_data.get("access_token")
    if not token:
        print("Failed to get access token from login response:", login_data)
        exit(1)
    print("Logged in successfully!")
except Exception as e:
    print(f"Login failed: {e}")
    exit(1)

# 2. Trigger MyOperator Sync
sync_url = f"{base_url}/transcribe/sync-myoperator"
headers = {
    "Authorization": f"Bearer {token}"
}

print(f"\nTriggering MyOperator Sync at {sync_url}...")
try:
    # Set timeout to 120s to allow sync to complete first batch of logs/downloads
    sync_response = requests.post(sync_url, headers=headers, timeout=120)
    print(f"Sync Response Status Code: {sync_response.status_code}")
    print("Sync Response JSON Body:")
    print(json.dumps(sync_response.json(), indent=2))
except Exception as e:
    print(f"Sync failed: {e}")
