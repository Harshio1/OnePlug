import os
import json
import requests
from dotenv import load_dotenv

dotenv_path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), ".env")
load_dotenv(dotenv_path)

AUTH_KEY = os.getenv("MYOPERATOR_AUTH_KEY")
search_url = "https://developers.myoperator.co/search"
headers = {
    "x-api-key": AUTH_KEY
}

print("--- Testing MyOperator Pagination and Date Filtering ---")

# Step 1: Fetch first record (Offset 0)
print("\n[Step 1] Fetching first record (limit=1)...")
res0 = requests.post(search_url, headers=headers, data={"limit": 1})
id0 = res0.json().get("data", {}).get("hits", [])[0].get("user_id")
print(f"Record 0 user_id: {id0}")

# Step 2: Test pagination offset using 'log_from'
print("\n[Step 2] Testing offset using 'log_from' = 1...")
res_log_from = requests.post(search_url, headers=headers, data={"limit": 1, "log_from": 1})
hits_log_from = res_log_from.json().get("data", {}).get("hits", [])
id_log_from = hits_log_from[0].get("user_id") if hits_log_from else "None"
print(f"Record offset (log_from=1) user_id: {id_log_from}")

# Step 3: Test pagination offset using 'offset'
print("\n[Step 3] Testing offset using 'offset' = 1...")
res_offset = requests.post(search_url, headers=headers, data={"limit": 1, "offset": 1})
hits_offset = res_offset.json().get("data", {}).get("hits", [])
id_offset = hits_offset[0].get("user_id") if hits_offset else "None"
print(f"Record offset (offset=1) user_id: {id_offset}")

# Step 4: Test Date Filtering using 'from' and 'to' in POST body
# From the logs, one call had start_time = 1781785973.
# Let's filter for start_time between 1781785900 and 1781786010.
print("\n[Step 4] Testing date filtering using 'from' and 'to' in POST body...")
res_date = requests.post(search_url, headers=headers, data={
    "limit": 5,
    "from": 1781785900,
    "to": 1781786010
})
date_json = res_date.json()
print("Date Filter Response Status:", date_json.get("status"))
hits_date = date_json.get("data", {}).get("hits", [])
print(f"Number of hits found in date range: {len(hits_date)}")
for h in hits_date:
    src = h.get("_source", {})
    print(f"  Call user_id: {h.get('user_id')} | Start Time: {src.get('start_time')} | Filename: {src.get('filename')}")
