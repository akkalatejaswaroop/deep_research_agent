import sys
import traceback

with open("debug_import.log", "w") as f:
    f.write("Starting debug import...\n")
    try:
        f.write("Importing agents.graph...\n")
        f.flush()
        from agents.graph import app_graph
        f.write("Import successful! app_graph = " + str(app_graph) + "\n")
    except Exception as e:
        f.write("Exception caught:\n")
        traceback.print_exc(file=f)
    f.write("Done.\n")
