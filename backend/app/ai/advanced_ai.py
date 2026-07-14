import requests

OLLAMA_URL = "http://localhost:11434/api/generate"

def ask_llm(message):

    prompt = f"""
Answer in 1 or 2 short sentences only.
Be concise.
User: {message}
"""

    response = requests.post(
        OLLAMA_URL,
        json={
            "model": "phi3:mini",
            "prompt": prompt,
            "stream": False,
            "options": {
                "num_predict": 40,
                "temperature": 0.2
            }
        }
    )

    return response.json()["response"]