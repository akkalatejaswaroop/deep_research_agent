import os
import requests
import json


def call_api_llm(model: str, system_prompt: str, user_prompt: str) -> str:
    if not os.getenv("API_LLM_API_KEY", ""):
        return ""
    if "claude" in model.lower():
        return _call_claude(model, system_prompt, user_prompt)
    return _call_openai_compat(model, system_prompt, user_prompt)


def _call_claude(model: str, system_prompt: str, user_prompt: str) -> str:
    api_key = os.getenv("API_LLM_API_KEY", "")
    headers = {
        "x-api-key": api_key,
        "anthropic-version": "2023-06-01",
        "content-type": "application/json",
    }
    body = {
        "model": model,
        "max_tokens": 4096,
        "system": system_prompt,
        "messages": [{"role": "user", "content": user_prompt}]
    }
    llm_timeout = int(os.getenv("LLM_TIMEOUT", "120"))
    try:
        r = requests.post(
            "https://api.anthropic.com/v1/messages",
            json=body, headers=headers, timeout=llm_timeout
        )
        data = r.json()
        return data.get("content", [{}])[0].get("text", "")
    except Exception as e:
        print(f"Claude LLM error: {e}")
        return ""


def _call_openai_compat(model: str, system_prompt: str, user_prompt: str) -> str:
    api_key = os.getenv("API_LLM_API_KEY", "")
    base = os.getenv("API_LLM_BASE_URL", "") or "https://api.openai.com/v1"
    headers = {
        "Authorization": f"Bearer {api_key}",
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
    llm_timeout = int(os.getenv("LLM_TIMEOUT", "120"))
    try:
        r = requests.post(
            f"{base}/chat/completions",
            json=body, headers=headers, timeout=llm_timeout
        )
        data = r.json()
        return data.get("choices", [{}])[0].get("message", {}).get("content", "")
    except Exception as e:
        print(f"API LLM error ({model}): {e}")
        return ""
