import requests
import json

url = "http://127.0.0.1:8000/api/v1/investigate"
payload = {
    "raw_input": "Your profile selected at Infosys. Salary 45k. Fee Rs.2499. Register at infosys-careers.in immediately! Contact us at hr@infosys-careers.in or +91 8888888888",
    "input_type": "paste"
}

try:
    print(f"Testing endpoint: {url}")
    response = requests.post(url, json=payload, timeout=30)
    print(f"Status Code: {response.status_code}")
    print(json.dumps(response.json(), indent=2))
except Exception as e:
    print(f"Error: {e}")
