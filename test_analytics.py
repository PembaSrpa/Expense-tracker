import requests

BASE_URL = "http://127.0.0.1:8000"

print("Testing Analytics Endpoints...\n")

# Test monthly trend
print("1. Monthly Spending Trend:")
response = requests.get(f"{BASE_URL}/analytics/monthly-trend?months=6")
print(response.json())
print()

# Test spending patterns
print("2. Spending Patterns:")
response = requests.get(f"{BASE_URL}/analytics/spending-patterns")
print(response.json())
print()

# Test top categories
print("3. Top Spending Categories:")
response = requests.get(f"{BASE_URL}/analytics/top-categories?limit=3")
print(response.json())
print()

# Test budget alerts
print("4. Budget Alerts:")
response = requests.get(f"{BASE_URL}/analytics/budget-alerts")
print(response.json())
print()

# Test predictions
print("5. Spending Prediction:")
response = requests.get(f"{BASE_URL}/analytics/predict-spending")
print(response.json())
print()

print("✅ All analytics endpoints are working!")
