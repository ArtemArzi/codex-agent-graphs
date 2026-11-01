from labels import normalize_label

def build_record(value):
    return {"label": normalize_label(value)}
