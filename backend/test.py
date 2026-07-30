import urllib.request
import urllib.error

try:
    response = urllib.request.urlopen('http://localhost:8001/api/v1/sessions/')
    print("SUCCESS", response.read().decode('utf-8'))
except urllib.error.HTTPError as e:
    print("ERROR", e.code, e.read().decode('utf-8'))
except Exception as e:
    print("OTHER ERROR", str(e))
