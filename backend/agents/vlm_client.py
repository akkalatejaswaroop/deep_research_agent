import os
import json
import base64
import requests


VLM_API_KEY = os.getenv("VLM_API_KEY", "")
VLM_MODEL = os.getenv("VLM_MODEL", "")


def vlm_read_image(image_bytes: bytes, prompt: str) -> str:
    if not VLM_API_KEY or not VLM_MODEL:
        return ""
    b64 = base64.b64encode(image_bytes).decode()

    if "claude" in VLM_MODEL.lower():
        return _read_claude(b64, prompt)
    elif "gpt" in VLM_MODEL.lower() or "o1" in VLM_MODEL.lower() or "o3" in VLM_MODEL.lower():
        return _read_openai(b64, prompt)
    return ""


def _read_claude(b64_image: str, prompt: str) -> str:
    headers = {
        "x-api-key": VLM_API_KEY,
        "anthropic-version": "2023-06-01",
        "content-type": "application/json",
    }
    body = {
        "model": VLM_MODEL,
        "max_tokens": 4096,
        "messages": [{
            "role": "user",
            "content": [
                {"type": "text", "text": prompt},
                {"type": "image", "source": {
                    "type": "base64",
                    "media_type": "image/png",
                    "data": b64_image
                }}
            ]
        }]
    }
    try:
        r = requests.post(
            "https://api.anthropic.com/v1/messages",
            json=body, headers=headers, timeout=60
        )
        data = r.json()
        return data.get("content", [{}])[0].get("text", "")
    except Exception as e:
        print(f"Claude VLM error: {e}")
        return ""


def _read_openai(b64_image: str, prompt: str) -> str:
    headers = {
        "Authorization": f"Bearer {VLM_API_KEY}",
        "Content-Type": "application/json",
    }
    body = {
        "model": VLM_MODEL,
        "max_tokens": 4096,
        "messages": [{
            "role": "user",
            "content": [
                {"type": "text", "text": prompt},
                {"type": "image_url", "image_url": {
                    "url": f"data:image/png;base64,{b64_image}",
                    "detail": "high"
                }}
            ]
        }]
    }
    try:
        r = requests.post(
            "https://api.openai.com/v1/chat/completions",
            json=body, headers=headers, timeout=60
        )
        data = r.json()
        return data.get("choices", [{}])[0].get("message", {}).get("content", "")
    except Exception as e:
        print(f"OpenAI VLM error: {e}")
        return ""
