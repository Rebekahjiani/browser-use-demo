"""Verify external Chrome survives a clean CDP disconnect, without an LLM."""
import asyncio
import tempfile
from pathlib import Path
from dotenv import load_dotenv
from explore_live import launch_chrome, ROOT
from browser_ape import disconnect_browser
from browser_use import Browser


async def main():
    load_dotenv(ROOT / '.env')
    # Chromium child processes can briefly retain cache handles after exit on
    # Windows. Cache deletion is not part of the CDP lifecycle assertion.
    with tempfile.TemporaryDirectory(ignore_cleanup_errors=True) as temp:
        process, port = await launch_chrome(Path(temp), True)
        browser = Browser(cdp_url=f'http://127.0.0.1:{port}', keep_alive=True)
        try:
            await browser.start()
            page = await browser.get_current_page()
            assert await page.evaluate('() => 2 + 2') == '4'
            await disconnect_browser(browser)
            assert process.poll() is None, 'Disconnect must not kill external Chrome'
            assert browser._cdp_client_root is None, 'CDP connection must be released'
            print('PASS: CDP disconnected and external Chrome remains alive', flush=True)
        finally:
            process.terminate()
            try:
                await asyncio.to_thread(process.wait, timeout=5)
            except Exception:
                process.kill()
                await asyncio.to_thread(process.wait, timeout=5)


if __name__ == '__main__':
    asyncio.run(main())
