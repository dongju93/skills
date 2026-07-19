import requests

BASE = "https://api.example.com"


def get_user(user_id: int) -> dict:
    response = requests.get(f"{BASE}/users/{user_id}", timeout=10)
    response.raise_for_status()
    return response.json()
