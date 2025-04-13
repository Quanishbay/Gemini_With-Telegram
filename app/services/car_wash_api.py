import requests

CAR_WASH_BASE_URL = "http://127.0.0.1:8000"

def get_categories():
    response = requests.get(f"{CAR_WASH_BASE_URL}/api/categories/all-categories")
    if response.status_code == 200:
        return response.json()
    return []

def get_services():
    response = requests.get(f"{CAR_WASH_BASE_URL}/api/car-washes/services")
    if response.status_code == 200:
        return response.json()
    return []

def get_washes():
    response = requests.get(f"{CAR_WASH_BASE_URL}/api/car-washes/get-washes")
    if response.status_code == 200:
        return response.json()
    return []
