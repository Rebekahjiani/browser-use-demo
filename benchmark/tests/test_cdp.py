"""Isolated headless Chrome snapshot smoke test; no model or existing browser touched."""
import asyncio
import importlib.util
import os
from pathlib import Path
import subprocess
import tempfile
import time
import unittest

spec = importlib.util.spec_from_file_location('capture_runner', Path(__file__).parents[1] / 'run.py')
runner = importlib.util.module_from_spec(spec)
spec.loader.exec_module(runner)


class CaptureSmoke(unittest.TestCase):
    def test_real_cdp_snapshot(self):
        chrome = Path(os.environ.get('PROGRAMFILES', 'C:/Program Files')) / 'Google/Chrome/Application/chrome.exe'
        if not chrome.exists():
            self.skipTest('Chrome not installed at the standard Windows path')
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            proc = subprocess.Popen([str(chrome), '--headless=new', '--no-first-run',
                '--no-default-browser-check', '--remote-debugging-port=0',
                f'--user-data-dir={root / "profile"}', 'about:blank'],
                stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
                creationflags=subprocess.CREATE_NO_WINDOW)
            try:
                port_file = root / 'profile' / 'DevToolsActivePort'
                until = time.monotonic() + 20
                while not port_file.exists():
                    if time.monotonic() > until or proc.poll() is not None:
                        self.fail('Chrome did not expose CDP')
                    time.sleep(.1)
                port = port_file.read_text().splitlines()[0]
                targets = runner.request_json(f'http://127.0.0.1:{port}/json/list')
                target = next(t for t in targets if t.get('type') == 'page')
                result = asyncio.run(runner.cdp_capture(target, root / 'snapshot'))
                self.assertEqual(result['url'], 'about:blank')
                for filename in ['page.html', 'accessibility.json', 'screenshot.png', 'metadata.json']:
                    self.assertGreater((root / 'snapshot' / filename).stat().st_size, 0)
            finally:
                proc.terminate()
                proc.wait(timeout=10)
                time.sleep(.5)


if __name__ == '__main__':
    unittest.main()
