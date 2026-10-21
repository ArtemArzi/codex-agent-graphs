from importlib import import_module
import sys


module = import_module(sys.argv[1])
assert module.render_tickets() == "1\n2\n3"
assert module.render_tickets("open") == "1\n3"
try:
    module.render_tickets("missing")
except ValueError:
    pass
else:
    raise AssertionError("unknown status must raise ValueError")
print("behavior contract passed; import boundary still requires review")
