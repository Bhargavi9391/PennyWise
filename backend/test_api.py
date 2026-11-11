
import requests

url = "http://127.0.0.1:5000/api/transactions"

data = {
    "name": "Test Transaction",
    "category": "Food & Dining",
    "amount": 500,
    "date": "2026-11-10",
    "transaction_type": "Expense"
}

response = requests.post(url, json=data)

print("Status Code:", response.status_code)
print("Response:", response.json())
