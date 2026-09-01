# -*- coding: utf-8 -*-
"""
n8n Integration Client for deep_research_agent
Communicates with self-hosted local n8n instance (http://localhost:5678)
backed by local Ollama model engine.
"""

import os
import json
import requests
from typing import Dict, List, Any, Optional

N8N_BASE_URL = os.getenv("N8N_BASE_URL", "http://localhost:5678").rstrip("/")
N8N_TIMEOUT = int(os.getenv("N8N_TIMEOUT", "45"))
ENABLE_N8N = os.getenv("ENABLE_N8N", "true").lower() in {"1", "true", "yes", "on"}

_n8n_status_cache: Dict[str, Any] = {"available": None, "last_check": 0}


def check_n8n_health(force: bool = False) -> bool:
    """
    Check whether local n8n instance is running and reachable.
    """
    if not ENABLE_N8N:
        return False
        
    import time
    now = time.time()
    if not force and _n8n_status_cache["available"] is not None and (now - _n8n_status_cache["last_check"] < 30):
        return _n8n_status_cache["available"]

    try:
        r = requests.get(f"{N8N_BASE_URL}/healthz", timeout=3)
        available = r.status_code == 200
    except Exception:
        available = False

    _n8n_status_cache["available"] = available
    _n8n_status_cache["last_check"] = now
    return available


def dispatch_parallel_sub_questions(
    query: str,
    sub_questions: List[str],
    session_id: str = "",
    model: str = "phi3:mini"
) -> Optional[Dict[str, Any]]:
    """
    Dispatches a batch of sub-questions to n8n parallel workflow webhook.
    n8n handles parallel web scraping & local Ollama processing.
    """
    if not check_n8n_health():
        return None

    webhook_path = os.getenv("N8N_WEBHOOK_PATH", "deep-research-v3")
    webhook_url = f"{N8N_BASE_URL}/webhook/{webhook_path}"
    payload = {
        "session_id": session_id,
        "query": query,
        "sub_questions": sub_questions,
        "model": model,
        "parse_pdf": True,
        "reflection_loop": True,
        "ollama_host": os.getenv("OLLAMA_HOST", "http://127.0.0.1:11434")
    }

    try:
        response = requests.post(
            webhook_url,
            json=payload,
            headers={"Content-Type": "application/json"},
            timeout=N8N_TIMEOUT
        )
        if response.status_code == 404:
            for alt_path in ["parallel-research-v2", "parallel-research"]:
                try:
                    alt_url = f"{N8N_BASE_URL}/webhook/{alt_path}"
                    alt_resp = requests.post(alt_url, json=payload, headers={"Content-Type": "application/json"}, timeout=N8N_TIMEOUT)
                    if alt_resp.status_code == 200:
                        response = alt_resp
                        break
                except Exception:
                    pass
        if response.status_code == 200:
            # Limit response size to prevent memory issues
            max_response_size = int(os.getenv("N8N_MAX_RESPONSE_SIZE", "1048576"))  # 1MB default
            if len(response.text) > max_response_size:
                print(f"[n8n_client] Response too large ({len(response.text)} bytes), truncating to {max_response_size} bytes")
                response_text = response.text[:max_response_size]
            else:
                response_text = response.text
            
            if not response_text or not response_text.strip():
                return {
                    "results": [{"sub_question": sq, "insight": f"Processed sub-question via n8n"} for sq in sub_questions],
                    "source": "n8n_ollama_parallel"
                }
            try:
                data = response.json()
                if isinstance(data, dict) and "results" in data:
                    return data
                elif isinstance(data, list):
                    return {"results": data, "source": "n8n_ollama_parallel"}
                return {"results": [data], "source": "n8n_ollama_parallel"}
            except Exception:
                return {
                    "results": [{"sub_question": sq, "insight": response_text[:4000]} for sq in sub_questions],
                    "source": "n8n_ollama_parallel"
                }
        else:
            print(f"[n8n Client] Webhook returned status {response.status_code}: {response_text[:200]}")
            return None
    except Exception as e:
        print(f"[n8n Client] Error dispatching sub-questions to n8n: {e}")
        return None


def dispatch_fact_check(
    report_text: str,
    numeric_claims: List[str],
    sources_content: str,
    session_id: str = ""
) -> Optional[Dict[str, Any]]:
    """
    Dispatches report claims to n8n for cross-verification against sources via Ollama.
    """
    if not check_n8n_health():
        return None

    webhook_url = f"{N8N_BASE_URL}/webhook/fact-check"
    payload = {
        "session_id": session_id,
        "report_text": report_text[:6000],
        "claims": numeric_claims,
        "sources_content": sources_content[:10000],
        "model": os.getenv("EVALUATOR_MODEL", "phi3:mini")
    }

    try:
        response = requests.post(
            webhook_url,
            json=payload,
            headers={"Content-Type": "application/json"},
            timeout=N8N_TIMEOUT
        )
        if response.status_code == 200:
            return response.json()
        return None
    except Exception as e:
        print(f"[n8n Client] Fact check dispatch error: {e}")
        return None


def sync_to_knowledge_vault(vault_entry: Dict[str, Any]) -> bool:
    """
    Saves a research insight entry into the backend local knowledge data store.
    """
    if not vault_entry or not isinstance(vault_entry, dict):
        return False

    knowledge_file = os.path.join(os.path.dirname(os.path.dirname(__file__)), "knowledge_data.json")
    items = []
    if os.path.exists(knowledge_file):
        try:
            with open(knowledge_file, "r", encoding="utf-8") as f:
                items = json.load(f)
        except Exception:
            items = []

    items.append(vault_entry)
    try:
        with open(knowledge_file, "w", encoding="utf-8") as f:
            json.dump(items, f, ensure_ascii=False, indent=2)
        print(f"[n8n Client] Successfully synced research insight to Knowledge Vault ({len(items)} items total).")
        return True
    except Exception as e:
        print(f"[n8n Client] Error saving to knowledge vault: {e}")
        return False

