def _to_lower(value):
    return value.lower()


def normalize_title(value):
    return '-'.join(_to_lower(value).split())
