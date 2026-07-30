import sys
import os
import subprocess

with open("debug_env.log", "w") as f:
    f.write(f"Python executable: {sys.executable}\n")
    f.write(f"Python version: {sys.version}\n")
    f.write(f"Python path: {sys.path}\n")
    
    # Try calling where python
    try:
        res = subprocess.run(["where", "python"], capture_output=True, text=True)
        f.write(f"where python output:\n{res.stdout}\n")
    except Exception as e:
        f.write(f"Error running where python: {e}\n")
