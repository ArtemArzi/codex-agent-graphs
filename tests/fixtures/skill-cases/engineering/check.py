from labels import normalize_label
assert normalize_label("  HeLLo  ") == "hello"
assert normalize_label("A  B") == "a  b"
assert normalize_label("   ") == ""
print("label contract passed")
