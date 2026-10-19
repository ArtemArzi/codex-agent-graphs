def fetch(response):
    if response.status_code != 200:
        return []
    return response.json().get("items", [])

def store(items, save):
    skipped = 0
    for item in items:
        if not save(item):
            skipped += 1
    return skipped
