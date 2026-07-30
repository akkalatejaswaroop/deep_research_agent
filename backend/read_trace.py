with open("trace.log", "rb") as f:
    data = f.read()

# Decode as utf-16le or utf-8
try:
    text = data.decode("utf-16")
except Exception:
    text = data.decode("utf-8", errors="ignore")

lines = text.splitlines()
last_lines = lines[-100:]

with open("trace_end.txt", "w", encoding="utf-8") as f_out:
    f_out.write("\n".join(last_lines))
    