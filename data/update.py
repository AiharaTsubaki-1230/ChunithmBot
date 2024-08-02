import json
import time

data = json.loads(open("./data/user.json").read()) # -> dict

keys = list(data.keys())

for key in keys:
    data[key]["last_sign"] = time.time()

open("./data/user.json", "w").write(json.dumps(data))