import requests
import json

url = "http://localhost:8001/api/search"
payload = {
    "refined": "test query",
    "threads": 5,
    "max_results": 10,
    "request_timeout": 30,
    "use_cache": True,
    "load_cached_only": False
}
headers = {
    "Content-Type": "application/json"
}

try:
    print(f"Sending request to {url} with payload: {json.dumps(payload, indent=2)}")
    response = requests.post(url, json=payload, headers=headers)
    print(f"Status Code: {response.status_code}")
    if response.status_code == 200:
        data = response.json()
        print(f"Success! Got {len(data.get('results', []))} results.")
        print(json.dumps(data, indent=2))
    else:
        print("Error response:")
        print(response.text)
except Exception as e:
    print(f"Exception: {e}")
