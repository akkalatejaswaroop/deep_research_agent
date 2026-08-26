import uvicorn
import sys
import os
sys.path.insert(0, r'D:\deep_research_agent\backend')
os.chdir(r'D:\deep_research_agent\backend')
uvicorn.run('main:app', host='127.0.0.1', port=8000, reload=False)