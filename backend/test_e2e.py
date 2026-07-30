"""End-to-end test: sends a research query and streams the SSE response."""
import json
import sys
import urllib.request
import time
import ssl

def main():
    ctx = ssl.create_default_context()
    ctx.check_hostname = False
    ctx.verify_mode = ssl.CERT_NONE

    payload = json.dumps({"query": "What is the capital of France?", "mode": "fast", "model": "ollama"}).encode()
    req = urllib.request.Request(
        "http://127.0.0.1:8001/api/v1/research",
        data=payload,
        headers={"Content-Type": "application/json"},
        method="POST"
    )

    MAX_LINES = 80
    STATUS_TIMEOUT = 90
    start = time.time()

    try:
        resp = urllib.request.urlopen(req, context=ctx, timeout=STATUS_TIMEOUT)
        content_type = resp.headers.get("Content-Type", "")
        print(f"Content-Type: {content_type}", flush=True)
        print(f"Status: {resp.status}", flush=True)

        lines_read = 0
        for line in resp:
            text = line.decode("utf-8", errors="replace").strip()
            if text.startswith("data: "):
                text = text[6:]
            if text == "[DONE]":
                print("[DONE]", flush=True)
                break
            if text:
                print(f"  {text[:250]}", flush=True)
                lines_read += 1
                if "error" in text.lower() or "fail" in text.lower():
                    print("ERROR DETECTED!", flush=True)
            if lines_read >= MAX_LINES:
                print("... (truncated)", flush=True)
                break
            elapsed = time.time() - start
            if elapsed > STATUS_TIMEOUT:
                print(f"\nTIMED OUT after {elapsed:.0f}s", flush=True)
                break

        print(f"\nTest completed. Lines: {lines_read}, Elapsed: {time.time()-start:.1f}s", flush=True)
    except Exception as e:
        elapsed = time.time() - start
        print(f"FAILED after {elapsed:.0f}s: {e}", flush=True)
        if hasattr(e, 'read'):
            body = e.read().decode('utf-8', errors='replace')[:500]
            print(f"Response body: {body}", flush=True)
        sys.exit(1)

if __name__ == "__main__":
    main()
