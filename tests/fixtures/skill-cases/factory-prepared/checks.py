import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parent
TEMP = ROOT / '.local' / 'test-scratch'


class ManifestChecks(unittest.TestCase):
    def setUp(self):
        TEMP.mkdir(parents=True, exist_ok=True)
        self.temp = tempfile.TemporaryDirectory(dir=TEMP)
        self.addCleanup(self.temp.cleanup)
        self.folder = Path(self.temp.name)
        self.db = self.folder / 'manifest.sqlite3'
        self.csv = self.folder / 'items.csv'
        self.csv.write_text('sku,name,units\nZ2,Blue box,3\nA1,Green box,2\n')

    def cli(self, *arguments, expected=0):
        result = subprocess.run([sys.executable, '-B', str(ROOT / 'app.py'), *map(str, arguments)], cwd=ROOT, text=True, capture_output=True)
        self.assertEqual(result.returncode, expected, result.stdout + result.stderr)
        return result

    def load(self):
        self.cli('import', '--db', self.db, '--input', self.csv)

    def summary(self):
        return json.loads(self.cli('summary', '--db', self.db).stdout)

    def test_import_summary_and_repeat(self):
        self.load()
        self.assertEqual(self.summary(), {'items': 2, 'units': 5})
        self.load()
        self.assertEqual(self.summary(), {'items': 2, 'units': 5})

    def test_invalid_input_is_atomic(self):
        self.load()
        for data in ('sku,name,units\nA1,Changed,9\nB3,Bad,-1\n', 'sku,name,units\nA1,Changed,9\nA1,Again,4\n', 'sku,name,units\nA1,Changed,9\nB3,Bad,1.5\n', 'sku,name,units,extra\nA1,Changed,9,x\n'):
            with self.subTest(data=data):
                self.csv.write_text(data)
                result = self.cli('import', '--db', self.db, '--input', self.csv, expected=2)
                self.assertIn('invalid', (result.stdout + result.stderr).lower())
                self.assertEqual(self.summary(), {'items': 2, 'units': 5})

    def test_missing_operator_preserves_output(self):
        self.load()
        output = self.folder / 'export.json'
        output.write_text('retained output')
        result = self.cli('export', '--db', self.db, '--config', self.folder / 'missing.json', '--output', output, expected=2)
        self.assertIn('operator', (result.stdout + result.stderr).lower())
        self.assertEqual(output.read_text(), 'retained output')
        self.assertEqual(self.summary(), {'items': 2, 'units': 5})

    def test_invalid_operator_preserves_output(self):
        self.load()
        config = self.folder / 'operator.json'
        output = self.folder / 'export.json'
        output.write_text('retained output')
        for raw in ('{', '{"destination":"other"}'):
            with self.subTest(raw=raw):
                config.write_text(raw)
                result = self.cli('export', '--db', self.db, '--config', config, '--output', output, expected=2)
                self.assertIn('operator', (result.stdout + result.stderr).lower())
                self.assertEqual(output.read_text(), 'retained output')
                self.assertEqual(self.summary(), {'items': 2, 'units': 5})

    def test_configured_export_and_repeat(self):
        self.load()
        config = self.folder / 'operator.json'
        config.write_text('{"destination":"demo-west"}')
        output = self.folder / 'export.json'
        arguments = ('export', '--db', self.db, '--config', config, '--output', output)
        self.cli(*arguments)
        expected = {'destination': 'demo-west', 'items': [{'sku': 'A1', 'name': 'Green box', 'units': 2}, {'sku': 'Z2', 'name': 'Blue box', 'units': 3}]}
        self.assertEqual(json.loads(output.read_text()), expected)
        before = output.read_bytes()
        self.cli(*arguments)
        self.assertEqual(output.read_bytes(), before)
        self.assertEqual(self.summary(), {'items': 2, 'units': 5})


if __name__ == '__main__':
    unittest.main()
