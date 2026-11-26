import json
import time
import urllib.request

while True:
    with urllib.request.urlopen("http://127.0.0.1:8087/status",timeout=5) as reply:
        row=json.load(reply)
    print(f"{row['time']}  ready={row['ready']} desired={row['desired']}  CPU={row['cpu']}%  "
          f"cooldown={row['hold_seconds']}s  {row['reason']}", flush=True)
    time.sleep(2)
