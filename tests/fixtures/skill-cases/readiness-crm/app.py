import argparse
import json
from pathlib import Path

parser = argparse.ArgumentParser()
parser.add_argument('--user', required=True)
parser.add_argument('--record', required=True)
args = parser.parse_args()
data = json.loads((Path(__file__).parent / 'data/records.json').read_text())
actor = data['users'][args.user]
record = data['records'][args.record]
print(json.dumps(record, sort_keys=True))
