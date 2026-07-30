import os
import requests
import json


API_LLM_API_KEY = os.getenv("API_LLM_API_KEY", "")
API_LLM_BASE_URL = os.getenv("API_LLM_BASE_URL", "")


def call_api_llm(model: str, system_prompt: str, user_prompt: str) -> str:
    if not API_LLM_API_KEY:
        return ""
    if "claude" in model.lower():
        return _call_claude(model, system_prompt, user_prompt)
    return _call_openai_compat(model, system_prompt, user_prompt)


def _call_claude(model: str, system_prompt: str, user_prompt: str) -> str:
    headers = {
        "x-api-key": API_LLM_API_KEY,
        "anthropic-version": "2023-06-01",
        "content-type": "application/json",
    }
    body = {
        "model": model,
        "max_tokens": 4096,
        "system": system_prompt,
        "messages": [{"role": "user", "content": user_prompt}]
    }
    try:
        r = requests.post(
            "https://api.anthropic.com/v1/messages",
            json=body, headers=headers, timeout=60
        )
        data = r.json()
        return data.get("content", [{}])[0].get("text", "")
    except Exception as e:
        print(f"Claude LLM error: {e}")
        return ""


def _call_openai_compat(model: str, system_prompt: str, user_prompt: str) -> str:
    base = API_LLM_BASE_URL or "https://api.openai.com/v1"
    headers = {
        "Authorization": f"Bearer {API_LLM_API_KEY}",
        "Content-Type": "application/json",
    }
    body = {
        "model": model,
        "max_tokens": 4096,
        "messages": [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt}
        ]
    }
    try:
        r = requests.post(
            f"{base}/chat/completions",
            json=body, headers=headers, timeout=60
        )
        data = r.json()
        return data.get("choices", [{}])[0].get("message", {}).get("content", "")
    except Exception as e:
        print(f"API LLM error ({model}): {e}")
        return ""
