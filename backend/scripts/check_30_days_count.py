import os
import time
import requests
from dotenv import load_dotenv

dotenv_path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), ".env")
load_dotenv(dotenv_path)

AUTH_KEY = os.getenv("MYOPERATOR_AUTH_KEY")
search_url = "https://developers.myoperator.co/search"
headers = {
    "x-api-key": AUTH_KEY
}

now_ts = int(time.time())
thirty_days_ago = now_ts - (30 * 24 * 60 * 60)

print(f"Querying MyOperator call count for last 30 days...")
print(f"Range: {thirty_days_ago} -> {now_ts}")

try:
    response = requests.post(search_url, headers=headers, data={
        "from": thirty_days_ago,
        "to": now_ts,
        "limit": 1
    })
    print("Status:", response.status_code)
    data = response.json()
    print("Total calls in last 30 days:", data.get("data", {}).get("total"))
except Exception as e:
    print("Error:", e)
