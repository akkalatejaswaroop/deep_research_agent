import os
os.environ["SIMULATED_MODE"] = "false"
from main import search_all_sources
sources = search_all_sources("transformer architecture AI", 3)
print(f"Found {len(sources)} sources")
for s in sources[:3]:
    print(f"  - {s['title']}: {s['url']}")
