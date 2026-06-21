import os
import requests
from dotenv import load_dotenv

# Load env variables
dotenv_path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), ".env")
load_dotenv(dotenv_path)

COMPANY_ID = os.getenv("MYOPERATOR_COMPANY_ID")
AUTH_KEY = os.getenv("MYOPERATOR_AUTH_KEY")
X_API_KEY = os.getenv("MYOPERATOR_X_API_KEY")
SECRET_KEY = os.getenv("MYOPERATOR_SECRET_KEY")

keys = {
    "AUTH_KEY": AUTH_KEY,
    "X_API_KEY": X_API_KEY,
    "SECRET_KEY": SECRET_KEY
}

print("Starting extensive MyOperator authentication test script...")

# Try passing token in query params
for name, val in keys.items():
    if not val:
        continue
    url = f"https://developers.myoperator.co/search?token={val}"
    try:
        response = requests.post(url, data={"limit": 1})
        print(f"[Query Param Token] Key: {name} | Status: {response.status_code} | Body: {response.text}")
    except Exception as e:
        print(f"Error {name}: {e}")

# Try passing token in POST body
for name, val in keys.items():
    if not val:
        continue
    url = "https://developers.myoperator.co/search"
    try:
        response = requests.post(url, data={"token": val, "limit": 1})
        print(f"[POST Body Token] Key: {name} | Status: {response.status_code} | Body: {response.text}")
    except Exception as e:
        print(f"Error {name}: {e}")

# Try passing x-api-key header and company-id in header/params
for name, val in keys.items():
    if not val:
        continue
    url = "https://developers.myoperator.co/search"
    headers = {
        "x-api-key": val,
        "Authorization": f"Bearer {val}"
    }
    try:
        response = requests.post(url, headers=headers, data={"limit": 1})
        print(f"[Headers] Key: {name} | Status: {response.status_code} | Body: {response.text}")
    except Exception as e:
        print(f"Error {name}: {e}")

# Try passing with company-id as parameter if required
for name, val in keys.items():
    if not val:
        continue
    url = f"https://developers.myoperator.co/search?token={val}"
    try:
        response = requests.post(url, data={"limit": 1, "company_id": COMPANY_ID})
        print(f"[Query + CompanyID] Key: {name} | Status: {response.status_code} | Body: {response.text}")
    except Exception as e:
        print(f"Error {name}: {e}")
