import json
from pathlib import Path
import sys
import tempfile
from types import SimpleNamespace
import unittest
from unittest.mock import AsyncMock, Mock, patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import browser_ape


class DriverTests(unittest.IsolatedAsyncioTestCase):
    async def test_start_browser_retries_transient_cdp_failure(self):
        failed = SimpleNamespace(start=AsyncMock(side_effect=RuntimeError('timeout')),
                                 stop=AsyncMock(), reset=AsyncMock())
        connected = SimpleNamespace(start=AsyncMock(), stop=AsyncMock())
        with patch.object(browser_ape, 'make_browser', side_effect=[failed, connected]):
            browser = await browser_ape.start_browser(9222, retries=2, retry_delay=0)
        self.assertIs(browser, connected)
        failed.stop.assert_awaited_once()
        connected.start.assert_awaited_once()

    async def test_start_browser_reports_exhausted_cdp_retries(self):
        failed = SimpleNamespace(start=AsyncMock(side_effect=RuntimeError('timeout')),
                                 stop=AsyncMock(), reset=AsyncMock())
        with patch.object(browser_ape, 'make_browser', return_value=failed):
            with self.assertRaisesRegex(RuntimeError, '2 次尝试均失败'):
                await browser_ape.start_browser(9222, retries=2, retry_delay=0)
        self.assertEqual(failed.stop.await_count, 2)

    async def test_initialization_failure_is_saved(self):
        with tempfile.TemporaryDirectory() as folder:
            args = browser_ape.parse_args(['--url', 'https://example.com', '--capture-dir', folder])
            self.assertEqual(await browser_ape.main(args), 1)
            result = json.loads((Path(folder) / 'ape-result.json').read_text(encoding='utf-8'))
            self.assertFalse(result['success'])
            self.assertIn('--llm-api-key', result['error'])
            status = json.loads((Path(folder) / 'ape-status.json').read_text(encoding='utf-8'))
            self.assertEqual(status['state'], 'stopped')

    async def test_navigation_precedes_agent_and_success_is_saved(self):
        with tempfile.TemporaryDirectory() as folder:
            args = browser_ape.parse_args(['--url', 'https://example.com', '--capture-dir', folder])
            page = SimpleNamespace(goto=AsyncMock())
            browser = SimpleNamespace(stop=AsyncMock(), get_current_page=AsyncMock(return_value=page))
            history = Mock(history=[])
            history.is_successful.return_value = True
            history.final_result.return_value = 'Done'
            history.errors.return_value = []

            async def run(**kwargs):
                page.goto.assert_awaited_once_with(args.url)
                self.assertIn('on_step_start', kwargs)
                self.assertIn('on_step_end', kwargs)
                return history

            agent = SimpleNamespace(run=AsyncMock(side_effect=run))
            with patch.object(browser_ape, 'make_llm'), \
                  patch.object(browser_ape, 'start_browser', return_value=browser), \
                 patch.object(browser_ape, 'LoginGuardAgent', return_value=agent):
                self.assertEqual(await browser_ape.main(args), 0)
            result = json.loads((Path(folder) / 'ape-result.json').read_text(encoding='utf-8'))
            self.assertTrue(result['success'])
            browser.stop.assert_awaited_once()

    async def test_disconnect_failure_does_not_raise(self):
        browser = SimpleNamespace(stop=AsyncMock(side_effect=RuntimeError('closed')), reset=AsyncMock())
        await browser_ape.disconnect_browser(browser)
        browser.reset.assert_awaited_once()
