import requests
import os


def generate_response(user_input: str):
    api_url = "https://generativelanguage.googleapis.com/v1beta2/models/text-bison:generateText"
    api_key = os.getenv("GEMINI_API_KEY")

    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json"
    }

    data = {
        "prompt": user_input,
        "temperature": 0.7,
        "maxOutputTokens": 100
    }

    response = requests.post(api_url, headers=headers, json=data)

    if response.status_code == 200:
        return response.json()["candidates"][0]["content"]
    else:
        return "Произошла ошибка при обработке запроса."

