import os

if "PREFER_LLM" not in os.environ:
    os.environ["PREFER_LLM"] = "false"
