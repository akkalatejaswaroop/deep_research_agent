# -*- coding: utf-8 -*-
"""Full End-to-End Integration Verification Script for REX Deep Research Agent."""
import sys
import os
import json
from unittest.mock import patch
from fastapi.testclient import TestClient

try:
    import backend.main as main_module
except ImportError:
    import main as main_module  # type: ignore

def log(msg: str):
    print(f"[E2E Test] {msg}", flush=True)

def run_e2e_test():
    client = TestClient(main_module.app)

    # 1. Health check endpoint
    log("Testing GET /health...")
    res = client.get("/health")
    assert res.status_code == 200, f"Health check failed: {res.status_code}"
    assert res.json().get("status") == "ok"
    log("GET /health PASSED!")

    # 2. SSE Research Stream endpoint
    log("Testing POST /api/v1/research/ SSE Stream...")
    mock_sources = [
        {"url": "https://example.com/energy", "title": "AI Grid Management", "domain": "example.com", "content": "Sample content about AI and smart grids."}
    ]

    os.environ["SIMULATED_MODE"] = "true"
    with patch.object(main_module, "app_graph", None), \
         patch.object(main_module, "search_all_sources", return_value=mock_sources), \
         patch.object(main_module, "search_web_duckduckgo", return_value=mock_sources), \
         patch.object(main_module, "search_wikipedia", return_value=[]), \
         patch.object(main_module, "call_llm", return_value="Verified synthesis response."):

        res = client.post(
            "/api/v1/research/",
            json={"query": "AI in Smart Grid Management", "depth": 1, "complexity": 1, "paragraphs": 1, "subQuestions": 2}
        )

        assert res.status_code == 200, f"Research endpoint failed: {res.status_code}"
        session_id = res.headers.get("X-Session-Id")
        log(f"Received Session ID: {session_id}")

        nodes_received = set()
        received_report = False
        received_metrics = False

        for line in res.text.splitlines():
            line = line.strip()
            if line.startswith("data: "):
                data_str = line[6:]
                if data_str == "[DONE]":
                    break
                try:
                    event = json.loads(data_str)
                    node = event.get("node")
                    if node:
                        nodes_received.add(node)
                        log(f"  Received SSE event node: {node}")
                    if node == "end":
                        if "report" in event:
                            received_report = True
                            log(f"  Final report received! Length: {len(event['report'])} chars")
                        if "metrics" in event:
                            received_metrics = True
                            log("  Metrics payload received!")
                except Exception:
                    pass

        log(f"Nodes executed: {sorted(list(nodes_received))}")
        assert "start" in nodes_received, "Missing 'start' node"
        assert "end" in nodes_received, "Missing 'end' node"
        assert received_report, "Missing report content in 'end' event"
        assert received_metrics, "Missing metrics payload in 'end' event"
        log("POST /api/v1/research/ SSE Stream PASSED!")

    # 3. Sessions Endpoint
    log("Testing GET /api/v1/sessions...")
    res_sess = client.get("/api/v1/sessions")
    assert res_sess.status_code == 200, "Sessions endpoint failed"
    sessions_list = res_sess.json()
    assert len(sessions_list) > 0, "No sessions recorded"
    log(f"GET /api/v1/sessions PASSED! ({len(sessions_list)} sessions recorded)")

    # 4. Export Endpoints (JSON, HTML, Markdown)
    if session_id:
        for fmt in ["json", "html", "md"]:
            log(f"Testing GET /api/v1/research/{session_id}/export?format={fmt}...")
            res_exp = client.get(f"/api/v1/research/{session_id}/export?format={fmt}")
            assert res_exp.status_code == 200, f"Export format '{fmt}' failed"
            assert len(res_exp.text) > 50, f"Export format '{fmt}' empty"
            log(f"Export format '{fmt}' PASSED! ({len(res_exp.text)} bytes)")

    log("=" * 60)
    log("ALL END-TO-END INTEGRATION TESTS PASSED SUCCESSFULLY!")
    log("=" * 60)

if __name__ == "__main__":
    run_e2e_test()
