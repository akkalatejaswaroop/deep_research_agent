import sys

class TraceImports:
    def __init__(self):
        self.depth = 0

    def __call__(self, frame, event, arg):
        if event == "call":
            code = frame.f_code
            name = code.co_name
            filename = code.co_filename
            if "site-packages" in filename or "importlib" in filename:
                print("  " * self.depth + f"-> {name} in {filename}")
                self.depth += 1
        elif event == "return":
            self.depth = max(0, self.depth - 1)
        return self

sys.settrace(TraceImports())

print("Importing ChatOllama...")
from langchain_ollama import ChatOllama
print("Import complete.")
