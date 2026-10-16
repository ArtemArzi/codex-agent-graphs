import json
from pathlib import Path
r=Path(__file__).resolve().parents[1]
print(json.dumps({"skill":str(r),"canon":str(r/"references/canon"),"producer":str(r/"references/PRODUCER-CONTRACT.md"),"readability":str(r/"references/READABILITY-CONTRACT.md")},ensure_ascii=False))
