import contextlib
import io
from pathlib import Path
import sys
import tempfile
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from browser_ape import parse_args, COMPLETION_RULE


class PromptTests(unittest.TestCase):
    def parse(self, *extra):
        return parse_args(['--url', 'https://example.com', '--capture-dir', '/tmp/capture', *extra])

    def test_legacy_template_unchanged(self):
        self.assertEqual(self.parse('--task-template', '探索 {url}').resolved_task, '探索 https://example.com' + COMPLETION_RULE)

    def test_default_and_custom_prompt(self):
        task = self.parse('--explore-prompt', '只浏览报表，汇总 {url} 的问题').resolved_task
        self.assertIn('打开 https://example.com', task)
        self.assertIn('只浏览报表，汇总 https://example.com 的问题', task)
        self.assertNotIn('登录后浏览主要导航', task)
        self.assertIn('立即调用 done', task)

    def test_append_to_existing_template(self):
        task = self.parse('--task-template', '基本任务', '--explore-prompt', '详细要求').resolved_task
        self.assertIn('基本任务', task)
        self.assertIn('用户任务（任务范围和结束条件优先于基础模板）：\n详细要求', task)

    def test_multiline_utf8_bom_file(self):
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / 'prompt.txt'
            path.write_text('探索 {url}\n保留 JSON 示例 {"a": 1}', encoding='utf-8-sig')
            task = self.parse('--explore-prompt-file', str(path)).resolved_task
            self.assertIn('探索 https://example.com\n保留 JSON 示例 {"a": 1}', task)
            self.assertNotIn('\ufeff', task)

    def test_invalid_inputs_fail_before_browser_or_model_start(self):
        for extra in [('--explore-prompt', ' '), ('--task-template', ''),
                      ('--explore-prompt-file', '/missing/prompt.txt'),
                      ('--explore-prompt', 'a', '--explore-prompt-file', 'b'),
                      ('--max-steps', '0'), ('--max-steps', '-1'),
                      ('--cdp-port', '0'), ('--cdp-port', '65536'),
                      ('--cdp-start-retries', '0'), ('--cdp-start-delay', 'nan'),
                      ('--login-wait-timeout', 'nan'), ('--login-wait-timeout', 'inf'),
                      ('--login-wait-timeout', '-1')]:
            with self.subTest(extra=extra), contextlib.redirect_stderr(io.StringIO()):
                with self.assertRaises(SystemExit) as exc:
                    self.parse(*extra)
                self.assertEqual(exc.exception.code, 2)


if __name__ == '__main__':
    unittest.main()
