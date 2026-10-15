def _to_lower(value):
    return value.lower()


def normalize_title(value):
    return _to_lower(value).strip().replace(' ', '-')
