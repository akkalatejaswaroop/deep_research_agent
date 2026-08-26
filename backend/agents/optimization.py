"""
Optimization and caching utilities for the Deep Research Agent.
Handles LLM response caching, search result caching, and streaming.
"""
import os
import json
import hashlib
import time
from typing import Dict, Optional, Any, Callable
from functools import wraps
import threading
import queue

# In-memory cache
_llm_response_cache: Dict[str, Dict[str, Any]] = {}
_search_result_cache: Dict[str, Dict[str, Any]] = {}
_cache_lock = threading.Lock()

CACHE_ENABLED = os.getenv("CACHE_ENABLED", "true").lower() == "true"
CACHE_TTL = int(os.getenv("CACHE_TTL", "86400"))


def _get_cache_key(key_input: str) -> str:
    """Generate a consistent cache key."""
    return hashlib.sha256(key_input.encode()).hexdigest()


def llm_response_cache(func: Callable) -> Callable:
    """
    Decorator to cache LLM responses.
    Caches based on model + prompt combination.
    """
    @wraps(func)
    def wrapper(*args, **kwargs):
        if not CACHE_ENABLED:
            return func(*args, **kwargs)
        
        # Extract model and prompt
        model = kwargs.get("model") or (args[0] if args else "unknown")
        prompt = kwargs.get("prompt") or (args[1] if len(args) > 1 else "")
        
        if not prompt:
            return func(*args, **kwargs)
        
        cache_key = _get_cache_key(f"{model}:{prompt[:500]}")
        
        with _cache_lock:
            if cache_key in _llm_response_cache:
                entry = _llm_response_cache[cache_key]
                if time.time() - entry["timestamp"] < CACHE_TTL:
                    print(f"[CACHE HIT] LLM response for {model}")
                    return entry["response"]
                else:
                    del _llm_response_cache[cache_key]
        
        # Call the actual function
        response = func(*args, **kwargs)
        
        # Cache the response
        with _cache_lock:
            _llm_response_cache[cache_key] = {
                "response": response,
                "timestamp": time.time(),
            }
        
        return response
    
    return wrapper


def search_result_cache(func: Callable) -> Callable:
    """
    Decorator to cache search results.
    Caches based on query.
    """
    @wraps(func)
    def wrapper(*args, **kwargs):
        if not CACHE_ENABLED:
            return func(*args, **kwargs)
        
        # Extract query
        query = kwargs.get("query") or (args[0] if args else "")
        
        if not query:
            return func(*args, **kwargs)
        
        cache_key = _get_cache_key(f"search:{query}")
        
        with _cache_lock:
            if cache_key in _search_result_cache:
                entry = _search_result_cache[cache_key]
                if time.time() - entry["timestamp"] < CACHE_TTL:
                    print(f"[CACHE HIT] Search results for '{query[:40]}'")
                    return entry["results"]
                else:
                    del _search_result_cache[cache_key]
        
        # Call the actual function
        results = func(*args, **kwargs)
        
        # Cache the results
        with _cache_lock:
            _search_result_cache[cache_key] = {
                "results": results,
                "timestamp": time.time(),
            }
        
        return results
    
    return wrapper


def clear_cache():
    """Clear all caches."""
    global _llm_response_cache, _search_result_cache
    with _cache_lock:
        _llm_response_cache.clear()
        _search_result_cache.clear()
    print("[CACHE] All caches cleared")


def get_cache_stats() -> Dict[str, int]:
    """Get cache statistics."""
    with _cache_lock:
        return {
            "llm_responses_cached": len(_llm_response_cache),
            "search_results_cached": len(_search_result_cache),
            "total_entries": len(_llm_response_cache) + len(_search_result_cache),
        }


class StreamingEventQueue:
    """
    Thread-safe event queue for real-time streaming to frontend.
    Supports multiple event types: thought, source, progress, error.
    """
    
    def __init__(self, max_size: int = 1000):
        self.queue = queue.Queue(maxsize=max_size)
        self.closed = False
    
    def put_thought(self, message: str):
        """Add a thought/status message."""
        self.put({
            "type": "thought",
            "message": message,
            "timestamp": time.time(),
        })
    
    def put_source(self, url: str, title: str = ""):
        """Add a discovered source."""
        self.put({
            "type": "source",
            "url": url,
            "title": title or url,
            "timestamp": time.time(),
        })
    
    def put_progress(self, stage: str, progress: int, total: int, message: str = ""):
        """Add a progress update."""
        self.put({
            "type": "progress",
            "stage": stage,
            "progress": progress,
            "total": total,
            "message": message,
            "timestamp": time.time(),
        })
    
    def put_error(self, message: str, stage: str = "unknown"):
        """Add an error message."""
        self.put({
            "type": "error",
            "message": message,
            "stage": stage,
            "timestamp": time.time(),
        })
    
    def put_result(self, data: Dict[str, Any]):
        """Add a result update."""
        self.put({
            "type": "result",
            "data": data,
            "timestamp": time.time(),
        })
    
    def put(self, event: Dict[str, Any]):
        """Put an event in the queue."""
        if self.closed:
            return
        try:
            self.queue.put_nowait(event)
        except queue.Full:
            # Remove oldest item and retry
            try:
                self.queue.get_nowait()
                self.queue.put_nowait(event)
            except queue.Empty:
                pass
    
    def get(self, timeout: Optional[float] = 1.0) -> Optional[Dict[str, Any]]:
        """Get the next event from the queue."""
        if self.closed:
            return None
        try:
            return self.queue.get(timeout=timeout)
        except queue.Empty:
            return None
    
    def get_all(self) -> list:
        """Get all pending events."""
        events = []
        while True:
            try:
                event = self.queue.get_nowait()
                events.append(event)
            except queue.Empty:
                break
        return events
    
    def close(self):
        """Close the queue."""
        self.closed = True
    
    def __iter__(self):
        """Iterate over events until queue is closed."""
        while not self.closed:
            event = self.get(timeout=1.0)
            if event is not None:
                yield event


