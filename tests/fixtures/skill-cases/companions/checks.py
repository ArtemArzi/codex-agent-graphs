import sys
from labels import normalize_label
from report import export_label

if sys.argv[1] == "labels":
    assert normalize_label("  Golden  Square  ") == "golden  square"
    assert normalize_label("  ") == ""
    assert isinstance(normalize_label("A"), str)
elif sys.argv[1] == "report":
    assert export_label("  Golden  Square  ") == "label=golden  square"
else:
    raise ValueError("Unknown check")
print("PASS", sys.argv[1])
