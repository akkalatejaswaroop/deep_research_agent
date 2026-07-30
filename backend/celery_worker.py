from celery import Celery
import redis
import json
import os
from agents.graph import app_graph

redis_url = os.getenv("CELERY_BROKER_URL", "redis://localhost:6379/0")
celery_app = Celery("deep_research", broker=redis_url, backend=redis_url)
redis_client = redis.Redis.from_url(redis_url)

@celery_app.task(bind=True)
def run_research_graph(self, session_id: str, initial_state: dict):
    channel_name = f"research_stream_{session_id}"
    config = {"configurable": {"thread_id": session_id}}
    
    for output in app_graph.stream(initial_state, config=config):
        node_name = list(output.keys())[0]
        redis_client.publish(channel_name, json.dumps({"node": node_name}))
        
    state_snapshot = app_graph.get_state(config)
    final_report = state_snapshot.values.get("report", "") if state_snapshot else ""
    redis_client.publish(channel_name, json.dumps({"node": "end", "report": final_report}))
    
    return {"status": "completed", "session_id": session_id}

@celery_app.task(bind=True)
def resume_research_graph(self, session_id: str):
    channel_name = f"research_stream_{session_id}"
    config = {"configurable": {"thread_id": session_id}}
    
    for output in app_graph.stream(None, config=config):
        node_name = list(output.keys())[0]
        redis_client.publish(channel_name, json.dumps({"node": node_name}))
        
    state_snapshot = app_graph.get_state(config)
    final_report = state_snapshot.values.get("report", "") if state_snapshot else ""
    redis_client.publish(channel_name, json.dumps({"node": "end", "report": final_report}))
    
    return {"status": "resumed_completed", "session_id": session_id}
