from service import build_record

def export_label(value):
    return "label=" + build_record(value)["label"]
