import json
from pathlib import Path
def write_cache(path, payload):
    Path(path).write_text(json.dumps(payload))
