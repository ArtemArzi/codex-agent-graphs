import json
from pathlib import Path
import subprocess
import sys
import unittest

ROOT = Path(__file__).resolve().parent


class AccessChecks(unittest.TestCase):
    def call(self, user, record):
        return subprocess.run([sys.executable, '-B', str(ROOT / 'app.py'), '--user', user, '--record', record], cwd=ROOT, text=True, capture_output=True)

    def test_own_record(self):
        result = self.call('alice', 'a1')
        self.assertEqual(result.returncode, 0)
        self.assertEqual(json.loads(result.stdout)['tenant'], 'alpha')

    def test_other_tenant_is_denied(self):
        result = self.call('alice', 'b1')
        self.assertEqual(result.returncode, 3, 'A foreign tenant record must be denied')
        self.assertNotIn('Beta private draft', result.stdout)


if __name__ == '__main__':
    unittest.main()
