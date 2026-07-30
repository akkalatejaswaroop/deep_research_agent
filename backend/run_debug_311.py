import sys
import traceback

with open("debug_import_311.log", "w") as f:
    f.write("Starting Python 3.11 import test...\n")
    try:
        f.write("Importing agents.graph...\n")
        f.flush()
        from agents.graph import app_graph
        f.write("Success! app_graph = " + str(app_graph) + "\n")
    except Exception as e:
        f.write("Exception:\n")
        traceback.print_exc(file=f)
    f.write("Finished.\n")