def create_streaming_response_generator(event_queue: StreamingEventQueue):
    """
    Create a generator for Server-Sent Events (SSE) streaming response.
    """
    def generate():
        try:
            # Send initial connection event
            yield f"data: {json.dumps({'type': 'connected', 'timestamp': time.time()})}\n\n"
            
            # Stream events from the queue
            for event in event_queue:
                if event:
                    try:
                        yield f"data: {json.dumps(event)}\n\n"
                    except Exception as e:
                        print(f"Error serializing event: {e}")
                        continue
        except GeneratorExit:
            event_queue.close()
        except Exception as e:
            print(f"Error in streaming generator: {e}")
    
    return generate()


# Timeout helper with fallback
class TimeoutHandler:
    """Helper class for managing LLM call timeouts with fallback strategies."""
    
    def __init__(self, timeout_seconds: float = None):
        if timeout_seconds is None:
            timeout_seconds = float(os.getenv("LLM_TIMEOUT", "120"))
        self.timeout = timeout_seconds
        self.fallback_responses = {
            "planner": json.dumps({"sub_questions": ["Key background and architecture", "Empirical data and benchmarks", "Trade-offs and limitations", "Future outlook"]}),
            "filter": json.dumps([]),
            "synthesis": json.dumps({"answer": "Synthesis timed out; using cached or fallback information."}),
            "gap_detector": json.dumps({"gaps": []}),
            "citation_mapper": "Processing completed.",
            "report": "# Deep Research Report\n\n## Executive Summary\nResearch report compilation timed out during full synthesis.\n\n## Key Findings\nResearch was conducted across queried tracks.\n",
            "evaluator": json.dumps({"lesson": "Execution timed out during stage.", "scores": {"relevance": 5, "depth": 5, "novelty": 5, "coherence": 5, "citation_accuracy": 5}}),
        }
    
    def get_fallback(self, stage: str) -> str:
        """Get appropriate fallback response for a stage."""
        return self.fallback_responses.get(stage, "Processing failed; using fallback.")
    
    def execute_with_timeout(self, func: Callable, stage: str, *args, **kwargs) -> Any:
        """
        Execute a function with timeout and fallback.
        Returns function result or fallback response on timeout.
        """
        import threading
        
        result_container = []
        error_container = []
        
        def target():
            try:
                res = func(*args, **kwargs)
                result_container.append(res)
            except Exception as ex:
                error_container.append(ex)

        thread = threading.Thread(target=target, daemon=True)
        thread.start()
        thread.join(timeout=self.timeout)
        
        if thread.is_alive():
            print(f"[TIMEOUT] Stage '{stage}' exceeded {self.timeout}s")
            return self.get_fallback(stage)
        elif error_container:
            print(f"[ERROR] Stage '{stage}': {error_container[0]}")
            return self.get_fallback(stage)
        elif result_container:
            return result_container[0]
        else:
            return self.get_fallback(stage)



# Batch processing utility
def batch_process(items: list, func: Callable, batch_size: int = 5, max_workers: int = 5):
    """
    Process items in batches using thread pool.
    Yields results as they complete.
    """
    from concurrent.futures import ThreadPoolExecutor, as_completed
    
    results = []
    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        futures = {executor.submit(func, item): i for i, item in enumerate(items)}
        for future in as_completed(futures):
            try:
                result = future.result()
                idx = futures[future]
                results.append((idx, result))
                yield result
            except Exception as e:
                idx = futures[future]
                print(f"Error processing item {idx}: {e}")
                yield None


# Deduplication utility
def deduplicate_results(results: list, key_func: Callable) -> list:
    """
    Deduplicate results based on key function.
    Preserves order and keeps first occurrence.
    """
    seen = set()
    deduplicated = []
    for item in results:
        key = key_func(item)
        if key not in seen:
            seen.add(key)
            deduplicated.append(item)
    return deduplicated


if __name__ == "__main__":
    print("Optimization module loaded successfully")
    print(f"Cache enabled: {CACHE_ENABLED}")
    print(f"Cache TTL: {CACHE_TTL}s")
